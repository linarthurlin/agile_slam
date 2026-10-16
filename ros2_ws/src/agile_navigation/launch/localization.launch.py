"""Simulation-only wheel feedback estimator and known-start alignment."""
import json
import math
import os
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    cfg=json.loads((Path(get_package_share_directory('gem_description'))/'config/vehicle.json').read_text())
    geometry={k:cfg[k] for k in ('wheelbase','track','wheel_radius','rear_axle_x')}
    x=float(os.environ.get('AGILE_SPAWN_X','0'));y=float(os.environ.get('AGILE_SPAWN_Y','0'));yaw=float(os.environ.get('AGILE_SPAWN_YAW','0'))
    geometry.update(initial_x=x+cfg['rear_axle_x']*math.cos(yaw),initial_y=y+cfg['rear_axle_x']*math.sin(yaw),initial_yaw=yaw)
    return LaunchDescription([
        Node(package='agile_navigation',executable='wheel_odometry.py',parameters=[{'use_sim_time':True},geometry],output='screen'),
        Node(package='tf2_ros',executable='static_transform_publisher',arguments=['--x','0','--y','0','--z','0','--roll','0','--pitch','0','--yaw','0','--frame-id','map','--child-frame-id','odom'],parameters=[{'use_sim_time':True}],output='screen')])
