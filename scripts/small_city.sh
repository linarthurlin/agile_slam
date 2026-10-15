#!/usr/bin/env bash
# Run from WSL so Docker can mount the WSLg and driver-library paths.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ ! -f "$root/assets/small_city/worlds/small_city.sdf" ]]; then
    echo 'Prepare assets with scripts/prepare_small_city.py and scripts/convert_small_city.py first.' >&2
    exit 1
fi
args=(-f "$root/compose.yaml" -f "$root/compose.small_city.yaml")
if [[ "${1:-}" == --gpu-experimental ]]; then
    [[ -S /mnt/wslg/.X11-unix/X0 && -e /dev/dxg ]] || { echo 'WSLg/GPU unavailable; use the default software profile.' >&2; exit 1; }
    args+=(-f "$root/compose.wslgpu.yaml")
fi
docker compose "${args[@]}" up -d
