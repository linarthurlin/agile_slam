#!/usr/bin/env python3
"""Send one navigation goal and report odometry/path/command observations."""
import json
import math
import time
from pathlib import Path as FilePath
from ament_index_python.packages import get_package_share_directory
from vehicle_math import footprint_overlaps_box, footprint_overlaps_polygon
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import Odometry, Path
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist
from std_msgs.msg import String
from rclpy.qos import qos_profile_sensor_data


def main():
    rclpy.init()
    node = Node('navigation_checker')
    gx = node.declare_parameter('goal_x', 3.0).value
    gy = node.declare_parameter('goal_y', 0.0).value
    goal_yaw = node.declare_parameter('goal_yaw', 0.0).value
    cfg=json.loads((FilePath(get_package_share_directory('gem_description'))/'config/vehicle.json').read_text())
    timeout = node.declare_parameter('timeout', 150.0).value
    observed = {'odom': None, 'commands': 0, 'path_points': 0, 'scans': 0, 'max_lateral_odom': 0.0, 'truth_rear_pose': None, 'truth_yaw': None, 'speed': None, 'rest_samples': 0, 'positive_turn_commands': 0, 'negative_turn_commands': 0, 'truth_samples': 0, 'footprint_overlap_samples': 0}
    scene_path=node.declare_parameter('scene_file',str(FilePath(get_package_share_directory('agile_navigation'))/'maps/navigation_scene.json')).value
    scene=json.loads(FilePath(scene_path).read_text())
    def truth(msg):
        pose=msg.pose.pose
        q=pose.orientation
        yaw=math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))
        x,y=pose.position.x,pose.position.y
        observed['truth_rear_pose']=[x+cfg['rear_axle_x']*math.cos(yaw),y+cfg['rear_axle_x']*math.sin(yaw)]
        observed['truth_yaw']=yaw
        observed['truth_samples']+=1
        if any(footprint_overlaps_polygon(x,y,yaw,b['polygon']) if 'polygon' in b else footprint_overlaps_box(x,y,yaw,b['center'],b['size']) for b in scene['obstacles']):
            observed['footprint_overlap_samples']+=1
    rest_observation=False
    odom_receipt=0.0
    def odometry(msg):
        nonlocal odom_receipt
        odom_receipt=time.monotonic()
        if rest_observation and abs(msg.twist.twist.linear.x)<.02:observed['rest_samples']+=1
        observed['speed']=msg.twist.twist.linear.x
        observed['odom'] = [msg.pose.pose.position.x, msg.pose.pose.position.y]
        observed['max_lateral_odom'] = max(observed['max_lateral_odom'], abs(msg.pose.pose.position.y))
    def command(msg):
        if msg.angular.z>.01:observed['positive_turn_commands']+=1
        if msg.angular.z<-.01:observed['negative_turn_commands']+=1
        if abs(msg.linear.x) > .01:
            observed['commands'] += 1
    def path(msg):
        observed['path_points'] = max(observed['path_points'],len(msg.poses))
    def scan(msg):
        observed['scans'] += 1
    for key,topic in (('readiness_diagnostics','/system/readiness'),('mock_diagnostics','/pacmod/mock/status')):
        node.create_subscription(String,topic,lambda msg,key=key:observed.update({key:json.loads(msg.data)}),10)
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
    request.pose.pose.orientation.z = math.sin(goal_yaw/2)
    request.pose.pose.orientation.w = math.cos(goal_yaw/2)
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
    # Hold observation after the action result; success must leave the vehicle at rest.
    rest_observation=True
    rest_deadline=time.monotonic()+3.0
    while time.monotonic()<rest_deadline:
        rclpy.spin_once(node,timeout_sec=.05)
    yaw_error=abs(math.atan2(math.sin(observed['truth_yaw']-goal_yaw),math.cos(observed['truth_yaw']-goal_yaw))) if observed['truth_yaw'] is not None else None
    final = observed['odom']
    error = math.hypot(final[0]-gx,final[1]-gy) if final else None
    truth_pose=observed['truth_rear_pose']
    truth_error=math.hypot(truth_pose[0]-gx,truth_pose[1]-gy) if truth_pose else None
    report = {'truth_goal_error_m': truth_error, 'truth_yaw_error_rad':yaw_error, 'goal_yaw_rad':goal_yaw, 'passed': time.monotonic()-odom_receipt<1.0 and observed['rest_samples']>10 and observed['speed'] is not None and abs(observed['speed'])<.02 and yaw_error is not None and yaw_error<=.35 and observed['truth_samples'] > 0 and observed['footprint_overlap_samples'] == 0 and status == 4 and error is not None and error <= .4 and truth_error is not None and truth_error <= .4 and observed['commands'] > 0 and observed['path_points'] > 0, 'action_status': status, 'goal': [gx,gy], 'initial_odom': initial, 'final_odom': final, 'goal_error_m': error, 'wall_duration_s': time.monotonic()-started, **{k:v for k,v in observed.items() if k!='odom'}}
    print(json.dumps(report,indent=2))
    node.destroy_node()
    rclpy.shutdown()
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
