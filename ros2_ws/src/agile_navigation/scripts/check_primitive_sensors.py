#!/usr/bin/env python3
"""Check original sensors against the stationary baseline wall at world x=7.85."""
import argparse
import json
import time
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Image, PointCloud2
from tf2_ros import Buffer, TransformListener


def rotation(q):
    x,y,z,w=q.x,q.y,q.z,q.w
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                     [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                     [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('sensor',choices=('camera','lidar','both'))
    parser.add_argument('--output-image')
    args=parser.parse_args()
    rclpy.init();node=Node('primitive_sensor_checker')
    buffer=Buffer();listener=TransformListener(buffer,node)
    state={'camera_samples':0,'cloud_samples':0,'truth':None,'wall_error_m':None}
    def truth(msg):state['truth']=msg.pose.pose
    last_image=None
    def camera(msg):
        nonlocal last_image
        if msg.encoding!='rgb8' or msg.width!=800 or msg.height!=600 or len(msg.data)!=msg.step*msg.height:
            state['image_valid']=False;return
        image=np.ndarray((msg.height,msg.width,3),dtype=np.uint8,buffer=msg.data,strides=(msg.step,3,1))
        last_image=image.copy()
        center=image[260:340,360:440].mean(axis=(0,1))
        channels=image.astype(np.int16)
        warm_fraction=float(np.mean((channels[:,:,0]>channels[:,:,1]+3)&(channels[:,:,1]>channels[:,:,2]+8)))
        state.update(camera_samples=state['camera_samples']+1,image_valid=warm_fraction>.01,warm_fraction=warm_fraction,center_rgb=center.tolist(),image_stddev=float(image.std()))
    def cloud(msg):
        fields={f.name:f for f in msg.fields}
        if not all(k in fields for k in ('x','y','z','intensity','ring')):
            state['cloud_valid']=False;return
        dtype=np.dtype({'names':['x','y','z'],'formats':[('>' if msg.is_bigendian else '<')+'f4']*3,'offsets':[fields[n].offset for n in ('x','y','z')],'itemsize':msg.point_step})
        values=np.ndarray((msg.height,msg.width),dtype=dtype,buffer=msg.data,strides=(msg.row_step,msg.point_step))
        points=np.column_stack([values[k].reshape(-1) for k in ('x','y','z')])
        points=points[np.isfinite(points).all(axis=1)]
        state.update(cloud_samples=state['cloud_samples']+1,cloud_valid=msg.height*msg.width==30000,finite_points=len(points))
        if state['truth'] is None:return
        try:tf=buffer.lookup_transform('base_footprint',msg.header.frame_id,rclpy.time.Time()).transform
        except Exception:return
        pose=state['truth']
        body=points@rotation(tf.rotation).T+np.array([tf.translation.x,tf.translation.y,tf.translation.z])
        world=body@rotation(pose.orientation).T+np.array([pose.position.x,pose.position.y,pose.position.z])
        wall=world[(np.abs(world[:,1])<5)&(world[:,2]>.5)&(world[:,2]<3.5)&(world[:,0]>7)&(world[:,0]<9)]
        if len(wall)>25:state.update(wall_points=len(wall),wall_error_m=float(np.median(np.abs(wall[:,0]-7.85))))
    node.create_subscription(Odometry,'/ground_truth/odometry',truth,qos_profile_sensor_data)
    if args.sensor in ('camera','both'):node.create_subscription(Image,'/sensors/cameras/front/image_raw',camera,qos_profile_sensor_data)
    if args.sensor in ('lidar','both'):node.create_subscription(PointCloud2,'/sensors/velodyne/points',cloud,qos_profile_sensor_data)
    deadline=time.monotonic()+75
    passed=False
    while time.monotonic()<deadline:
        rclpy.spin_once(node,timeout_sec=.1)
        camera_ok=args.sensor=='lidar' or (state['camera_samples']>=10 and state.get('image_valid',False) and state.get('image_stddev',0)>1)
        lidar_ok=args.sensor=='camera' or (state['cloud_samples']>=10 and state.get('cloud_valid',False) and state.get('finite_points',0)>1000 and state['wall_error_m'] is not None and state['wall_error_m']<.1)
        if camera_ok and lidar_ok:passed=True;break
    if args.output_image and last_image is not None:
        from PIL import Image as PillowImage
        PillowImage.fromarray(last_image).save(args.output_image)
    print(json.dumps({'passed':passed,'sensor':args.sensor,**{k:v for k,v in state.items() if k!='truth'},'scope':'Stationary primitive camera color and LiDAR wall-range readback; no deskew or photometric hardware calibration.'},indent=2))
    node.destroy_node();rclpy.shutdown()
    return 0 if passed else 1


if __name__=='__main__':raise SystemExit(main())
