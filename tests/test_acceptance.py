"""Rest acceptance must tolerate slow simulation without accepting stale data."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ros2_ws/src/agile_navigation/scripts'))
from acceptance_logic import RestWindow


class RestTests(unittest.TestCase):
    def test_slow_fresh_feedback_can_establish_rest(self):
        rest=RestWindow();rest.start()
        for i in range(6):rest.observe(i*.033,0,i*.33)
        self.assertTrue(rest.ready(1.66))

    def test_duplicate_stamps_do_not_establish_rest(self):
        rest=RestWindow();rest.start()
        for i in range(30):rest.observe(1,0,i*.1)
        self.assertFalse(rest.ready(3))

    def test_motion_resets_the_consecutive_window(self):
        rest=RestWindow();rest.start()
        for i in range(11):rest.observe(i,0,i*.1)
        self.assertTrue(rest.ready(1.01))
        rest.observe(12,.2,1.1)
        self.assertFalse(rest.ready(1.1))

    def test_missing_or_invalid_data_resets_rest(self):
        rest=RestWindow();rest.start()
        for i in range(11):rest.observe(i,0,i*.1)
        self.assertFalse(rest.ready(2))
        rest.observe(12,0,2)
        self.assertFalse(rest.ready(2))
        rest.observe(13,float('nan'),2.1)
        self.assertFalse(rest.ready(2.1))


if __name__=='__main__':unittest.main()
