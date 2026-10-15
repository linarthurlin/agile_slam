#!/usr/bin/env bash
# Open WSLg clients against the already-running simulation namespace.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
view="${1:-baseline}"
if [[ "$view" != baseline && "$view" != navigation ]]; then
    echo "Usage: bash scripts/gui.sh [baseline|navigation]" >&2
    exit 1
fi
sim="$(docker compose --project-directory "$root" ps -q sim)"
if [[ -z "$sim" ]] || [[ "$(docker inspect -f '{{.State.Running}}' "$sim")" != true ]]; then
    echo 'Start the simulator with docker compose up -d first.' >&2
    exit 1
fi
if [[ ! -S /mnt/wslg/.X11-unix/X0 ]]; then
    echo 'WSLg X11 socket not found. Run this script inside the WSLg-enabled distro.' >&2
    exit 1
fi
image="$(docker inspect -f '{{.Image}}' "$sim")"
partition="$(docker exec "$sim" printenv IGN_PARTITION || true)"
if [[ -z "$partition" ]]; then
    partition="$(docker exec "$sim" hostname):$(docker exec "$sim" id -un)"
fi
domain="$(docker exec "$sim" printenv ROS_DOMAIN_ID)"
start_client() {
    local name="$1"
    shift
    if docker inspect "$name" >/dev/null 2>&1; then
        if [[ "$(docker inspect -f '{{.State.Running}}' "$name")" == true ]]; then
            echo "$name is already running."
            return
        fi
        docker rm "$name" >/dev/null
    fi
    docker run -d --init --name "$name" \
        --network "container:$sim" \
        -e DISPLAY=:0 -e QT_QPA_PLATFORM=xcb -e QT_X11_NO_MITSHM=1 \
        -e LIBGL_ALWAYS_SOFTWARE=1 -e ROS_DOMAIN_ID="$domain" \
        -e IGN_PARTITION="$partition" \
        -v /mnt/wslg/.X11-unix:/tmp/.X11-unix:ro \
        -v "$root/config/rviz:/gui:ro" \
        "$image" "$@"
}
start_client agile-slam-gazebo ign gazebo -g -v 2
start_client agile-slam-rviz rviz2 -d "/gui/$view.rviz" --ros-args -p use_sim_time:=true
printf 'Opened Gazebo and RViz through WSLg.\n'
printf 'Close clients with: docker stop agile-slam-gazebo agile-slam-rviz\n'
