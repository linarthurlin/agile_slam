#!/usr/bin/env bash
set -e
source /opt/ros/humble/setup.bash
if [[ -f /workspace/ros_ws/install/setup.bash ]]; then
    source /workspace/ros_ws/install/setup.bash
fi
source /opt/agile_slam_ws/install/setup.bash
export IGN_GAZEBO_SYSTEM_PLUGIN_PATH="/opt/ros/humble/lib${IGN_GAZEBO_SYSTEM_PLUGIN_PATH:+:$IGN_GAZEBO_SYSTEM_PLUGIN_PATH}"
exec "$@"
