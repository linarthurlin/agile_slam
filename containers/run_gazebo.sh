#!/usr/bin/env bash
set -euo pipefail

world="${AGILE_WORLD:-/opt/agile_assets/worlds/small_city.sdf}"
gui="${AGILE_GAZEBO_GUI:-0}"

if [[ "${gui}" == "1" ]]; then
    exec ign gazebo -r -v 2 "${world}"
fi

exec xvfb-run -a ign gazebo -r -s -v 2 "${world}"
