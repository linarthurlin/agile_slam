"""Known-start navigation experiment using wheel feedback, without SLAM/truth TF."""
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    share = FindPackageShare('agile_navigation')
    config = PathJoinSubstitution([share, 'config', 'nav2.yaml'])
    tree = PathJoinSubstitution([share, 'config', 'navigate.xml'])
    lifecycle_nodes = ['map_server', 'planner_server', 'controller_server', 'bt_navigator']
    return LaunchDescription([
        IncludeLaunchDescription(PythonLaunchDescriptionSource(PathJoinSubstitution([FindPackageShare('avl_bringup'), 'launch', 'baseline.launch.py'])), launch_arguments={'world_name': 'navigation.sdf'}.items()),
        Node(package='agile_navigation', executable='obstacle_scan.py', parameters=[{'use_sim_time': True}], output='screen'),
        Node(package='agile_navigation', executable='wheel_odometry.py', parameters=[{'use_sim_time': True}], output='screen'),
        Node(package='agile_navigation', executable='twist_to_ackermann.py', parameters=[{'use_sim_time': True}], output='screen'),
        # Known-start-only alignment. Replace this authority with AMCL/SLAM later.
        Node(package='tf2_ros', executable='static_transform_publisher', arguments=['--x', '0', '--y', '0', '--z', '0', '--roll', '0', '--pitch', '0', '--yaw', '0', '--frame-id', 'map', '--child-frame-id', 'odom'], parameters=[{'use_sim_time': True}]),
        Node(package='nav2_map_server', executable='map_server', name='map_server', parameters=[config, {'yaml_filename': PathJoinSubstitution([share, 'maps', 'navigation.yaml'])}], output='screen'),
        Node(package='nav2_planner', executable='planner_server', name='planner_server', parameters=[config], output='screen'),
        Node(package='nav2_controller', executable='controller_server', name='controller_server', parameters=[config], output='screen'),
        Node(package='nav2_bt_navigator', executable='bt_navigator', name='bt_navigator', parameters=[config, {'default_nav_to_pose_bt_xml': tree, 'default_nav_through_poses_bt_xml': PathJoinSubstitution([share, 'config', 'navigate_through.xml'])}], output='screen'),
        Node(package='nav2_lifecycle_manager', executable='lifecycle_manager', name='lifecycle_manager_navigation', parameters=[{'use_sim_time': True, 'autostart': True, 'node_names': lifecycle_nodes}], output='screen'),
    ])
