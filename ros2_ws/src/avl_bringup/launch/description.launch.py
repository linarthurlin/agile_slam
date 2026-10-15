"""Publish the shared vehicle description independently of any backend."""
from launch import LaunchDescription
from launch.substitutions import Command,PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    model=ParameterValue(Command(['xacro ',PathJoinSubstitution([FindPackageShare('gem_description'),'urdf','gem.urdf.xacro'])]),value_type=str)
    return LaunchDescription([Node(package='robot_state_publisher',executable='robot_state_publisher',parameters=[{'robot_description':model,'use_sim_time':True}],output='screen')])
