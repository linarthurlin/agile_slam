"""Shared core; Gazebo and the estimator are separate services."""
import json
import tempfile
import yaml
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    share = FindPackageShare('agile_navigation')
    config = PathJoinSubstitution([share, 'config', 'nav2.yaml'])
    tree = PathJoinSubstitution([share, 'config', 'navigate_pacmod.xml'])
    cfg=json.loads((Path(get_package_share_directory('gem_description'))/'config/vehicle.json').read_text())
    rear=cfg['rear_axle_x']; half=cfg['body_half_width']
    footprint=str([[x-rear,y] for x,y in ((cfg['body_front_x'],half),(cfg['body_front_x'],-half),(cfg['body_rear_x'],-half),(cfg['body_rear_x'],half))])
    settings=yaml.safe_load((Path(get_package_share_directory('agile_navigation'))/'config/nav2.yaml').read_text())
    for name in ('local_costmap','global_costmap'):
        settings[name][name]['ros__parameters']['footprint']=footprint
    settings['planner_server']['ros__parameters']['GridBased']['minimum_turning_radius']=cfg['minimum_turning_radius']
    settings['controller_server']['ros__parameters']['FollowPath']['desired_linear_vel']=cfg['max_speed']
    settings['bt_navigator']['ros__parameters']['goal_reached_tol']=1.0
    settings['bt_navigator']['ros__parameters']['plugin_lib_names'].append('nav2_goal_reached_condition_bt_node')
    generated=tempfile.NamedTemporaryFile(mode='w',suffix='.yaml',delete=False)
    yaml.safe_dump(settings,generated);generated.close();config=generated.name
    lifecycle_nodes = ['planner_server', 'controller_server', 'bt_navigator']
    return LaunchDescription([
        DeclareLaunchArgument('map_yaml', default_value=PathJoinSubstitution([share, 'maps', 'navigation.yaml'])),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(PathJoinSubstitution([FindPackageShare('avl_bringup'),'launch','description.launch.py']))),
        Node(package='agile_navigation',executable='readiness.py',parameters=[{'use_sim_time':True}],output='screen'),
        Node(package='agile_navigation', executable='obstacle_scan.py', parameters=[{'use_sim_time': True}], output='screen'),
        # Known-start-only alignment. Replace this authority with AMCL/SLAM later.
        Node(package='nav2_map_server', executable='map_server', name='map_server', parameters=[config, {'yaml_filename': LaunchConfiguration('map_yaml')}], output='screen'),
        Node(package='nav2_planner', executable='planner_server', name='planner_server', parameters=[config], output='screen'),
        Node(package='nav2_controller', executable='controller_server', name='controller_server', parameters=[config], output='screen'),
        Node(package='nav2_bt_navigator', executable='bt_navigator', name='bt_navigator', parameters=[config, {'default_nav_to_pose_bt_xml': tree, 'default_nav_through_poses_bt_xml': PathJoinSubstitution([share, 'config', 'navigate_through.xml'])}], output='screen'),
        Node(package='nav2_lifecycle_manager',executable='lifecycle_manager',name='lifecycle_manager_map',parameters=[{'use_sim_time':True,'autostart':True,'node_names':['map_server']}],output='screen'),
        Node(package='nav2_lifecycle_manager', executable='lifecycle_manager', name='lifecycle_manager_navigation', parameters=[{'use_sim_time': True, 'autostart': False, 'node_names': lifecycle_nodes}], output='screen'),
    ])
