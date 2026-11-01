"""Bridge simulated sensor data and PACMod2 ROS contracts to Gazebo."""
import json
import math
import os
from pathlib import Path

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import EmitEvent, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def start_after_success(next_action):
    def on_exit(event, context):
        if event.returncode == 0:
            return [next_action]
        return [EmitEvent(event=Shutdown(reason='Simulation bridge startup stage failed'))]

    return on_exit


def generate_launch_description():
    description_path = Path(get_package_share_directory('gem_description'))
    vehicle = json.loads((description_path / 'config/vehicle.json').read_text())
    controller_config = yaml.safe_load(
        (Path(get_package_share_directory('gem_gazebo')) / 'config/gem_ackermann_control_params_ros2.yaml').read_text()
    )['ackermann_controller']['ros__parameters']

    for wheel_name in ('left_front_wheel', 'right_front_wheel', 'left_rear_wheel', 'right_rear_wheel'):
        controller_config[wheel_name]['diameter'] = 2.0 * vehicle['wheel_radius']

    # AGILE_SPAWN_* remains the inherited chassis-origin fixture; the model root is now rear-axle base_link.
    spawn_yaw = float(os.environ.get('AGILE_SPAWN_YAW', '0'))
    spawn_x = float(os.environ.get('AGILE_SPAWN_X', '0')) + vehicle['rear_axle_x'] * math.cos(spawn_yaw)
    spawn_y = float(os.environ.get('AGILE_SPAWN_Y', '0')) + vehicle['rear_axle_x'] * math.sin(spawn_yaw)
    spawn = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-name', 'gem',
            '-topic', 'robot_description',
            '-z', '0.3',
            '-x', str(spawn_x),
            '-y', str(spawn_y),
            '-Y', str(spawn_yaw),
        ],
        output='screen',
    )
    controllers = Node(
        package='avl_bringup',
        executable='spawn_sim_controllers.py',
        arguments=[
            '--controller-manager-timeout', '180',
            '--service-call-timeout', '180',
            '--switch-timeout', '120',
        ],
        parameters=[{'use_sim_time': True}],
        output='screen',
    )
    actuator = Node(
        package='gem_gazebo',
        executable='gem_control.py',
        name='simulation_actuator_adapter',
        parameters=[{'use_sim_time': True, 'cmd_timeout': 0.5}, controller_config],
        remappings=[('ackermann_cmd', '/simulation/actuation')],
        output='screen',
    )

    return LaunchDescription([
        RegisterEventHandler(OnProcessExit(target_action=spawn, on_exit=start_after_success(controllers))),
        RegisterEventHandler(OnProcessExit(target_action=controllers, on_exit=start_after_success(actuator))),
        RegisterEventHandler(
            OnProcessExit(
                target_action=actuator,
                on_exit=[EmitEvent(event=Shutdown(reason='Simulation actuator adapter exited'))],
            )
        ),
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            parameters=[{
                'config_file': PathJoinSubstitution([
                    FindPackageShare('gem_gazebo'), 'config', 'gz_bridge.yaml'
                ]),
                'use_sim_time': True,
            }],
            output='screen',
        ),
        Node(
            package='ros_gz_image',
            executable='image_bridge',
            arguments=['/camera/image_raw'],
            remappings=[('/camera/image_raw', '/sensors/cameras/front/image_raw')],
            parameters=[{'use_sim_time': True}],
            output='screen',
        ),
        Node(
            package='agile_vehicle',
            executable='pacmod_mock.py',
            parameters=[{'use_sim_time': True}],
            output='screen',
        ),
        spawn,
    ])
