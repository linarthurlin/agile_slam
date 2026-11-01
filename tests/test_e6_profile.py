"""Regression checks for the pending and calibrated GEM e6 frame profiles."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from e6_profile import inspect_profile, load_profile, render_sensor_xacro  # noqa: E402


def calibrated_fixture():
    inventory, calibration, driver_matrix = load_profile()
    inventory = deepcopy(inventory)
    calibration = deepcopy(calibration)
    driver_matrix = deepcopy(driver_matrix)

    calibration["status"] = "validated"
    calibration["frames"]["base_link"]["geometry_status"] = "validated"
    translations = {
        "livox_mount_link": [0.0, 0.0, 1.5],
        "livox_fl_link": [0.4, -0.3, 0.0],
        "livox_fc_link": [0.4, 0.0, 0.0],
        "livox_fr_link": [0.4, 0.3, 0.0],
        "top_sensor_rig_link": [0.0, 0.0, 1.8],
        "velodyne_link": [0.0, 0.0, 0.2],
        "gnss_main_link": [-0.2, 0.0, 0.4],
        "gnss_slave_link": [-0.8, 0.0, 0.4],
        "realsense_link": [0.5, 0.0, 1.0],
    }
    camera_xy = {
        "fl": [0.8, 0.6], "fr": [0.8, -0.6],
        "cl": [0.0, 0.6], "cr": [0.0, -0.6],
        "rl": [-0.8, 0.6], "rr": [-0.8, -0.6],
    }
    for side, xy in camera_xy.items():
        translations[f"avt_cam_{side}_link"] = [xy[0], xy[1], 0.0]
    for name, entry in calibration["frames"].items():
        if name == "base_link":
            continue
        if name == "realsense_wrapper_children":
            entry["frame_ids"] = [
                "realsense_color_optical_frame", "realsense_depth_optical_frame",
                "realsense_gyro_frame", "realsense_accel_frame", "realsense_imu_frame",
            ]
            entry["status"] = "validated"
            continue
        if name in translations:
            entry["translation_m"] = translations[name]
            if name != "livox_mount_link" and name != "top_sensor_rig_link":
                entry["rotation_rpy_rad"] = [0.0, 0.0, 0.0]
        elif name.endswith("_optical_frame"):
            entry["status"] = "defined_by_convention"
            continue
        entry["status"] = "validated"
        entry["rotation_rpy_rad"] = [0.0, 0.0, 0.0]

    for row in inventory:
        sensor_id = row["sensor_id"]
        row["hardware_status"] = "validated"
        row["manufacturer"] = "synthetic-manufacturer"
        row["serial"] = f"synthetic-{sensor_id}"
        row["model"] = "synthetic-model"
        row["firmware"] = "synthetic-1"
        row["network_or_port"] = "synthetic-endpoint"
        if row["driver_status"] != "not_applicable":
            row["driver_status"] = "validated"
        if row["extrinsic_status"] != "not_applicable":
            row["extrinsic_status"] = "validated"
        if sensor_id == "realsense":
            row["message_frame_id"] = ";".join([
                "/sensors/realsense/color/image_raw=realsense_color_optical_frame",
                "/sensors/realsense/color/camera_info=realsense_color_optical_frame",
                "/sensors/realsense/depth/image_rect_raw=realsense_depth_optical_frame",
                "/sensors/realsense/depth/camera_info=realsense_depth_optical_frame",
                "/sensors/realsense/gyro/sample=realsense_gyro_frame",
                "/sensors/realsense/accel/sample=realsense_accel_frame",
                "/sensors/realsense/imu=realsense_imu_frame",
            ])

    driver_matrix["status"] = "validated"
    for entry in driver_matrix["drivers"]:
        entry["status"] = "validated"
        entry["version_or_commit"] = "synthetic-test-revision"
    for entry in driver_matrix["clock_sources"].values():
        entry["status"] = "validated"
    for name, entry in driver_matrix["bandwidth"].items():
        if isinstance(entry, dict):
            entry["status"] = "validated"
        else:
            driver_matrix["bandwidth"][name] = {"status": "validated", "basis": "synthetic test"}
    return inventory, calibration, driver_matrix


class E6ProfileTests(unittest.TestCase):
    def test_checked_in_profile_has_consistent_contract_but_is_not_ready(self):
        inventory, calibration, driver_matrix = load_profile()
        report = inspect_profile(inventory, calibration, driver_matrix)
        self.assertEqual(report.contract_errors, [])
        self.assertTrue(report.calibration_issues)
        self.assertTrue(report.integration_issues)
        self.assertFalse(report.integration_ready)

    def test_generator_refuses_pending_hardware_calibration(self):
        inventory, calibration, driver_matrix = load_profile()
        with self.assertRaisesRegex(ValueError, "Refusing to generate uncalibrated sensor frames"):
            render_sensor_xacro(inventory, calibration, driver_matrix)

    def test_generator_refuses_when_system_integration_gates_are_pending(self):
        inventory, calibration, driver_matrix = calibrated_fixture()
        driver_matrix["clock_sources"]["preferred_vehicle_clock"]["status"] = "pending_measurement"
        with self.assertRaisesRegex(ValueError, "before driver/clock/bandwidth gates pass"):
            render_sensor_xacro(inventory, calibration, driver_matrix)

    def test_calibrated_profile_generates_expected_tf_links_and_parents(self):
        inventory, calibration, driver_matrix = calibrated_fixture()
        report = inspect_profile(inventory, calibration, driver_matrix)
        self.assertEqual(report.contract_errors, [])
        self.assertEqual(report.calibration_issues, [])
        self.assertEqual(report.integration_issues, [])
        xml = render_sensor_xacro(inventory, calibration, driver_matrix)
        robot = ET.fromstring(xml)
        links = {link.get("name") for link in robot.findall("link")}
        self.assertIn("top_sensor_rig_link", links)
        self.assertIn("velodyne_link", links)
        self.assertIn("gnss_main_link", links)
        self.assertIn("avt_cam_fl_optical_frame", links)
        self.assertNotIn("imu_link", links)
        parents = {
            joint.find("child").get("link"): joint.find("parent").get("link")
            for joint in robot.findall("joint")
        }
        self.assertEqual(parents["velodyne_link"], "top_sensor_rig_link")
        self.assertEqual(parents["gnss_main_link"], "top_sensor_rig_link")
        self.assertEqual(parents["avt_cam_fl_link"], "top_sensor_rig_link")

    def test_uninstalled_optional_slave_is_omitted_from_generated_tree(self):
        inventory, calibration, driver_matrix = calibrated_fixture()
        slave = next(row for row in inventory if row["sensor_id"] == "gnss_slave")
        slave["hardware_status"] = "not_installed"
        slave["driver_status"] = "not_applicable"
        slave["extrinsic_status"] = "not_applicable"
        calibration["frames"]["gnss_slave_link"]["status"] = "not_installed"
        report = inspect_profile(inventory, calibration, driver_matrix)
        self.assertEqual(report.calibration_issues, [])
        robot = ET.fromstring(render_sensor_xacro(inventory, calibration, driver_matrix))
        links = {link.get("name") for link in robot.findall("link")}
        self.assertNotIn("gnss_slave_link", links)

    def test_wrong_sensor_parent_is_rejected(self):
        inventory, calibration, driver_matrix = calibrated_fixture()
        calibration["frames"]["velodyne_link"]["parent"] = "base_link"
        report = inspect_profile(inventory, calibration, driver_matrix)
        self.assertTrue(any("velodyne_link must have parent 'top_sensor_rig_link'" in error for error in report.contract_errors))


if __name__ == "__main__":
    unittest.main()
