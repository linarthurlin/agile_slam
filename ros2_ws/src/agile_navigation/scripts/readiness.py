#!/usr/bin/env python3
"""Activate Nav2 only after ROS data/TF readiness; inhibit on backend loss."""
import json
import time
import rclpy
from rclpy.node import Node
from rclpy.clock import Clock,ClockType
from rclpy.qos import QoSProfile,DurabilityPolicy
from sensor_msgs.msg import PointCloud2
from nav_msgs.msg import Odometry,OccupancyGrid
from rosgraph_msgs.msg import Clock as ClockMessage
from pacmod2_msgs.msg import VehicleSpeedRpt
from std_msgs.msg import Bool,String
from nav2_msgs.srv import ManageLifecycleNodes
from action_msgs.srv import CancelGoal
from tf2_ros import Buffer,TransformListener

class Readiness(Node):
    def __init__(self):
        super().__init__('readiness')
        self.map_ready=False;self.times={};self.last_clock=None;self.active=False;self.starting=None;self.failed=False
        self.last_fault=None;self.report_valid=None
        self.buffer=Buffer();self.listener=TransformListener(self.buffer,self)
        self.inhibit=self.create_publisher(Bool,'/vehicle/inhibit',QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.status=self.create_publisher(String,'/system/readiness',10)
        self.manager=self.create_client(ManageLifecycleNodes,'/lifecycle_manager_navigation/manage_nodes')
        self.cancel=self.create_client(CancelGoal,'/navigate_to_pose/_action/cancel_goal')
        self.create_subscription(PointCloud2,'/sensors/velodyne/points',lambda msg:self.seen('cloud'),10)
        self.create_subscription(OccupancyGrid,'/map',self.map,QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.create_subscription(Odometry,'/odometry/wheel',lambda msg:self.seen('odom'),10)
        self.create_subscription(VehicleSpeedRpt,'/pacmod/vehicle_speed_rpt',self.speed,10)
        self.create_subscription(ClockMessage,'/clock',self.clock,10)
        self.timer=self.create_timer(.1,self.update,clock=Clock(clock_type=ClockType.STEADY_TIME))

    def map(self,msg):self.map_ready=msg.info.width>0 and msg.info.height>0 and bool(msg.data)
    def seen(self,key):self.times[key]=time.monotonic()
    def speed(self,msg):
        self.report_valid=msg.vehicle_speed_valid
        if msg.vehicle_speed_valid:self.seen('report')
        else:self.times.pop('report',None)
    def clock(self,msg):
        stamp=msg.clock.sec+msg.clock.nanosec*1e-9
        if self.last_clock is not None and stamp<self.last_clock:self.trip('clock_rewind')
        if stamp!=self.last_clock:self.seen('clock')
        self.last_clock=stamp
    def ages(self):
        now=time.monotonic()
        return {key:now-self.times[key] if key in self.times else None for key in ('clock','cloud','odom','report')}
    def trip(self,reason):
        if self.failed:return
        self.last_fault={'reason':reason,'stream_ages_s':self.ages(),'report_valid':self.report_valid}
        self.get_logger().error('Readiness fault: '+json.dumps(self.last_fault))
        self.failed=True;self.active=False
        if self.cancel.service_is_ready():self.cancel.call_async(CancelGoal.Request())
        if self.manager.service_is_ready():
            req=ManageLifecycleNodes.Request();req.command=1;self.manager.call_async(req)
    def update(self):
        now=time.monotonic()
        data=self.map_ready and all(k in self.times and now-self.times[k]<2. for k in ('clock','cloud','odom','report'))
        tf=bool(self.buffer.can_transform('map','base_rear_axle',rclpy.time.Time()))
        if self.starting is not None and self.starting.done():
            result=self.starting.result();self.active=bool(result and result.success);self.failed=not self.active;self.starting=None
        if not self.failed and not self.active and self.starting is None and data and tf and self.manager.service_is_ready():
            req=ManageLifecycleNodes.Request();req.command=0;self.starting=self.manager.call_async(req)
        if self.active and not (data and tf):self.trip('data_stale_or_invalid' if not data else 'tf_unavailable')
        ready=self.active and data and tf and not self.failed
        msg=Bool();msg.data=not ready;self.inhibit.publish(msg)
        status=String();status.data=json.dumps({'ready':ready,'data_ready':data,'tf_ready':tf,'nav2_active':self.active,'fault_latched':self.failed,'stream_ages_s':self.ages(),'report_valid':self.report_valid,'last_fault':self.last_fault});self.status.publish(status)

def main():
    rclpy.init();node=Readiness()
    try:rclpy.spin(node)
    except (KeyboardInterrupt,rclpy.executors.ExternalShutdownException):pass
    finally:
        node.destroy_node()
        if rclpy.ok():rclpy.shutdown()
if __name__=='__main__':main()
