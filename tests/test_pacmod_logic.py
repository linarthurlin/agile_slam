"""Independent command-freshness, interlock, and enable-latch regressions."""
import json
import math
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'ros2_ws/src/agile_vehicle/scripts'))
from control_logic import SpeedController,MockState,CommandBundle
CFG=json.loads((ROOT/'ros2_ws/src/gem_description/config/vehicle.json').read_text())

class ControllerTests(unittest.TestCase):
    def test_receipt_expiry_is_not_refreshed_by_updates(self):
        c=SpeedController(CFG);c.command(.6,0,0)
        self.assertGreater(c.step(.1,0,.01,True,False)[0],0)
        for t in (.2,.4,.6):c.step(t,0,.01,True,False)
        accel,brake,_,_=c.step(.8,.4,.01,True,False)
        self.assertEqual(accel,0);self.assertGreater(brake,0)
    def test_disabled_invalid_or_stale_reports_stop(self):
        for enabled,age,inhibited,speed in ((False,0,False,0),(True,1,False,0),(True,0,True,0),(True,0,False,float('nan'))):
            c=SpeedController(CFG);c.command(.6,0,0)
            accel,brake,_,_=c.step(.1,speed,age,enabled,inhibited)
            self.assertEqual(accel,0);self.assertGreater(brake,0)
    def test_nonfinite_and_reverse_commands_are_rejected(self):
        for speed,yaw in ((float('nan'),0),(.5,float('inf')),(-.1,0)):
            c=SpeedController(CFG);self.assertFalse(c.command(speed,yaw,0))
            self.assertEqual(c.step(.1,0,0,True,False)[0],0)
    def test_speed_and_road_angle_are_bounded(self):
        c=SpeedController(CFG);c.command(5,10,0)
        self.assertEqual(c.target,.6);self.assertEqual(c.angle,.48)
    def test_outputs_are_mutually_exclusive(self):
        for measured in (0,.2,.59,.8):
            c=SpeedController(CFG);c.command(.6,0,0)
            a,b,_,_=c.step(.1,measured,0,True,False)
            self.assertEqual(a*b,0)

class MockTests(unittest.TestCase):
    def test_enable_requires_readiness_and_is_never_automatic(self):
        m=MockState();self.assertFalse(m.enable(True,False));self.assertFalse(m.enabled)
        self.assertTrue(m.enable(True,True));m.trip('fault');m.fault=False
        self.assertFalse(m.enabled);self.assertTrue(m.enable(True,True))
    def test_disabled_and_neutral_cannot_drive(self):
        m=MockState()
        self.assertEqual(m.advance(.1,.5,0,0,3,True,CFG)[0],0)
        m.enable(True,True)
        self.assertEqual(m.advance(.1,.5,0,0,3,True,CFG)[0],0)
    def test_motion_requires_forward_and_feedback_readiness(self):
        m=MockState();m.enable(True,True);m.shift(3,0)
        self.assertGreater(m.advance(.1,.5,0,0,3,True,CFG)[0],0)
        self.assertEqual(m.advance(.1,.5,0,0,3,False,CFG)[0],0)
        self.assertFalse(m.enabled);self.assertTrue(m.timeout)
    def test_fault_override_and_interlock_latch(self):
        for reason in ('fault','override'):
            m=MockState();m.enable(True,True);m.trip(reason)
            self.assertFalse(m.enabled);self.assertFalse(m.enable(True,True))
        m=MockState();m.enable(True,True);m.shift(3,0)
        self.assertEqual(m.advance(.1,.3,.3,0,3,True,CFG)[0],0)
        self.assertTrue(m.fault)
    def test_shift_while_moving_and_reverse_rejected(self):
        for gear,speed in ((1,0),(2,.3)):
            m=MockState();m.gear=3;m.enable(True,True)
            self.assertFalse(m.shift(gear,speed));self.assertFalse(m.enabled)
    def test_shaft_angle_rate_maps_to_road_angle(self):
        m=MockState();m.enable(True,True);m.shift(3,0)
        _,angle=m.advance(.1,0,0,7.68,3.2,True,CFG)
        self.assertAlmostEqual(angle,.02)
    def test_invalid_actuation_latches_fault(self):
        m=MockState();m.enable(True,True);m.shift(3,0)
        self.assertEqual(m.advance(.1,float('nan'),0,0,3,True,CFG)[0],0)
        self.assertTrue(m.fault)

class BundleTests(unittest.TestCase):
    def test_interleaved_brake_transition_is_atomic(self):
        b=CommandBundle()
        self.assertIsNone(b.push('accel',1,.3))
        self.assertIsNone(b.push('brake',1,0.))
        self.assertEqual(b.push('steer',1,(0.,3.))['accel'],.3)
        self.assertIsNone(b.push('brake',2,.4))
        self.assertIsNone(b.push('accel',2,0.))
        frame=b.push('steer',2,(0.,3.))
        self.assertEqual(frame['accel'],0);self.assertEqual(frame['brake'],.4)
    def test_old_command_cycle_cannot_replace_current_cycle(self):
        b=CommandBundle()
        for key in ('accel','brake','steer'):b.push(key,5,0)
        self.assertIsNone(b.push('accel',4,1))
        b.reset();self.assertIsNone(b.push('accel',0,0))

if __name__=='__main__':unittest.main()
