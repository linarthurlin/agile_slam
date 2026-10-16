"""Isolated simulation backend; consumes description and private actuation."""
import json
import os
import yaml
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument,ExecuteProcess,RegisterEventHandler,EmitEvent
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration,PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

def checked(next_action):
    def handler(event,context):
        return [next_action] if event.returncode==0 else [EmitEvent(event=Shutdown(reason='Simulation backend startup failed'))]
    return handler

def generate_launch_description():
    cfg=json.loads((Path(get_package_share_directory('gem_description'))/'config/vehicle.json').read_text())
    joints=yaml.safe_load((Path(get_package_share_directory('gem_gazebo'))/'config/gem_ackermann_control_params_ros2.yaml').read_text())['ackermann_controller']['ros__parameters']
    for wheel in ('left_front_wheel','right_front_wheel','left_rear_wheel','right_rear_wheel'):
        joints[wheel]['diameter']=2*cfg['wheel_radius']
    server=ExecuteProcess(cmd=['ign','gazebo','-r','-s','-v','2',LaunchConfiguration('world')],output='screen')
    spawn=Node(package='ros_gz_sim',executable='create',arguments=['-name','gem','-topic','robot_description','-z','0.3','-x',os.environ.get('AGILE_SPAWN_X','0'),'-y',os.environ.get('AGILE_SPAWN_Y','0'),'-Y',os.environ.get('AGILE_SPAWN_YAW','0')],output='screen')
    spawner=Node(package='controller_manager',executable='spawner',arguments=['joint_state_broadcaster','left_steering_controller','right_steering_controller','left_front_wheel_controller','right_front_wheel_controller','left_rear_wheel_controller','right_rear_wheel_controller','--controller-manager-timeout','180','--switch-timeout','120','--service-call-timeout','180'],parameters=[{'use_sim_time':True}],output='screen')
    adapter=Node(package='gem_gazebo',executable='gem_control.py',name='simulation_actuator_adapter',parameters=[{'use_sim_time':True,'cmd_timeout':.5},joints],remappings=[('ackermann_cmd','/simulation/actuation')],output='screen')
    return LaunchDescription([
        DeclareLaunchArgument('world',default_value='/opt/agile_assets/worlds/small_city.sdf'),
        RegisterEventHandler(OnProcessExit(target_action=spawn,on_exit=checked(spawner))),
        RegisterEventHandler(OnProcessExit(target_action=spawner,on_exit=checked(adapter))),
        RegisterEventHandler(OnProcessExit(target_action=server,on_exit=[EmitEvent(event=Shutdown(reason='Gazebo backend exited'))])),
        RegisterEventHandler(OnProcessExit(target_action=adapter,on_exit=[EmitEvent(event=Shutdown(reason='Simulation actuator exited'))])),
        server,
        Node(package='ros_gz_bridge',executable='parameter_bridge',parameters=[{'config_file':PathJoinSubstitution([FindPackageShare('gem_gazebo'),'config','gz_bridge.yaml'])}],output='screen'),
        Node(package='ros_gz_image',executable='image_bridge',arguments=['/camera/image_raw'],remappings=[('/camera/image_raw','/sensors/cameras/front/image_raw')],output='screen'),
        Node(package='agile_vehicle',executable='pacmod_mock.py',parameters=[{'use_sim_time':True}],output='screen'),
        spawn])
