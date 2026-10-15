#!/usr/bin/env python3
"""Check wheel-feedback speed and truth drift after a completed simulation goal."""
import json
import math
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from nav_msgs.msg import Odometry

def main():
    rclpy.init()
    node=Node('motion_stop_checker')
    speeds=[];poses=[]
    node.create_subscription(Odometry,'/odometry/wheel',lambda m:speeds.append(abs(m.twist.twist.linear.x)),10)
    node.create_subscription(Odometry,'/ground_truth/odometry',lambda m:poses.append((m.pose.pose.position.x,m.pose.pose.position.y)),qos_profile_sensor_data)
    deadline=time.monotonic()+10
    while time.monotonic()<deadline:rclpy.spin_once(node,timeout_sec=.05)
    drift=max((math.hypot(x-poses[0][0],y-poses[0][1]) for x,y in poses),default=None)
    maximum=max(speeds,default=None)
    passed=len(speeds)>=10 and len(poses)>=10 and maximum<.02 and drift<.01
    print(json.dumps({'passed':passed,'wall_window_s':10,'wheel_samples':len(speeds),'truth_samples':len(poses),'max_wheel_speed_mps':maximum,'max_truth_drift_m':drift,'scope':'Post-goal rest check; not stopping-distance validation.'},indent=2))
    node.destroy_node();rclpy.shutdown()
    return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
