"""Publish the shared vehicle description independently of any backend."""
import json
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.substitutions import Command,PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    cfg=json.loads((Path(get_package_share_directory('gem_description'))/'config/simulation.json').read_text())
    auxiliary=str(cfg['auxiliary_cameras']).lower()
    model=ParameterValue(Command(['xacro ',PathJoinSubstitution([FindPackageShare('gem_description'),'urdf','gem.urdf.xacro']),' auxiliary_cameras:=',auxiliary]),value_type=str)
    return LaunchDescription([Node(package='robot_state_publisher',executable='robot_state_publisher',parameters=[{'robot_description':model,'use_sim_time':True}],output='screen')])
