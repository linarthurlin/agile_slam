import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from check_gui import windows_present


class GuiTests(unittest.TestCase):
    def test_requires_actual_client_windows(self):
        tree='0xc "Gazebo": ("ign-gazebo-gui" "Gazebo GUI") 1000x845+0+0\n0xa "/gui/motion.rviz* - RViz": ("rviz2" "rviz2") 1200x850+0+0'
        self.assertTrue(all(windows_present(tree).values()))

    def test_dummy_selection_windows_do_not_count(self):
        self.assertFalse(any(windows_present('0xc "Gazebo GUI": () 1x1+0+0\n0xa "rviz2": () 1x1+0+0').values()))

    def test_missing_gazebo_is_not_dual_gui(self):
        self.assertEqual(windows_present('0xa "motion.rviz - RViz": () 1200x850+0+0'),{'gazebo':False,'rviz':True})
