# Development and Simulation Setup

## Prerequisites

- Windows with WSL2 and Docker Desktop using the Linux container engine.
- WSL integration enabled for the Ubuntu 22.04 distribution.
- The local Linux/amd64 image `agile_control_ros2` with ID `sha256:a6acca67607edcb48e66adfec152714ad480b0b0854587c6dcca72034f2084ca`.
- The Small City assets prepared under `assets/small_city/`.
- VS Code with the Dev Containers extension for containerized editing.

The inherited image is local-only and is not downloaded or redistributed by this repository.

## Prepare the runtime

From PowerShell at the repository root:

```powershell
python -m pip install -r scripts/requirements-scenes.txt
python scripts/prepare_small_city.py
python scripts/prepare_base.py
python scripts/deploy.py build
```

The build creates `agile_slam:humble` from the pinned local base. The simulator and runtime services are not started during the build.

## Open the development container

Open the repository in VS Code and select **Dev Containers: Reopen in Container**. The development Compose file starts only `0025-dev`. It mounts this repository at `/workspaces/Agile_SLAM` and runs `colcon build` after creation. It does not start Gazebo, Nav2, localization, or vehicle-control.

## Run the simulator

```powershell
python scripts/deploy.py up
python scripts/deploy.py check
python scripts/deploy.py status
```

The headless simulation profile starts the three shared ROS services, Gazebo server, and the simulation bridge. To launch the graphical mode:

```powershell
python scripts/deploy.py down
python scripts/deploy.py up --gui
```

The `up` command always stops and cold-starts the full Agile SLAM project so all services use the same Gazebo `/clock`. GUI mode opens Gazebo inside `0025-gazebo` and starts the optional `0025-rviz` service through WSLg. Closing the Gazebo window exits the Gazebo server as well.

Stop the project with:

```powershell
python scripts/deploy.py down
```

The runtime Compose project does not expose physical serial or CAN devices. The PACMod2 mock is a ROS-message-level simulation adapter only.

## Troubleshooting

- If build reports a missing base image, verify the supplied image ID and rerun `python scripts/prepare_base.py`.
- If deployment reports missing Small City files, rerun `python scripts/prepare_small_city.py` and confirm `assets/small_city/worlds/small_city.sdf` exists.
- If `--gui` reports WSLg unavailable, verify `/mnt/wslg/.X11-unix/X0` from the Ubuntu 22.04 WSL distribution.
- If simulation time appears frozen after a container change, stop the complete profile and start it again. Do not independently restart Gazebo while clock-consuming ROS nodes remain active.

The new split Compose configuration still needs a clean build and runtime acceptance run. Historical validation evidence is available under `docs/validation/`, but it was collected on the previous container topology.
