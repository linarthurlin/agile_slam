# Simulation Runtime

## Status

The runtime has been split into dedicated services and validated on the local Windows 11 + WSL2 Ubuntu 22.04 desktop. The current acceptance includes an image build, service readiness, visible Gazebo/RViz operation, and all three goals in the curve route with GPU simulation rendering. See [the acceptance report](validation/simulation-runtime-2026-10-31.md) for exact evidence and limits.

The active software baseline is Ubuntu 22.04, ROS 2 Humble, Gazebo Fortress, amd64, and CycloneDDS. The local base image is required and is not published by this repository.

## Service layout

| Compose service | Container | Responsibility |
| --- | --- | --- |
| `autonomy` | `0025-autonomy` | Robot description and TF, obstacle processing, map, Nav2, and readiness |
| `localization` | `0025-localization` | Current simulation-only wheel odometry and known-start alignment |
| `vehicle-control` | `0025-vehicle-control` | Shared speed/steering controller and `pacmod2_msgs` command adapter; no CAN access |
| `gazebo` | `0025-gazebo` | Small City world, vehicle and sensors, simulated clock and joints; GUI is optional in this same container |
| `sim-bridge` | `0025-sim-bridge` | Gazebo-to-ROS sensor bridges, vehicle spawn/controller setup, and PACMod2 ROS mock |
| `rviz` | `0025-rviz` | Optional ROS visualization |
| `dev` | `0025-dev` | Optional Dev Container for editing and colcon build; it does not start the simulator |

The root `compose.yaml` holds the common ROS runtime services. `compose.sim.yaml` adds the simulator backend. `compose.dev.yaml` contains the separate development service. The WSLg and GPU overrides in `deploy/` contain desktop-only settings. All runtime services use the private `agile-slam-ros` bridge network and the same ROS domain.

## Data paths

Sensor data flows from Gazebo through Gazebo Transport into `sim-bridge`, then onto ROS 2 sensor topics. The simulation does not emulate serial, USB, Ethernet sensor protocols, NTRIP/RTCM, SocketCAN, or CAN frames.

The control path is:

```text
Nav2 /cmd_vel
    -> vehicle-control
    -> pacmod2_msgs commands
    -> sim-bridge PACMod2 mock
    -> /simulation/actuation
    -> Gazebo joint controllers
    -> simulated joint feedback and PACMod2 reports
```

The mock exercises the ROS command/report contract and safety state transitions. It does not validate a physical PACMod ECU or CAN transport.

## Operations

Prepare the local base image and Small City assets first; see [setup](setup.md). From the repository root:

```powershell
python scripts/deploy.py build
python scripts/deploy.py up
python scripts/deploy.py check
python scripts/deploy.py status
python scripts/deploy.py down
```

Headless mode runs Gazebo server without its GUI. The `up` action first stops the full Agile SLAM project, then starts a cold profile so all time-dependent nodes attach to the same `/clock`. To open Gazebo and RViz on WSLg:

```powershell
python scripts/deploy.py down
python scripts/deploy.py up --gui
```

The GUI runs in the Gazebo service inside `0025-gazebo`; closing its window stops the attached simulation server. Switching GUI/headless mode or software/GPU rendering requires a cold start so all consumers attach to the same `/clock`. Use `down` when stopping the project without immediately restarting it.

For WSL2 GPU mode, `python scripts/deploy.py up --gui --rendering gpu` runs the GPU-accelerated Gazebo sensor server under Xvfb and attaches a separate software-rendered Gazebo GUI client to the same world. This works around the WSLg D3D12/GLX context failure seen when the GUI shares the accelerated server process. RViz is a separate WSLg client. Start the deployment from Windows PowerShell or the Ubuntu-22.04 WSL distro so the WSLg sockets and GPU overlay resolve in the Linux environment.

The simulation Compose overlay sets `AGILE_SIM_COMMAND_TIMEOUT=1.5` seconds to tolerate the measured WSL2 scheduling gap during GPU simulation. This override is simulation-only; the shared vehicle settings retain their 0.75-second default outside the simulation overlay.

Actuation is disabled at startup. `enable` is a simulation-only explicit enable; it does not enable a real vehicle. `test` exercises the mock contract and intentionally leaves it disabled with a readiness fault latched. Hardware and replay modes are unavailable and fail closed. The simulation profile receives no CAN or USB devices.

## Development container

Open the repository in VS Code and choose **Reopen in Container**. Dev Containers starts only `0025-dev`, mounts the source tree, and builds the ROS workspace in that checkout. Gazebo and the runtime services stay stopped until started separately with `scripts/deploy.py`.

## Limits

The current vehicle is an e2-derived surrogate, not a measured GEM e6 model. Localization is wheel odometry with a known-start alignment, not LIO. The current LiDAR model does not provide validated per-point firing times. The image inherits the local `agile_control_ros2` base; its complete source provenance is not yet reproducible from this public repository.

The vehicle deployment overlay, real sensor drivers, UM982 serial integration, PACMod2 CAN driver path, calibration workflow, and hardware read-only bringup remain unimplemented. Curve-route acceptance does not cover intersections, injected runtime faults, hardware interfaces, or extended-duration operation.
