"""Launch the isolated legacy simulator baseline without a real vehicle driver."""
from launch import LaunchDescription
from launch.actions import EmitEvent, ExecuteProcess, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import Command, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def after_success(next_action):
    def handler(event, context):
        if event.returncode != 0:
            return [EmitEvent(event=Shutdown(reason='Baseline startup stage failed'))]
        return [next_action]
    return handler


def generate_launch_description():
    description = ParameterValue(Command(['xacro ', PathJoinSubstitution([FindPackageShare('gem_description'), 'urdf', 'gem.urdf.xacro'])]), value_type=str)
    world = PathJoinSubstitution([FindPackageShare('gem_gazebo'), 'worlds', 'baseline.sdf'])
    gazebo = ExecuteProcess(cmd=['ign', 'gazebo', '-r', '-s', '-v', '2', world], output='screen')
    spawn = Node(package='ros_gz_sim', executable='create', arguments=['-name', 'gem', '-topic', 'robot_description', '-z', '0.3'], output='screen')
    controllers = Node(package='controller_manager', executable='spawner', arguments=['joint_state_broadcaster', 'left_steering_controller', 'right_steering_controller', 'left_front_wheel_controller', 'right_front_wheel_controller', 'left_rear_wheel_controller', 'right_rear_wheel_controller', '--controller-manager-timeout', '60'], output='screen', parameters=[{'use_sim_time': True}])
    controller = Node(package='gem_gazebo', executable='gem_control.py', name='ackermann_controller', parameters=[{'use_sim_time': True, 'cmd_timeout': 0.5}, PathJoinSubstitution([FindPackageShare('gem_gazebo'), 'config', 'gem_ackermann_control_params_ros2.yaml'])], output='screen')
    return LaunchDescription([
        RegisterEventHandler(OnProcessExit(target_action=spawn, on_exit=after_success(controllers))),
        RegisterEventHandler(OnProcessExit(target_action=controllers, on_exit=after_success(controller))),
        RegisterEventHandler(OnProcessExit(target_action=controller, on_exit=[EmitEvent(event=Shutdown(reason='Vehicle controller exited'))])),
        RegisterEventHandler(OnProcessExit(target_action=gazebo, on_exit=[EmitEvent(event=Shutdown(reason='Gazebo exited'))])),
        Node(package='robot_state_publisher', executable='robot_state_publisher', parameters=[{'robot_description': description, 'use_sim_time': True}], output='screen'),
        gazebo,
        Node(package='ros_gz_bridge', executable='parameter_bridge', parameters=[{'config_file': PathJoinSubstitution([FindPackageShare('gem_gazebo'), 'config', 'gz_bridge.yaml']), 'use_sim_time': True}], output='screen'),
        Node(package='ros_gz_image', executable='image_bridge', arguments=['/camera/image_raw'], remappings=[('/camera/image_raw', '/sensors/cameras/front/image_raw')], parameters=[{'use_sim_time': True}], output='screen'),
        spawn,
    ])
