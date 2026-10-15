#!/usr/bin/env python3
"""Project a reliable 3-D snapshot cloud into a small virtual obstacle scan."""
import math
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from rclpy.time import Time
from sensor_msgs.msg import PointCloud2, LaserScan
from tf2_ros import Buffer, TransformListener


class ObstacleScan(Node):
    def __init__(self):
        super().__init__('obstacle_scan')
        self.buffer = Buffer()
        self.listener = TransformListener(self.buffer, self)
        self.publisher = self.create_publisher(LaserScan, '/sensors/obstacle_scan', 10)
        self.create_subscription(PointCloud2, '/sensors/velodyne/points', self.update, 10)

    def update(self, cloud):
        try:
            tf = self.buffer.lookup_transform('base_footprint', cloud.header.frame_id, Time.from_msg(cloud.header.stamp))
        except Exception:
            return
        fields = {field.name: field for field in cloud.fields}
        if not all(name in fields and fields[name].datatype == 7 for name in ('x', 'y', 'z')):
            return
        endian = '>' if cloud.is_bigendian else '<'
        dtype = np.dtype({'names': ['x','y','z'], 'formats': [endian+'f4']*3, 'offsets': [fields[n].offset for n in ('x','y','z')], 'itemsize': cloud.point_step})
        records = np.ndarray((cloud.height, cloud.width), dtype=dtype, buffer=cloud.data, strides=(cloud.row_step, cloud.point_step))
        points = np.stack([records[n].reshape(-1) for n in ('x','y','z')], axis=1)
        q = tf.transform.rotation
        x,y,z,w = q.x,q.y,q.z,q.w
        rotation = np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)], [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)], [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
        t = tf.transform.translation
        points = points @ rotation.T + [t.x,t.y,t.z]
        valid = np.isfinite(points).all(axis=1) & (points[:,2] >= .25) & (points[:,2] <= 2.5)
        points = points[valid]
        distance = np.hypot(points[:,0],points[:,1])
        valid = (distance >= 1.0) & (distance <= 15.0)
        points,distance = points[valid],distance[valid]
        bins = 720
        angles = np.arctan2(points[:,1],points[:,0])
        indices = np.floor((angles+math.pi)/(2*math.pi/bins)).astype(int) % bins
        ranges = np.full(bins, np.inf, dtype=float)
        np.minimum.at(ranges, indices, distance)
        scan = LaserScan()
        scan.header.stamp = cloud.header.stamp
        scan.header.frame_id = 'base_footprint'
        scan.angle_min,scan.angle_increment = -math.pi,2*math.pi/bins
        scan.angle_max = scan.angle_min + (bins-1)*scan.angle_increment
        scan.range_min,scan.range_max,scan.scan_time = 1.0,15.0,.1
        scan.ranges = ranges.tolist()
        self.publisher.publish(scan)


def main():
    rclpy.init()
    node = ObstacleScan()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
