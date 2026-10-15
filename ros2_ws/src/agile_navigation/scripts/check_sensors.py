#!/usr/bin/env python3
"""Report a short sensor sanity/rate window; no truth pose is consumed."""
import json
import math
import time
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import PointCloud2, Imu, Image, CameraInfo, LaserScan
from rosgraph_msgs.msg import Clock


def main():
    rclpy.init()
    node = Node('sensor_sanity_checker')
    duration=node.declare_parameter('duration',15.0).value
    records={}
    clocks=[]
    node.create_subscription(Clock,'/clock',lambda msg: clocks.append((time.monotonic(),msg.clock.sec+msg.clock.nanosec*1e-9)),qos_profile_sensor_data)
    topics={'/sensors/velodyne/points':PointCloud2,'/sensors/imu/data_raw':Imu,'/sensors/cameras/front/image_raw':Image,'/sensors/cameras/front/camera_info':CameraInfo,'/sensors/obstacle_scan':LaserScan}
    subscriptions=[]
    for topic,kind in topics.items():
        def receive(msg,topic=topic):
            record=records.setdefault(topic,{'count':0,'wall':[],'stamps':[]})
            record['count']+=1
            record['wall'].append(time.monotonic())
            record['stamps'].append(msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9)
            record['frame_id']=msg.header.frame_id
            if isinstance(msg,Imu):
                record['acceleration_norm']=math.sqrt(msg.linear_acceleration.x**2+msg.linear_acceleration.y**2+msg.linear_acceleration.z**2)
            elif isinstance(msg,Image):
                record['shape']=[msg.width,msg.height]
                record['encoding']=msg.encoding
                record['payload_valid']=len(msg.data)==msg.step*msg.height
            elif isinstance(msg,CameraInfo):
                record['shape']=[msg.width,msg.height]
                record['focal_lengths']=[msg.k[0],msg.k[4]]
            elif isinstance(msg,PointCloud2):
                fields={f.name:f for f in msg.fields}
                record['fields']=list(fields)
                record['points']=msg.width*msg.height
                dtype=np.dtype({'names':['x','y','z'],'formats':[('>' if msg.is_bigendian else '<')+'f4']*3,'offsets':[fields[n].offset for n in ('x','y','z')],'itemsize':msg.point_step})
                array=np.ndarray((msg.height,msg.width),dtype=dtype,buffer=msg.data,strides=(msg.row_step,msg.point_step))
                record['finite_points']=int(np.count_nonzero(np.isfinite(array['x'])&np.isfinite(array['y'])&np.isfinite(array['z'])))
            elif isinstance(msg,LaserScan):
                valid=[r for r in msg.ranges if math.isfinite(r)]
                record['finite_ranges']=len(valid)
                record['nearest_obstacle_m']=min(valid,default=None)
        subscriptions.append(node.create_subscription(kind,topic,receive,10))
    deadline=time.monotonic()+duration
    while time.monotonic()<deadline:
        rclpy.spin_once(node,timeout_sec=.05)
    for record in records.values():
        wall,stamps=record.pop('wall'),record.pop('stamps')
        record['received_rate_wall_hz']=(len(wall)-1)/(wall[-1]-wall[0]) if len(wall)>1 else None
        record['received_rate_stamp_hz']=(len(stamps)-1)/(stamps[-1]-stamps[0]) if len(stamps)>1 and stamps[-1]>stamps[0] else None
        record['backward_stamps']=sum(b<a for a,b in zip(stamps,stamps[1:]))
    rtf=(clocks[-1][1]-clocks[0][1])/(clocks[-1][0]-clocks[0][0]) if len(clocks)>1 else None
    passed=all(records.get(topic,{}).get('count',0)>=3 and records[topic]['backward_stamps']==0 for topic in topics)
    passed=passed and records.get('/sensors/cameras/front/image_raw',{}).get('payload_valid',False)
    passed=passed and records.get('/sensors/velodyne/points',{}).get('finite_points',0)>1000 and records.get('/sensors/obstacle_scan',{}).get('finite_ranges',0)>10
    image=records.get('/sensors/cameras/front/image_raw',{})
    info=records.get('/sensors/cameras/front/camera_info',{})
    imu=records.get('/sensors/imu/data_raw',{})
    passed=passed and image.get('shape')==info.get('shape')==[800,600]
    passed=passed and image.get('frame_id')==info.get('frame_id')=='camera_front_optical_frame'
    passed=passed and imu.get('frame_id')=='IMU_link' and 9.5<imu.get('acceleration_norm',0)<10.1
    warnings=[]
    if image.get('received_rate_stamp_hz',0)<24:
        warnings.append('RGB delivery is below 80% of nominal rate in acquisition time.')
    print(json.dumps({'passed':passed,'wall_window_s':duration,'estimated_rtf':rtf,'warnings':warnings,'topics':records,'scope':'Short delivery/schema sanity window; not a hardware accuracy, latency, or long-duration acceptance.'},indent=2))
    node.destroy_node()
    rclpy.shutdown()
    return 0 if passed else 1


if __name__=='__main__':
    raise SystemExit(main())
