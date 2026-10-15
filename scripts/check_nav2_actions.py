#!/usr/bin/env python3
"""Verify cancel/occupied-goal behavior against an already running city profile."""
import json
import time
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import Twist


def main():
    rclpy.init()
    node=Node('nav2_action_checker')
    client=ActionClient(node,NavigateToPose,'/navigate_to_pose')
    commands=[]
    node.create_subscription(Twist,'/cmd_vel',lambda msg: commands.append((time.monotonic(),msg.linear.x,msg.angular.z)),10)
    def spin(seconds):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:rclpy.spin_once(node,timeout_sec=.05)
    def request(x,y):
        goal=NavigateToPose.Goal()
        goal.pose.header.frame_id='map'
        goal.pose.pose.position.x=x;goal.pose.pose.position.y=y
        goal.pose.pose.orientation.w=1.
        future=client.send_goal_async(goal)
        rclpy.spin_until_future_complete(node,future,timeout_sec=10)
        if not future.done() or not future.result() or not future.result().accepted:
            raise RuntimeError('Goal was not accepted.')
        return future.result()
    if not client.wait_for_server(timeout_sec=30):raise RuntimeError('Nav2 unavailable.')
    handle=request(30.,0.)
    result=handle.get_result_async()
    spin(5)
    cancel=handle.cancel_goal_async()
    rclpy.spin_until_future_complete(node,cancel,timeout_sec=10)
    rclpy.spin_until_future_complete(node,result,timeout_sec=20)
    spin(3)
    cancel_status=result.result().status if result.done() else None
    stopped=bool(commands) and abs(commands[-1][1])<1e-4 and abs(commands[-1][2])<1e-4
    commands.clear()
    handle=request(0.,10.)  # Outside the navigable road corridor.
    result=handle.get_result_async()
    rclpy.spin_until_future_complete(node,result,timeout_sec=30)
    occupied_status=result.result().status if result.done() else None
    if not result.done():
        future=handle.cancel_goal_async()
        rclpy.spin_until_future_complete(node,future,timeout_sec=5)
    nonzero=sum(abs(v)>.01 or abs(w)>.01 for _,v,w in commands)
    report={'passed':cancel_status==5 and stopped and occupied_status==6 and nonzero==0,
            'cancel_status':cancel_status,'zero_command_after_cancel':stopped,
            'occupied_goal_status':occupied_status,'occupied_goal_nonzero_commands':nonzero,
            'scope':'Action cancellation and command output only; not a physical braking test.'}
    print(json.dumps(report,indent=2))
    node.destroy_node()
    rclpy.shutdown()
    return 0 if report['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
