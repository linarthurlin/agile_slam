# Simulation Runtime

## Status

The repository is being moved from a combined simulator container to separate runtime services. The Compose files, Gazebo bridge launch, container names, and Dev Container target have been updated. The rebuilt image and new multi-container runtime have not yet been started or validated; local WSL2 and Docker remain paused.

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

The GUI runs in the Gazebo process inside `0025-gazebo`; closing its window exits that Gazebo process. The same cold-start behavior applies when switching between GUI and headless modes or changing software/GPU rendering. Use `down` when stopping the project without immediately restarting it.

Actuation is disabled at startup. `enable` is a simulation-only explicit enable; it does not enable a real vehicle. `test` exercises the mock contract and intentionally leaves it disabled with a readiness fault latched. Hardware and replay modes are unavailable and fail closed. The simulation profile receives no CAN or USB devices.

## Development container

Open the repository in VS Code and choose **Reopen in Container**. Dev Containers starts only `0025-dev`, mounts the source tree, and builds the ROS workspace in that checkout. Gazebo and the runtime services stay stopped until started separately with `scripts/deploy.py`.

## Limits

The current vehicle is an e2-derived surrogate, not a measured GEM e6 model. Localization is wheel odometry with a known-start alignment, not LIO. The current LiDAR model does not provide validated per-point firing times. The image inherits the local `agile_control_ros2` base; its complete source provenance is not yet reproducible from this public repository.

The vehicle deployment overlay, real sensor drivers, UM982 serial integration, PACMod2 CAN driver path, calibration workflow, and hardware read-only bringup remain unimplemented. Existing validation reports document the previous topology and must not be treated as acceptance evidence for this refactor.
