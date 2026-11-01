#!/usr/bin/env python3
"""Verify actual stationary model and rear-axle origins before enabling motion."""
import argparse
import json
import math
from pathlib import Path
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from nav_msgs.msg import Odometry
from ament_index_python.packages import get_package_share_directory


def main():
    parser=argparse.ArgumentParser()
    for name in ('x','y','yaw'):parser.add_argument(name,type=float)
    args=parser.parse_args()
    if not all(math.isfinite(v) for v in (args.x,args.y,args.yaw)):parser.error('Nonfinite fixture')
    rclpy.init();node=Node('start_fixture_checker')
    cfg=json.loads((Path(get_package_share_directory('gem_description'))/'config/vehicle.json').read_text())
    rear_x=cfg['rear_axle_x']
    rear_pose=[args.x+rear_x*math.cos(args.yaw),args.y+rear_x*math.sin(args.yaw),args.yaw]
    expected={'truth':rear_pose,'odom':rear_pose}
    records={};receipts={};stamps={}
    def receive(msg,key):
        stamp=msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9
        if key in stamps and stamp<=stamps[key]:return
        p=msg.pose.pose;q=p.orientation
        yaw=math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))
        records[key]=[p.position.x,p.position.y,yaw,msg.twist.twist.linear.x]
        receipts[key]=time.monotonic();stamps[key]=stamp
    node.create_subscription(Odometry,'/ground_truth/odometry',lambda msg:receive(msg,'truth'),qos_profile_sensor_data)
    node.create_subscription(Odometry,'/odometry/wheel',lambda msg:receive(msg,'odom'),10)
    deadline=time.monotonic()+15
    while time.monotonic()<deadline and len(records)<2:rclpy.spin_once(node,timeout_sec=.1)
    errors={}
    for key,target in expected.items():
        if key not in records:continue
        value=records[key]
        errors[key]={'position_m':math.hypot(value[0]-target[0],value[1]-target[1]),'yaw_rad':abs(math.atan2(math.sin(value[2]-target[2]),math.cos(value[2]-target[2]))),'speed_mps':abs(value[3]),'age_s':time.monotonic()-receipts[key]}
    passed=len(errors)==2 and all(all(math.isfinite(v) for v in error.values()) and error['position_m']<.05 and error['yaw_rad']<.03 and error['speed_mps']<.02 and error['age_s']<1 for error in errors.values())
    print(json.dumps({'passed':passed,'expected':expected,'observed':records,'errors':errors,'scope':'Test-only truth preflight; no operational localization or control uses truth.'},indent=2))
    node.destroy_node();rclpy.shutdown()
    return 0 if passed else 1


if __name__=='__main__':raise SystemExit(main())
