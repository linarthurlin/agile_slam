#!/usr/bin/env python3
"""Observe split-runtime readiness or explicitly toggle simulation actuation."""
import argparse
import json
import time
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from std_srvs.srv import SetBool

def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('ready','inhibited','enable','disable'));args=parser.parse_args()
    rclpy.init();node=Node('runtime_probe');state={'system':{},'mock':{},'control':{}}
    for key,topic in (('system','/system/readiness'),('mock','/pacmod/mock/status'),('control','/vehicle/control_status')):
        node.create_subscription(String,topic,lambda m,key=key:state.update({key:json.loads(m.data)}),10)
    deadline=time.monotonic()+120
    success=False
    while time.monotonic()<deadline:
        rclpy.spin_once(node,timeout_sec=.05)
        if args.action in ('ready','enable') and state['system'].get('ready'):success=True;break
        if args.action=='inhibited' and state['control'].get('inhibited') is True and state['system'].get('fault_latched'):success=True;break
        if args.action=='disable' and state['mock']:success=True;break
    if success and args.action in ('enable','disable'):
        client=node.create_client(SetBool,'/pacmod/mock/enable');success=client.wait_for_service(timeout_sec=10)
        if success:
            req=SetBool.Request();req.data=args.action=='enable';future=client.call_async(req)
            rclpy.spin_until_future_complete(node,future,timeout_sec=10)
            success=bool(future.done() and future.result() and future.result().success)
            deadline=time.monotonic()+5
            while success and time.monotonic()<deadline:
                rclpy.spin_once(node,timeout_sec=.05)
                if state['mock'].get('enabled')==req.data:break
            success=success and state['mock'].get('enabled')==req.data
    print(json.dumps({'passed':success,'action':args.action,'state':state,'graph':sorted(name for name,_ in node.get_node_names_and_namespaces())},indent=2))
    node.destroy_node();rclpy.shutdown();return 0 if success else 1
if __name__=='__main__':raise SystemExit(main())
