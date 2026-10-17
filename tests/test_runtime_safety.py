"""Fault latch, heartbeat lease and asynchronous command-cycle regressions."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'ros2_ws/src/agile_navigation/scripts'))
sys.path.insert(0, str(ROOT/'ros2_ws/src/agile_vehicle/scripts'))
from readiness_state import ReadinessState
from control_logic import ReadinessLease, CommandBundle


class LifecycleTests(unittest.TestCase):
    def test_late_startup_cannot_clear_clock_rewind_fault(self):
        state = ReadinessState()
        state.trip()
        self.assertFalse(state.complete_startup(True))
        self.assertTrue(state.failed)
        self.assertFalse(state.active)

    def test_failed_startup_stays_latched_after_later_success(self):
        state = ReadinessState()
        self.assertFalse(state.complete_startup(False))
        self.assertFalse(state.complete_startup(True))

    def test_success_then_trip_requires_new_state(self):
        state = ReadinessState()
        self.assertTrue(state.complete_startup(True))
        state.trip()
        self.assertFalse(state.complete_startup(True))
        self.assertTrue(ReadinessState().complete_startup(True))


class LeaseTests(unittest.TestCase):
    def test_requires_live_heartbeat_even_with_retained_permission(self):
        lease = ReadinessLease(.5)
        self.assertFalse(lease.permit(0))
        self.assertTrue(lease.receive('a', 1, True, 0))
        self.assertTrue(lease.permit(.1))
        self.assertFalse(lease.permit(.6))
        self.assertTrue(lease.fault_latched)

    def test_recovery_does_not_automatically_resume(self):
        lease = ReadinessLease(.5)
        lease.receive('a', 1, True, 0)
        lease.permit(.1)
        lease.permit(.6)
        lease.receive('a', 2, True, .7)
        self.assertFalse(lease.permit(.8))
        self.assertTrue(lease.rearm(.8))
        self.assertTrue(lease.permit(.9))

    def test_duplicate_and_out_of_order_messages_do_not_renew(self):
        lease = ReadinessLease(.5)
        lease.receive('a', 2, True, 0)
        self.assertFalse(lease.receive('a', 2, True, .4))
        self.assertFalse(lease.receive('a', 1, True, .4))
        self.assertFalse(lease.permit(.6))

    def test_new_producer_session_requires_reenable(self):
        lease = ReadinessLease(.5)
        lease.receive('a', 10, True, 0)
        lease.permit(.1)
        lease.receive('b', 1, True, .2)
        self.assertFalse(lease.permit(.3))
        self.assertTrue(lease.rearm(.3))
        self.assertTrue(lease.permit(.4))

    def test_not_ready_and_stale_lease_cannot_rearm(self):
        lease = ReadinessLease(.5)
        lease.receive('a', 1, False, 0)
        self.assertFalse(lease.rearm(.1))
        lease.receive('a', 2, True, .2)
        self.assertFalse(lease.rearm(.8))

    def test_malformed_heartbeat_does_not_grant_permission(self):
        lease = ReadinessLease(.5)
        for session,sequence,ready in [('',1,True),('a',True,True),('a',1,'true'),('a',0,True)]:
            self.assertFalse(lease.receive(session,sequence,ready,0))
        self.assertFalse(lease.permit(0))


class CommandCycleTests(unittest.TestCase):
    def test_one_cycle_topic_skew_does_not_starve(self):
        bundle = CommandBundle()
        bundle.push('accel',1,.2,0)
        frames = []
        for cycle in range(1,61):
            for key,stamp,value in [('accel',cycle+1,.2),('brake',cycle,0),('steer',cycle,(0,1))]:
                frame = bundle.push(key,stamp,value,cycle*.02)
                if frame is not None:
                    frames.append(frame)
        self.assertEqual(len(frames),60)

    def test_committed_stamp_cannot_mix_new_brake_with_old_accelerator(self):
        bundle = CommandBundle()
        for key,value in [('accel',.2),('brake',0),('steer',(0,1))]:
            bundle.push(key,10,value,0)
        self.assertIsNone(bundle.push('brake',10,.4,.1))
        self.assertIsNone(bundle.push('accel',10,0,.1))

    def test_pending_cycles_are_bounded(self):
        bundle = CommandBundle(max_pending=3)
        for stamp in range(20):
            bundle.push('accel',stamp,.2,stamp*.001)
        self.assertEqual(len(bundle.pending),3)

    def test_expired_partial_cycle_cannot_be_committed(self):
        bundle = CommandBundle(max_age=.5)
        bundle.push('accel',1,.2,0)
        bundle.push('brake',1,0,.6)
        self.assertIsNone(bundle.push('steer',1,(0,1),.6))

    def test_old_cycle_after_new_commit_is_ignored(self):
        bundle = CommandBundle()
        for key,value in [('accel',.2),('brake',0),('steer',(0,1))]:
            bundle.push(key,20,value,0)
        self.assertIsNone(bundle.push('accel',19,.8,.1))
        bundle.reset()
        for key,value in [('accel',0),('brake',.4),('steer',(0,1))]:
            frame = bundle.push(key,0,value,.2)
        self.assertEqual(frame['brake'],.4)


if __name__ == '__main__':
    unittest.main()
