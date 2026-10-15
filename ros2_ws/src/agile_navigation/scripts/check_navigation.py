#!/usr/bin/env python3
"""Send one navigation goal and report odometry/path/command observations."""
import json
import math
import time
from pathlib import Path as FilePath
from ament_index_python.packages import get_package_share_directory
from vehicle_math import footprint_overlaps_box
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import Odometry, Path
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist
from rclpy.qos import qos_profile_sensor_data


def main():
    rclpy.init()
    node = Node('navigation_checker')
    gx = node.declare_parameter('goal_x', 3.0).value
    gy = node.declare_parameter('goal_y', 0.0).value
    timeout = node.declare_parameter('timeout', 150.0).value
    observed = {'odom': None, 'commands': 0, 'path_points': 0, 'scans': 0, 'max_lateral_odom': 0.0, 'truth_rear_pose': None, 'truth_samples': 0, 'footprint_overlap_samples': 0}
    scene=json.loads((FilePath(get_package_share_directory('agile_navigation'))/'maps/navigation_scene.json').read_text())
    def truth(msg):
        pose=msg.pose.pose
        q=pose.orientation
        yaw=math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))
        x,y=pose.position.x,pose.position.y
        observed['truth_rear_pose']=[x-.87*math.cos(yaw),y-.87*math.sin(yaw)]
        observed['truth_samples']+=1
        if any(footprint_overlaps_box(x,y,yaw,b['center'],b['size']) for b in scene['obstacles']):
            observed['footprint_overlap_samples']+=1
    def odometry(msg):
        observed['odom'] = [msg.pose.pose.position.x, msg.pose.pose.position.y]
        observed['max_lateral_odom'] = max(observed['max_lateral_odom'], abs(msg.pose.pose.position.y))
    def command(msg):
        if abs(msg.linear.x) > .01:
            observed['commands'] += 1
    def path(msg):
        observed['path_points'] = max(observed['path_points'],len(msg.poses))
    def scan(msg):
        observed['scans'] += 1
    # Ground truth is consumed here only by the evaluator, never the estimator/controller.
    node.create_subscription(Odometry, '/ground_truth/odometry', truth, qos_profile_sensor_data)
    node.create_subscription(Odometry, '/odometry/wheel', odometry, 10)
    node.create_subscription(Twist, '/cmd_vel', command, 10)
    node.create_subscription(Path, '/plan', path, 10)
    node.create_subscription(LaserScan, '/sensors/obstacle_scan', scan, qos_profile_sensor_data)
    client = ActionClient(node, NavigateToPose, '/navigate_to_pose')
    if not client.wait_for_server(timeout_sec=60):
        raise RuntimeError('Nav2 action server unavailable.')
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline and (observed['odom'] is None or not observed['scans']):
        rclpy.spin_once(node, timeout_sec=.1)
    if observed['odom'] is None or not observed['scans']:
        raise RuntimeError('Wheel odometry or obstacle scan unavailable.')
    initial = observed['odom'][:]
    request = NavigateToPose.Goal()
    request.pose.header.frame_id = 'map'
    request.pose.pose.position.x,request.pose.pose.position.y = gx,gy
    request.pose.pose.orientation.w = 1.0
    future = client.send_goal_async(request)
    rclpy.spin_until_future_complete(node,future,timeout_sec=10)
    if not future.done() or future.result() is None or not future.result().accepted:
        raise RuntimeError('Navigation goal not accepted.')
    handle = future.result()
    result = handle.get_result_async()
    started = time.monotonic()
    deadline = started+timeout
    while time.monotonic() < deadline and not result.done():
        rclpy.spin_once(node,timeout_sec=.1)
    status = result.result().status if result.done() else None
    if not result.done():
        cancel = handle.cancel_goal_async()
        rclpy.spin_until_future_complete(node,cancel,timeout_sec=5)
    final = observed['odom']
    error = math.hypot(final[0]-gx,final[1]-gy) if final else None
    truth_pose=observed['truth_rear_pose']
    truth_error=math.hypot(truth_pose[0]-gx,truth_pose[1]-gy) if truth_pose else None
    report = {'truth_goal_error_m': truth_error, 'passed': observed['truth_samples'] > 0 and observed['footprint_overlap_samples'] == 0 and status == 4 and error is not None and error <= .4 and observed['commands'] > 0 and observed['path_points'] > 0, 'action_status': status, 'goal': [gx,gy], 'initial_odom': initial, 'final_odom': final, 'goal_error_m': error, 'wall_duration_s': time.monotonic()-started, **{k:v for k,v in observed.items() if k!='odom'}}
    print(json.dumps(report,indent=2))
    node.destroy_node()
    rclpy.shutdown()
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
