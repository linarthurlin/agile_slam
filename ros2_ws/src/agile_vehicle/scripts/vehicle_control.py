#!/usr/bin/env python3
"""Humble Twist -> normalized setpoint -> feedback-controlled PACMod commands."""
import json
import math
import time
from rclpy.node import Node
from rclpy.clock import Clock,ClockType
from rclpy.qos import QoSProfile,DurabilityPolicy
from geometry_msgs.msg import Twist
from ackermann_msgs.msg import AckermannDriveStamped
from std_msgs.msg import Bool,String
from pacmod2_msgs.msg import SystemCmdFloat,SystemCmdInt,PositionWithSpeed,VehicleSpeedRpt,GlobalRpt
from control_logic import SpeedController
from runtime_support import config,run


class VehicleControl(Node):
    def __init__(self):
        super().__init__('vehicle_control')
        self.cfg=config();self.logic=SpeedController(self.cfg)
        self.speed=0.;self.speed_valid=False;self.speed_time=0.;self.global_time=0.
        self.enabled=False;self.inhibited=True
        self.accel=self.create_publisher(SystemCmdFloat,'/pacmod/accel_cmd',10)
        self.brake=self.create_publisher(SystemCmdFloat,'/pacmod/brake_cmd',10)
        self.steer=self.create_publisher(PositionWithSpeed,'/pacmod/steering_cmd',10)
        self.shift=self.create_publisher(SystemCmdInt,'/pacmod/shift_cmd',10)
        self.setpoint=self.create_publisher(AckermannDriveStamped,'/vehicle/setpoint',10)
        self.status=self.create_publisher(String,'/vehicle/control_status',10)
        self.create_subscription(Twist,'/cmd_vel',self.command,10)
        self.create_subscription(VehicleSpeedRpt,'/pacmod/vehicle_speed_rpt',self.report,10)
        self.create_subscription(GlobalRpt,'/pacmod/global_rpt',self.global_report,10)
        self.create_subscription(Bool,'/vehicle/inhibit',self.inhibit,QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.timer=self.create_timer(.02,self.update,clock=Clock(clock_type=ClockType.STEADY_TIME))

    def command(self,msg):
        accepted=self.logic.command(msg.linear.x,msg.angular.z,time.monotonic())
        out=AckermannDriveStamped();out.header.stamp=self.get_clock().now().to_msg();out.header.frame_id='base_rear_axle'
        if accepted:out.drive.speed=self.logic.target;out.drive.steering_angle=self.logic.angle
        self.setpoint.publish(out)

    def report(self,msg):
        self.speed_time=time.monotonic();self.speed=msg.vehicle_speed
        self.speed_valid=msg.vehicle_speed_valid and math.isfinite(self.speed)

    def global_report(self,msg):
        self.global_time=time.monotonic()
        self.enabled=msg.enabled and not any((msg.override_active,msg.veh_can_timeout,msg.str_can_timeout,msg.brk_can_timeout,msg.usr_can_timeout,msg.user_can_read_errors))

    def inhibit(self,msg):self.inhibited=msg.data

    def update(self):
        now=time.monotonic()
        age=max(now-self.speed_time,now-self.global_time) if self.speed_valid else float('inf')
        accel,brake,angle,state=self.logic.step(now,self.speed,age,self.enabled,self.inhibited)
        stamp=self.get_clock().now().to_msg()
        a=SystemCmdFloat();a.header.stamp=stamp;a.command=accel;self.accel.publish(a)
        b=SystemCmdFloat();b.header.stamp=stamp;b.command=brake;self.brake.publish(b)
        s=PositionWithSpeed();s.header.stamp=stamp;s.angular_position=angle*self.cfg['steering_ratio'];s.angular_velocity_limit=self.cfg['steering_rate'];self.steer.publish(s)
        g=SystemCmdInt();g.header.stamp=stamp;g.command=SystemCmdInt.SHIFT_FORWARD;self.shift.publish(g)
        status=String();status.data=json.dumps({'state':state,'enabled':self.enabled,'inhibited':self.inhibited,'report_age_s':age if math.isfinite(age) else None,'target_mps':self.logic.target,'feedback_mps':self.speed,'accel':accel,'brake':brake});self.status.publish(status)

if __name__=='__main__':run(VehicleControl)
