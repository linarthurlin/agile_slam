#!/usr/bin/env python3
"""Estimate planar motion from simulated joint feedback, never truth odometry."""
import math
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import JointState
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster
from vehicle_math import curvature_from_front_angles, integrate


class WheelOdometry(Node):
    def __init__(self):
        super().__init__('wheel_odometry')
        self.wheelbase = self.declare_parameter('wheelbase', 1.75).value
        self.track = self.declare_parameter('track', 1.2).value
        self.radius = self.declare_parameter('wheel_radius', 0.295).value
        self.rear_x = self.declare_parameter('rear_axle_x', -0.87).value
        self.x, self.y, self.yaw = self.rear_x, 0.0, 0.0
        self.last_stamp = None
        self.publisher = self.create_publisher(Odometry, '/odometry/wheel', 10)
        self.broadcaster = TransformBroadcaster(self)
        self.create_subscription(JointState, '/joint_states', self.update, qos_profile_sensor_data)

    def update(self, msg):
        required = ('rear_left_wheel_joint', 'rear_right_wheel_joint', 'left_steering_hinge_joint', 'right_steering_hinge_joint')
        if not all(name in msg.name for name in required):
            return
        index = {name: msg.name.index(name) for name in required}
        if len(msg.velocity) != len(msg.name) or len(msg.position) != len(msg.name):
            return
        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        speed = self.radius * (msg.velocity[index[required[0]]] + msg.velocity[index[required[1]]]) / 2
        left, right = msg.position[index[required[2]]], msg.position[index[required[3]]]
        yaw_rate = speed * curvature_from_front_angles(left, right, self.wheelbase, self.track)
        if self.last_stamp is not None:
            dt = stamp - self.last_stamp
            if dt < 0:
                self.x, self.y, self.yaw = self.rear_x, 0.0, 0.0
            elif dt <= 0.5:
                self.x, self.y, self.yaw = integrate(self.x, self.y, self.yaw, speed, yaw_rate, dt)
        self.last_stamp = stamp
        odom = Odometry()
        odom.header.stamp = msg.header.stamp
        odom.header.frame_id = 'odom'
        odom.child_frame_id = 'base_rear_axle'
        odom.pose.pose.position.x, odom.pose.pose.position.y = self.x, self.y
        odom.pose.pose.orientation.z = math.sin(self.yaw/2)
        odom.pose.pose.orientation.w = math.cos(self.yaw/2)
        odom.twist.twist.linear.x, odom.twist.twist.angular.z = speed, yaw_rate
        # Engineering placeholders, not measured uncertainty estimates.
        for i in (0, 7, 35):
            odom.pose.covariance[i] = 0.01
            odom.twist.covariance[i] = 0.01
        for i in (14, 21, 28):
            odom.pose.covariance[i] = 1e3
            odom.twist.covariance[i] = 1e3
        self.publisher.publish(odom)
        transform = TransformStamped()
        transform.header = odom.header
        transform.child_frame_id = 'base_footprint'
        transform.transform.translation.x = self.x - self.rear_x * math.cos(self.yaw)
        transform.transform.translation.y = self.y - self.rear_x * math.sin(self.yaw)
        transform.transform.rotation = odom.pose.pose.orientation
        self.broadcaster.sendTransform(transform)


def main():
    rclpy.init()
    node = WheelOdometry()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
