#!/usr/bin/env python3
"""Exercise the simulation PACMod contract; never run on a physical vehicle."""
import json
import math
import time
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import Twist
from std_srvs.srv import SetBool
from pacmod2_msgs.msg import VehicleSpeedRpt,GlobalRpt

def main():
    rclpy.init();node=Node('pacmod_runtime_checker')
    state={'ready':False,'speed':0.,'enabled':None,'mock':{},'control':{}}
    node.create_subscription(String,'/system/readiness',lambda m:state.update(ready=json.loads(m.data)['ready']),10)
    node.create_subscription(String,'/pacmod/mock/status',lambda m:state.update(mock=json.loads(m.data)),10)
    node.create_subscription(String,'/vehicle/control_status',lambda m:state.update(control=json.loads(m.data)),10)
    node.create_subscription(VehicleSpeedRpt,'/pacmod/vehicle_speed_rpt',lambda m:state.update(speed=m.vehicle_speed),10)
    node.create_subscription(GlobalRpt,'/pacmod/global_rpt',lambda m:state.update(enabled=m.enabled),10)
    publisher=node.create_publisher(Twist,'/cmd_vel',10)
    results={}
    def wait(predicate,seconds=10,speed=None):
        deadline=time.monotonic()+seconds;next_publish=0.
        while time.monotonic()<deadline:
            now=time.monotonic()
            if speed is not None and now>=next_publish:
                msg=Twist();msg.linear.x=speed;publisher.publish(msg);next_publish=now+.05
            rclpy.spin_once(node,timeout_sec=.02)
            if predicate():return True
        return False
    def service(name,value):
        client=node.create_client(SetBool,'/pacmod/mock/'+name)
        if not client.wait_for_service(timeout_sec=10):raise RuntimeError('Mock service unavailable: '+name)
        req=SetBool.Request();req.data=value;future=client.call_async(req)
        rclpy.spin_until_future_complete(node,future,timeout_sec=10)
        node.destroy_client(client)
        return bool(future.done() and future.result() and future.result().success)
    try:
        if not wait(lambda:state['ready'],120):raise RuntimeError('Runtime did not become ready.')
        endpoint=node.get_publishers_info_by_topic('/simulation/actuation')
        results['private_actuation_only_mock']=len(endpoint)==1 and endpoint[0].node_name=='pacmod_mock'
        results['no_legacy_bypass']=not node.get_publishers_info_by_topic('/ackermann_cmd') and not any(n=='twist_to_ackermann' for n,_ in node.get_node_names_and_namespaces())
        service('enable',False);wait(lambda:state['enabled'] is False)
        wait(lambda:False,1,speed=.3)
        results['disabled_no_motion']=abs(state['speed'])<.02
        results['explicit_enable']=service('enable',True)
        results['closed_loop_motion']=wait(lambda:state['speed']>.15,15,speed=.3)
        results['command_expiry_stop']=wait(lambda:abs(state['speed'])<.02 and state['control'].get('state')=='inhibited',12)
        service('enable',True)
        wait(lambda:state['speed']>.1,12,speed=.3)
        service('override',True)
        results['override_stop']=wait(lambda:state['enabled'] is False and abs(state['speed'])<.02,10)
        service('override',False);wait(lambda:False,1,speed=.3)
        results['override_clear_no_auto_enable']=state['enabled'] is False and abs(state['speed'])<.02
        service('enable',True);wait(lambda:state['speed']>.1,12,speed=.3)
        service('fault',True)
        results['fault_stop']=wait(lambda:state['enabled'] is False and abs(state['speed'])<.02,10)
        service('fault',False);wait(lambda:False,1,speed=.3)
        results['fault_clear_no_auto_enable']=state['enabled'] is False and abs(state['speed'])<.02
        service('enable',True);wait(lambda:state['speed']>.1,12,speed=.3)
        wait(lambda:False,.3,speed=float('nan'))
        results['invalid_setpoint_stop']=wait(lambda:abs(state['speed'])<.02,10)
        service('report_valid',False)
        results['invalid_report_inhibits']=wait(lambda:state['ready'] is False and state['enabled'] is False and abs(state['speed'])<.02,12)
        service('report_valid',True)
        service('enable',False)
        results['final_disabled_rest']=wait(lambda:state['enabled'] is False and abs(state['speed'])<.02,10)
        print(json.dumps({'passed':all(results.values()),'checks':results,'final':state,'scope':'ROS mock contract, no CAN/firmware or measured vehicle dynamics.'},indent=2))
        return 0 if all(results.values()) else 1
    finally:
        node.destroy_node()
        if rclpy.ok():rclpy.shutdown()

if __name__=='__main__':raise SystemExit(main())
