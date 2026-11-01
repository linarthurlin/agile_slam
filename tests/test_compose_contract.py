"""Guard the separation between deployable runtime and editor tooling images."""
from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]


class ComposeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = yaml.safe_load((ROOT / "compose.yaml").read_text())
        cls.simulation = yaml.safe_load((ROOT / "compose.sim.yaml").read_text())
        cls.development = yaml.safe_load((ROOT / "compose.dev.yaml").read_text())

    def test_runtime_services_build_the_minimal_runtime_target(self):
        autonomy = self.runtime["services"]["autonomy"]
        self.assertEqual(autonomy["build"]["target"], "runtime")
        self.assertEqual(autonomy["image"], "agile_slam:humble")

    def test_devcontainer_keeps_its_separate_development_target(self):
        dev = self.development["services"]["dev"]
        self.assertEqual(dev["build"]["target"], "dev")
        self.assertEqual(dev["image"], "agile_slam:dev-humble")
        self.assertEqual(dev["volumes"][0], ".:/workspaces/Agile_SLAM:cached")

    def test_split_simulation_waits_for_gazebo_and_autonomy(self):
        sim_bridge = self.simulation["services"]["sim-bridge"]
        self.assertEqual(
            sim_bridge["depends_on"]["gazebo"]["condition"], "service_healthy"
        )
        self.assertEqual(
            sim_bridge["depends_on"]["autonomy"]["condition"], "service_started"
        )
        self.assertEqual(
            sim_bridge["command"],
            ["ros2", "launch", "avl_bringup", "sim_bridge.launch.py"],
        )


if __name__ == "__main__":
    unittest.main()
