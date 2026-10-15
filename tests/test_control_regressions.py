"""Regression checks for command expiry and transform lookup direction."""
import ast
import threading
import types
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / 'ros2_ws/src/gem_gazebo/scripts/gem_control.py'


def method(name, extra=None):
    tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
    controller = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'GEMController')
    node = next(node for node in controller.body if isinstance(node, ast.FunctionDef) and node.name == name)
    module = ast.Module(body=[node], type_ignores=[])
    scope = {'Float64MultiArray': lambda: types.SimpleNamespace(data=[])}
    scope.update(extra or {})
    exec(compile(module, str(SOURCE), 'exec'), scope)
    return scope[name]


class Stamp:
    def __init__(self, seconds):
        self.nanoseconds = int(seconds * 1e9)
    def __sub__(self, other):
        return Stamp((self.nanoseconds - other.nanoseconds) / 1e9)


class WatchdogTests(unittest.TestCase):
    def test_updates_do_not_refresh_command_age(self):
        stopped = []
        published = []
        clock = types.SimpleNamespace(now=lambda: Stamp(0.1))
        fake = types.SimpleNamespace(
            get_clock=lambda: clock, last_cmd_time=Stamp(0), last_update_time=Stamp(0),
            cmd_timeout=0.5, last_steer_ang=0.0, steer_ang=0.0,
            steer_ang_vel=0.0, speed=1.0, accel=0.0,
            ackermann_cmd_lock=threading.Lock(), theta_left=0.0, theta_right=0.0,
            left_front_ang_vel=0.0, right_front_ang_vel=0.0,
            left_rear_ang_vel=0.0, right_rear_ang_vel=0.0,
            control_steering=lambda *args: (False, 1e9),
            control_wheels=lambda speed, *args: stopped.append(speed),
        )
        for name in ('left_steer_pub', 'right_steer_pub', 'left_front_wheel_pub', 'right_front_wheel_pub', 'left_rear_wheel_pub', 'right_rear_wheel_pub'):
            setattr(fake, name, types.SimpleNamespace(publish=published.append))
        update = method('update')
        update(fake)
        clock.now = lambda: Stamp(0.6)
        update(fake)
        self.assertEqual(stopped, [1.0, 0.0])
        self.assertEqual(fake.last_cmd_time.nanoseconds, 0)
        self.assertEqual(fake.last_update_time.nanoseconds, 600000000)

    def test_clock_rewind_invalidates_stored_speed(self):
        fake = types.SimpleNamespace(
            get_clock=lambda: types.SimpleNamespace(now=lambda: Stamp(1)),
            last_cmd_time=Stamp(10), last_update_time=Stamp(10),
            speed=1.0, accel=0.5, ackermann_cmd_lock=threading.Lock(),
        )
        method('update')(fake)
        self.assertEqual(fake.speed, 0.0)
        self.assertEqual(fake.accel, 0.0)
        self.assertEqual(fake.last_cmd_time.nanoseconds, 1000000000)

    def test_geometry_waits_for_elapsed_deadline_not_spin_count(self):
        attempts = []
        elapsed = [0.0]
        def lookup(*args):
            attempts.append(args)
            if len(attempts) < 16:
                raise RuntimeError('TF not ready')
            return types.SimpleNamespace(transform=types.SimpleNamespace(
                translation=types.SimpleNamespace(x=1.75, y=0.0, z=0.0)))
        def spin(*args, **kwargs):
            elapsed[0] += 0.01
        fake = types.SimpleNamespace(
            right_rear_link='rear_right_wheel_link',
            tf_buffer=types.SimpleNamespace(lookup_transform=lookup),
            get_logger=lambda: types.SimpleNamespace(info=lambda message: None),
        )
        extra = {
            'time': types.SimpleNamespace(monotonic=lambda: elapsed[0]),
            'rclpy': types.SimpleNamespace(ok=lambda: True, spin_once=spin,
                time=types.SimpleNamespace(Time=lambda: None)),
            'np': types.SimpleNamespace(array=tuple),
        }
        result = method('get_link_position', extra)(fake, 'front_left_wheel_link')
        self.assertEqual(result, (1.75, 0.0, 0.0))
        self.assertEqual(len(attempts), 16)

    def test_tf_lookup_requests_reference_from_link(self):
        tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'lookup_transform']
        self.assertEqual(len(calls), 1)
        self.assertEqual([node.id for node in calls[0].args[:2]], ['reference_frame', 'link'])


if __name__ == '__main__':
    unittest.main()
