# Agile SLAM

A ROS 2 platform for GEM sensor integration, calibration, and SLAM experiments.

The active baseline is Ubuntu 22.04, ROS 2 Humble, Gazebo Fortress, and amd64. The imported vehicle remains an e2-derived surrogate; it is not a measured GEM e6 model.

## Architecture

The runtime is split into small services: autonomy, localization, vehicle-control, Gazebo, and a simulation bridge. Gazebo GUI can be selected at startup inside the Gazebo service; RViz remains optional. A separate Dev Container supports editing and colcon builds without starting simulation.

See [runtime operations and limitations](docs/runtime.md), [setup](docs/setup.md), and the [architecture decisions](docs/architecture/).

## Repository layout

- `.devcontainer/`: VS Code Dev Container configuration.
- `containers/`: shared runtime image, developer target, and process entrypoints.
- `compose.yaml`, `compose.sim.yaml`, `compose.dev.yaml`: common runtime, simulation, and development services.
- `deploy/`: WSLg and GPU-specific Compose overlays.
- `ros2_ws/src/`: ROS 2 packages and platform bringup.
- `config/`: shared runtime configuration and interface contracts.
- `scripts/`: deployment, environment inspection, and validation tools.
- `docs/`: setup, validation, and implementation records.
- `third_party/`: source provenance and license information.

## Local base image

The build uses the local image `agile_control_ros2`, ID `sha256:a6acca67607edcb48e66adfec152714ad480b0b0854587c6dcca72034f2084ca`. It includes ROS 2 Humble, FAST-LIO, PACMod2 messages/driver, Nav2, and RViz. It is not distributed by this repository.

```powershell
python scripts/doctor.py
python -m pip install -r scripts/requirements-scenes.txt
python scripts/prepare_small_city.py
python scripts/prepare_base.py
python scripts/deploy.py build
python scripts/deploy.py up
python scripts/deploy.py check
python scripts/deploy.py status
python scripts/deploy.py down
```

Use `python scripts/deploy.py up --gui` to cold-start Gazebo with its GUI and open RViz through WSLg. Every `up` starts the full project from a clean state so all simulation-time consumers restart together.

## Simulation boundary

The simulator publishes ROS sensor data; it does not emulate serial, USB, Ethernet sensor protocols, NTRIP/RTCM, SocketCAN, or CAN frames. PACMod is represented by a `pacmod2_msgs` ROS-level mock that maps commands to Gazebo joints and creates feedback reports. No physical device is exposed to the simulation Compose project.

## Status and limitations

The split runtime has been built and exercised on the local Windows 11 + WSL2 Ubuntu 22.04 desktop. The current acceptance includes an image build, PACMod mock runtime checks, GPU renderer preflight, and all three goals in the curve route with Gazebo and RViz open. See the [current runtime acceptance report](docs/validation/simulation-runtime-2026-10-31.md) for the tested image, route results, and remaining limits.

The current vehicle is an e2-derived surrogate. The current acceptance covers the curves route only; intersection routes, dynamic fault injection, and long-duration transport are not yet accepted on this split runtime. LIO, rolling-scan LiDAR timing, full sensor profiles, calibration, the UM982 serial service, the real PACMod2/CAN driver service, and vehicle deployment mode remain future milestones. See [the roadmap](docs/roadmap.md) and [the simulation-first plan](docs/plans/simulation_first_plan.md).

Project code, README, configuration, and operational documentation use English. Implementation plans use Traditional Chinese.
