#!/usr/bin/env python3
"""Exercise simulator drive commands and verify command expiry at the output."""
import json
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from ackermann_msgs.msg import AckermannDrive
from std_msgs.msg import Float64MultiArray
from nav_msgs.msg import Odometry


def main():
    rclpy.init()
    node = Node('sim_command_checker')
    node.set_parameters([rclpy.parameter.Parameter('use_sim_time', value=True)])
    wheels = []
    poses = []
    node.create_subscription(Float64MultiArray, '/left_rear_wheel_controller/commands', lambda msg: wheels.append((node.get_clock().now().nanoseconds / 1e9, msg.data[0])), 10)
    node.create_subscription(Odometry, '/ground_truth/odometry', lambda msg: poses.append((msg.pose.pose.position.x, msg.pose.pose.position.y)), qos_profile_sensor_data)
    publisher = node.create_publisher(AckermannDrive, '/ackermann_cmd', 10)
    warmup = time.monotonic() + 3
    while time.monotonic() < warmup:
        rclpy.spin_once(node, timeout_sec=0.05)
    if publisher.get_subscription_count() != 1:
        raise RuntimeError('Expected exactly one simulator command subscriber.')
    start_pose = poses[-1] if poses else None
    command = AckermannDrive()
    command.speed = 0.5
    command.steering_angle = 0.1
    moving_until = time.monotonic() + 2
    while time.monotonic() < moving_until:
        publisher.publish(command)
        rclpy.spin_once(node, timeout_sec=0.05)
    stopped_at = node.get_clock().now().nanoseconds / 1e9
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.05)
        if node.get_clock().now().nanoseconds / 1e9 > stopped_at + 1.0:
            break
    nonzero = [value for stamp, value in wheels if stamp <= stopped_at and abs(value) > 0.01]
    expired = [value for stamp, value in wheels if stamp > stopped_at + 0.6]
    passed = bool(nonzero) and bool(expired) and all(abs(value) < 1e-6 for value in expired)
    print(json.dumps({'passed': passed, 'nonzero_command_samples': len(nonzero), 'expired_command_samples': len(expired), 'expired_command_max_abs': max(map(abs, expired), default=None), 'start_pose': start_pose, 'end_pose': poses[-1] if poses else None}, indent=2))
    node.destroy_node()
    rclpy.shutdown()
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
