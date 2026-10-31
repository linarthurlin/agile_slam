#!/usr/bin/env bash
set -euo pipefail

world="${AGILE_WORLD:-/opt/agile_assets/worlds/small_city.sdf}"
gui="${AGILE_GAZEBO_GUI:-0}"
gpu="${AGILE_WSL_GPU:-0}"

if [[ "${gui}" == "1" && "${gpu}" == "1" ]]; then
    world_name="$(basename "${world}" .sdf)"
    server_log="/tmp/agile-gazebo-server.log"
    xvfb-run -a ign gazebo -r -s -v 2 "${world}" >"${server_log}" 2>&1 &
    server_pid=$!

    stop_server() {
        kill -TERM "${server_pid}" 2>/dev/null || true
        wait "${server_pid}" 2>/dev/null || true
    }
    trap stop_server EXIT INT TERM

    server_ready=0
    for ((attempt = 0; attempt < 180; attempt++)); do
        if ! kill -0 "${server_pid}" 2>/dev/null; then
            break
        fi
        if ign service -l 2>/dev/null | grep -Fq "/world/${world_name}/create"; then
            server_ready=1
            break
        fi
        sleep 1
    done
    if [[ "${server_ready}" != "1" ]]; then
        cat "${server_log}" >&2
        echo "Gazebo server did not become ready for GUI attachment." >&2
        exit 1
    fi

    set +e
    env -u GALLIUM_DRIVER -u MESA_D3D12_DEFAULT_ADAPTER_NAME -u LD_LIBRARY_PATH \
        DISPLAY="${AGILE_GUI_DISPLAY:-:0}" LIBGL_ALWAYS_SOFTWARE=1 \
        QT_QPA_PLATFORM=xcb QT_X11_NO_MITSHM=1 \
        ign gazebo -g -v 2 "${world}"
    gui_status=$?
    set -e
    stop_server
    trap - EXIT INT TERM
    exit "${gui_status}"
fi

if [[ "${gui}" == "1" ]]; then
    exec ign gazebo -r -v 2 "${world}"
fi

exec xvfb-run -a ign gazebo -r -s -v 2 "${world}"
