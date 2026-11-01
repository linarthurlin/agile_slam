"""Static contract checks for the simulation's canonical E6 TF migration."""
from pathlib import Path
import json
import unittest
import xml.etree.ElementTree as ET

import yaml


ROOT = Path(__file__).resolve().parents[1]
XACRO_PATH = ROOT / "ros2_ws/src/gem_description/urdf/gem.urdf.xacro"
REGISTRY_PATH = ROOT / "config/e6/simulation_nominal_transforms.yaml"


def local_name(tag):
    return tag.rsplit("}", 1)[-1]


class SimulationCanonicalTfTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.xacro_source = XACRO_PATH.read_text()
        cls.robot = ET.fromstring(cls.xacro_source)
        cls.registry = yaml.safe_load(REGISTRY_PATH.read_text())
        cls.links = {
            element.get("name")
            for element in cls.robot.iter()
            if local_name(element.tag) == "link"
        }
        cls.parents = {}
        for joint in (
            element
            for element in cls.robot.iter()
            if local_name(element.tag) == "joint"
        ):
            parent = next(
                (
                    child.get("link")
                    for child in joint
                    if local_name(child.tag) == "parent"
                ),
                None,
            )
            child = next(
                (
                    element.get("link")
                    for element in joint
                    if local_name(element.tag) == "child"
                ),
                None,
            )
            if not parent or not child:
                continue
            if parent.startswith("${"):
                parent = cls.registry["simulation_scope"]["supplemental_transforms"][
                    "legacy_gnss_sim_link"
                ]["parent"]
            if child in cls.parents:
                raise AssertionError(f"{child} has multiple parent joints")
            cls.parents[child] = parent

    def test_robot_description_is_one_tree_rooted_at_base_link(self):
        roots = self.links - set(self.parents)
        self.assertEqual(roots, {"base_link"})
        self.assertEqual(set(self.parents), self.links - roots)
        self.assertTrue(set(self.parents.values()) <= self.links)

    def test_canonical_sensor_parentage_is_used_by_simulation(self):
        expected = {
            "base_chassis_link": "base_link",
            "top_sensor_rig_link": "base_link",
            "velodyne_link": "top_sensor_rig_link",
            "realsense_link": "base_link",
            "realsense_color_optical_frame": "realsense_link",
            "realsense_depth_optical_frame": "realsense_link",
            "realsense_imu_frame": "realsense_link",
        }
        for child, parent in expected.items():
            with self.subTest(child=child):
                self.assertEqual(self.parents[child], parent)

    def test_nominal_transforms_are_loaded_from_the_registry(self):
        transforms = self.registry["transforms"]
        self.assertIn("xacro.load_yaml(simulation_nominal_file)", self.xacro_source)
        for frame in (
            "base_chassis_link",
            "top_sensor_rig_link",
            "velodyne_link",
            "realsense_link",
            "realsense_color_optical_frame",
            "realsense_depth_optical_frame",
            "realsense_imu_frame",
        ):
            with self.subTest(frame=frame):
                self.assertIn(frame, transforms)
                self.assertIn(f"sim_transforms['{frame}']['translation_m']", self.xacro_source)
                self.assertIn(f"sim_transforms['{frame}']['rotation_rpy_rad']", self.xacro_source)

        rig = transforms["top_sensor_rig_link"]["translation_m"]
        lidar = transforms["velodyne_link"]["translation_m"]
        resolved = [a + b for a, b in zip(rig, lidar)]
        expected = transforms["velodyne_link"]["resolved_base_pose_m"]
        for actual, recorded in zip(resolved, expected):
            self.assertAlmostEqual(actual, recorded, places=5)

    def test_ros_package_and_container_install_the_registry_for_xacro(self):
        cmake = (ROOT / "ros2_ws/src/gem_description/CMakeLists.txt").read_text()
        dockerfile = (ROOT / "containers/Dockerfile").read_text()
        self.assertIn(
            "${CMAKE_CURRENT_SOURCE_DIR}/../../../config/e6/simulation_nominal_transforms.yaml",
            cmake,
        )
        self.assertIn(
            "COPY config/e6/simulation_nominal_transforms.yaml /opt/config/e6/simulation_nominal_transforms.yaml",
            dockerfile,
        )

    def test_nav_and_runtime_consumers_use_base_link(self):
        nav = yaml.safe_load(
            (ROOT / "ros2_ws/src/agile_navigation/config/nav2.yaml").read_text()
        )
        runtime = json.loads(
            (ROOT / "config/interfaces/runtime.json").read_text()
        )
        self.assertEqual(
            nav["bt_navigator"]["ros__parameters"]["robot_base_frame"], "base_link"
        )
        self.assertEqual(
            nav["local_costmap"]["local_costmap"]["ros__parameters"][
                "robot_base_frame"
            ],
            "base_link",
        )
        self.assertEqual(
            nav["global_costmap"]["global_costmap"]["ros__parameters"][
                "robot_base_frame"
            ],
            "base_link",
        )
        self.assertEqual(runtime["tf_owners"]["odom->base_link"], "wheel_odometry")
        for source_path in (
            "ros2_ws/src/agile_navigation/scripts/wheel_odometry.py",
            "ros2_ws/src/agile_navigation/scripts/readiness.py",
            "ros2_ws/src/agile_navigation/scripts/obstacle_scan.py",
            "ros2_ws/src/agile_vehicle/scripts/vehicle_control.py",
        ):
            source = (ROOT / source_path).read_text()
            self.assertNotIn("base_rear_axle", source_path + source)
            self.assertNotIn("base_footprint", source_path + source)

    def test_legacy_navsat_is_separate_from_e6_gnss_contract(self):
        supplemental = self.registry["simulation_scope"]["supplemental_transforms"][
            "legacy_gnss_sim_link"
        ]
        self.assertEqual(supplemental["parent"], "base_chassis_link")
        self.assertIn("not an E6 antenna phase-center model", supplemental["role"])
        self.assertFalse(
            self.registry["vehicle_mode_policy"]["allow_simulation_nominal_values"]
        )

    def test_integrated_backend_reuses_the_canonical_simulation_ros_stack(self):
        backend = (
            ROOT / "ros2_ws/src/avl_bringup/launch/backend_sim.launch.py"
        ).read_text()
        bridge = (
            ROOT / "ros2_ws/src/avl_bringup/launch/sim_bridge.launch.py"
        ).read_text()

        self.assertIn("IncludeLaunchDescription", backend)
        self.assertIn("sim_bridge.launch.py", backend)
        self.assertIn("OnProcessStart(target_action=server", backend)
        self.assertIn("package='ros_gz_sim'", bridge)
        self.assertIn("pacmod_mock.py", bridge)
        self.assertIn("parameter_bridge", bridge)
        for duplicated_runtime_owner in (
            "package='ros_gz_sim'",
            "package='controller_manager'",
            "package='ros_gz_bridge'",
            "pacmod_mock.py",
        ):
            with self.subTest(owner=duplicated_runtime_owner):
                self.assertNotIn(duplicated_runtime_owner, backend)


if __name__ == "__main__":
    unittest.main()
