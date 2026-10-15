#!/usr/bin/env python3
"""Check that the baseline delivers sensor data and an isolated truth stream."""
import json
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import PointCloud2, Imu, Image, CameraInfo, JointState
from nav_msgs.msg import Odometry
from rosgraph_msgs.msg import Clock


def main():
    rclpy.init()
    node = Node('baseline_checker')
    received = {}
    subscriptions = []
    topics = {
        '/clock': Clock,
        '/sensors/velodyne/points': PointCloud2,
        '/sensors/imu/data_raw': Imu,
        '/sensors/cameras/front/image_raw': Image,
        '/sensors/cameras/front/camera_info': CameraInfo,
        '/ground_truth/odometry': Odometry,
        '/joint_states': JointState,
    }
    for topic, kind in topics.items():
        def callback(msg, topic=topic):
            record = received.setdefault(topic, {'count': 0})
            record['count'] += 1
            if hasattr(msg, 'header'):
                record['frame_id'] = msg.header.frame_id
            if isinstance(msg, PointCloud2):
                record['fields'] = [field.name for field in msg.fields]
                record['points'] = msg.width * msg.height
            if isinstance(msg, Imu):
                record['acceleration'] = [msg.linear_acceleration.x, msg.linear_acceleration.y, msg.linear_acceleration.z]
        qos = 10 if kind in (Image, PointCloud2) else qos_profile_sensor_data
        subscriptions.append(node.create_subscription(kind, topic, callback, qos))
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.2)
        if all(received.get(topic, {}).get('count', 0) >= 3 for topic in topics):
            break
    unexpected = [topic for topic in ('/odom', '/odometry/local') if node.count_publishers(topic)]
    success = all(received.get(topic, {}).get('count', 0) >= 3 for topic in topics) and not unexpected
    print(json.dumps({'passed': success, 'topics': received, 'unexpected_odometry_publishers': unexpected}, indent=2))
    node.destroy_node()
    rclpy.shutdown()
    return 0 if success else 1


if __name__ == '__main__':
    raise SystemExit(main())
