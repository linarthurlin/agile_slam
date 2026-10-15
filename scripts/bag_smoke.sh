#!/usr/bin/env bash
# Execute inside the simulator container through its ROS entrypoint.
set -euo pipefail
mode="${1:?Usage: bag_smoke.sh record|replay [bag-directory]}"
bag="${2:-/artifacts/bags/small_city_smoke}"
case "$mode" in
  record)
    mkdir -p "$(dirname "$bag")"
    [[ ! -e "$bag" ]] || { echo 'Choose a new bag directory; existing data is preserved.' >&2; exit 1; }
    status=0
    timeout --signal=INT 20 ros2 bag record -o "$bag" /clock /tf /tf_static \
      /joint_states /odometry/wheel /ground_truth/odometry /ackermann_cmd /cmd_vel \
      /sensors/velodyne/points /sensors/imu/data_raw \
      /sensors/cameras/front/image_raw /sensors/cameras/front/camera_info \
      /sensors/obstacle_scan || status=$?
    [[ "$status" == 0 || "$status" == 124 ]] || exit "$status"
    ros2 bag info "$bag"
    ;;
  replay)
    export ROS_DOMAIN_ID=43
    python3 /opt/agile_slam_ws/src/agile_navigation/scripts/check_sensors.py \
      > /artifacts/small_city_replay_sensors.json &
    checker=$!
    trap 'kill "$checker" 2>/dev/null || true' EXIT
    ros2 bag play "$bag" --delay 2
    wait "$checker"
    trap - EXIT
    ;;
  *) echo 'Expected record or replay.' >&2; exit 1 ;;
esac
