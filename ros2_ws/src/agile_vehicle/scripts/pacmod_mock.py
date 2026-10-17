#!/usr/bin/env python3
"""Simulation-only PACMod2 ROS contract; no CAN transport or hardware claim."""
import json
import math
import time
from rclpy.node import Node
from rclpy.clock import Clock,ClockType
from rclpy.qos import qos_profile_sensor_data
from std_srvs.srv import SetBool
from std_msgs.msg import String
from sensor_msgs.msg import JointState
from ackermann_msgs.msg import AckermannDrive
from pacmod2_msgs.msg import SystemCmdFloat,SystemCmdInt,PositionWithSpeed,VehicleSpeedRpt,GlobalRpt,SystemRptFloat,SystemRptInt
from control_logic import MockState,CommandBundle
from runtime_support import config,run


class PacmodMock(Node):
    def __init__(self):
        super().__init__('pacmod_mock')
        self.cfg=config();self.state=MockState();self.bundle=CommandBundle(max_age=self.cfg['command_timeout']);self.report_valid=True;self.commands={'accel':0.,'brake':.4,'shaft':0.,'rate':self.cfg['steering_rate']};self.receipts={}
        self.feedback=0.;self.feedback_angle=0.;self.joint_time=0.;self.clock_time=0.;self.last_stamp=None;self.last_step=None
        self.last_watchdog_fault=None
        self.actuation=self.create_publisher(AckermannDrive,'/simulation/actuation',10)
        self.speed=self.create_publisher(VehicleSpeedRpt,'/pacmod/vehicle_speed_rpt',10)
        self.global_pub=self.create_publisher(GlobalRpt,'/pacmod/global_rpt',10)
        self.steer_report=self.create_publisher(SystemRptFloat,'/pacmod/steering_rpt',10)
        self.shift_report=self.create_publisher(SystemRptInt,'/pacmod/shift_rpt',10)
        self.status=self.create_publisher(String,'/pacmod/mock/status',10)
        self.create_subscription(JointState,'/joint_states',self.joints,qos_profile_sensor_data)
        for key,topic in (('accel','accel_cmd'),('brake','brake_cmd')):
            self.create_subscription(SystemCmdFloat,'/pacmod/'+topic,lambda msg,key=key:self.receive(key,msg.header.stamp,msg.command),10)
        self.create_subscription(PositionWithSpeed,'/pacmod/steering_cmd',self.steering,10)
        self.create_subscription(SystemCmdInt,'/pacmod/shift_cmd',self.gear,10)
        self.create_service(SetBool,'/pacmod/mock/enable',self.enable)
        self.create_service(SetBool,'/pacmod/mock/fault',self.fault)
        self.create_service(SetBool,'/pacmod/mock/override',self.override)
        self.create_service(SetBool,'/pacmod/mock/report_valid',self.validity)
        self.timer=self.create_timer(.02,self.update,clock=Clock(clock_type=ClockType.STEADY_TIME))

    def receive(self,key,stamp,value):
        stamp=stamp.sec*1000000000+stamp.nanosec
        frame=self.bundle.push(key,stamp,value)
        if frame is not None:
            self.commands.update(accel=frame['accel'],brake=frame['brake'],shaft=frame['steer'][0],rate=frame['steer'][1])
            receipt=time.monotonic()
            for name in ('accel','brake','shaft'):self.receipts[name]=receipt

    def steering(self,msg):
        self.receive('steer',msg.header.stamp,(msg.angular_position,msg.angular_velocity_limit))

    def gear(self,msg):
        self.receipts['gear']=time.monotonic();self.state.shift(msg.command,self.feedback)

    def joints(self,msg):
        needed=('rear_left_wheel_joint','rear_right_wheel_joint','left_steering_hinge_joint','right_steering_hinge_joint')
        if not all(n in msg.name for n in needed) or len(msg.velocity)!=len(msg.name) or len(msg.position)!=len(msg.name):return
        i=[msg.name.index(n) for n in needed]
        speed=self.cfg['wheel_radius']*(msg.velocity[i[0]]+msg.velocity[i[1]])/2
        left,right=math.tan(msg.position[i[2]]),math.tan(msg.position[i[3]])
        length,track=self.cfg['wheelbase'],self.cfg['track']
        curvature=.5*(left/(length+track*left/2)+right/(length-track*right/2))
        angle=math.atan(length*curvature)
        if not all(math.isfinite(v) for v in (speed,angle)):self.state.trip('fault');return
        self.feedback=speed;self.feedback_angle=angle;self.joint_time=time.monotonic()
        stamp=msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9
        if self.last_stamp is not None and stamp<self.last_stamp:
            self.state.enabled=False;self.state.velocity=0.;self.last_step=None;self.bundle.reset();self.receipts.clear()
        if stamp!=self.last_stamp:self.clock_time=time.monotonic()
        self.last_stamp=stamp

    def ready(self,now):
        return self.report_valid and now-self.joint_time<=self.cfg['backend_timeout'] and now-self.clock_time<=self.cfg['backend_timeout'] and all(k in self.receipts and now-self.receipts[k]<=self.cfg['command_timeout'] for k in ('accel','brake','shaft','gear'))

    def enable(self,req,res):
        res.success=self.state.enable(req.data,self.ready(time.monotonic()));res.message='Enabled' if self.state.enabled else 'Disabled or not ready';return res

    def fault(self,req,res):
        self.state.fault=req.data
        if req.data:self.state.trip('fault')
        res.success=True;res.message='Fault updated; enable remains explicit';return res

    def override(self,req,res):
        self.state.override=req.data
        if req.data:self.state.trip('override')
        res.success=True;res.message='Override updated; enable remains explicit';return res

    def validity(self,req,res):
        self.report_valid=req.data
        if not req.data:self.state.trip('timeout')
        res.success=True;res.message='Report validity updated; enable remains explicit';return res

    def update(self):
        now=time.monotonic();sim=self.get_clock().now().nanoseconds/1e9
        dt=sim-self.last_step if self.last_step is not None else 0.;self.last_step=sim
        if dt<0:self.state.enabled=False;self.state.velocity=0.
        ready=self.ready(now)
        if self.state.enabled and not ready:
            self.last_watchdog_fault={'joint_age_s':now-self.joint_time,'advancing_joint_stamp_age_s':now-self.clock_time,'command_ages_s':{key:now-self.receipts[key] if key in self.receipts else None for key in ('accel','brake','shaft','gear')},'report_valid':self.report_valid}
            self.get_logger().error('Mock watchdog: '+json.dumps(self.last_watchdog_fault))
        speed,angle=self.state.advance(dt,self.commands['accel'],self.commands['brake'],self.commands['shaft'],self.commands['rate'],ready,self.cfg)
        cmd=AckermannDrive();cmd.speed=speed;cmd.steering_angle=angle;self.actuation.publish(cmd)
        stamp=self.get_clock().now().to_msg()
        rpt=VehicleSpeedRpt();rpt.header.stamp=stamp;rpt.vehicle_speed=self.feedback;rpt.vehicle_speed_valid=self.report_valid and now-self.joint_time<=self.cfg['backend_timeout'] and now-self.clock_time<=self.cfg['backend_timeout'];self.speed.publish(rpt)
        glob=GlobalRpt();glob.header.stamp=stamp;glob.enabled=self.state.enabled;glob.override_active=self.state.override;glob.veh_can_timeout=self.state.fault;glob.usr_can_timeout=self.state.timeout;self.global_pub.publish(glob)
        steering=SystemRptFloat();steering.header.stamp=stamp;steering.command=self.commands['shaft'];steering.output=self.feedback_angle*self.cfg['steering_ratio'];self.steer_report.publish(steering)
        gear=SystemRptInt();gear.header.stamp=stamp;gear.command=self.state.gear;gear.output=self.state.gear;self.shift_report.publish(gear)
        status=String();status.data=json.dumps({'enabled':self.state.enabled,'ready':ready,'fault':self.state.fault,'override':self.state.override,'timeout':self.state.timeout,'gear':self.state.gear,'feedback_mps':self.feedback,'plant_target_mps':speed,'last_watchdog_fault':self.last_watchdog_fault,'scope':'Provisional ROS mock, no CAN/firmware validation'});self.status.publish(status)

if __name__=='__main__':run(PacmodMock)
