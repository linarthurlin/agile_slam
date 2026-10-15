#!/usr/bin/env python3
"""Convert forward-only Nav2 Twist commands into bounded simulator commands."""
import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from ackermann_msgs.msg import AckermannDrive
from vehicle_math import steering_from_twist


class TwistToAckermann(Node):
    def __init__(self):
        super().__init__('twist_to_ackermann')
        self.wheelbase = self.declare_parameter('wheelbase', 1.75).value
        self.max_speed = self.declare_parameter('max_speed', 0.6).value
        self.max_steer = self.declare_parameter('max_steer', 0.48).value
        self.publisher = self.create_publisher(AckermannDrive, '/ackermann_cmd', 10)
        self.create_subscription(Twist, '/cmd_vel', self.update, 10)

    def update(self, msg):
        command = AckermannDrive()
        if math.isfinite(msg.linear.x) and math.isfinite(msg.angular.z):
            command.speed = max(0.0, min(self.max_speed, msg.linear.x))
            command.steering_angle = steering_from_twist(msg.linear.x, msg.angular.z, self.wheelbase, self.max_steer)
        self.publisher.publish(command)
        # No timer republishes stale commands: the simulator's expiry remains effective.


def main():
    rclpy.init()
    node = TwistToAckermann()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
