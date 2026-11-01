"""Start an all-in-one simulation with the canonical Gazebo/ROS bridge stack."""
import os

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    EmitEvent,
    ExecuteProcess,
    IncludeLaunchDescription,
    RegisterEventHandler,
)
from launch.event_handlers import OnProcessExit, OnProcessStart
from launch.events import Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    server = ExecuteProcess(
        cmd=[
            'ign',
            'gazebo',
            '-r',
            '-s',
            '-v',
            '2',
            LaunchConfiguration('world'),
        ],
        output='screen',
    )
    simulation_ros_stack = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare('avl_bringup'), 'launch', 'sim_bridge.launch.py']
            )
        )
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                'world',
                default_value=os.environ.get(
                    'AGILE_WORLD', '/opt/agile_assets/worlds/small_city.sdf'
                ),
                description='Gazebo world file to load.',
            ),
            RegisterEventHandler(
                OnProcessStart(target_action=server, on_start=[simulation_ros_stack])
            ),
            RegisterEventHandler(
                OnProcessExit(
                    target_action=server,
                    on_exit=[
                        EmitEvent(event=Shutdown(reason='Gazebo backend exited'))
                    ],
                )
            ),
            server,
        ]
    )
