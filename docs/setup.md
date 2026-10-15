# Local baseline setup

Prerequisites: Docker Desktop using Linux containers and WSL2 integration, Python 3, and the supplied `agile_control_ros2` image. The image must match the ID documented in the README. The public repository cannot download this local image automatically.

Run `python scripts/prepare_base.py`, then `python scripts/doctor.py`. Build with `docker compose build`. Build output embeds a resolved package inventory at `/opt/agile_slam_metadata/packages.tsv`; no service rebuilds the workspace on startup.

Start with `docker compose up -d`, inspect `docker compose logs`, and run the baseline checker from the README. Stop with `docker compose down`. Source changes require an image rebuild. The baseline deliberately uses software rendering; GPU and WSLg GUI are separate validation gates.

Only `artifacts/` is mounted writable. Do not mount over `/workspace`: this would hide the base image workspace. Do not attach real CAN/USB devices to the simulation service.

The default ROS domain is 42 and can be overridden through `ROS_DOMAIN_ID`. All participants must use compatible message definitions and QoS. The validated single-container DDS profile uses loopback with larger fragments for image and point-cloud transport. A separate non-loopback profile is required before splitting containers; cross-container transport is a later gate.

The import retains upstream `gem_*` package names to keep the initial port reviewable. `avl_bringup` owns the adapted launch path. No measured e6 parameters or real-vehicle enable settings are supplied.

## Gazebo and RViz through WSLg

With the simulator running, open a PowerShell terminal in the repository and run:

```powershell
wsl -d Ubuntu-22.04 -- bash /mnt/d/UCSD/Lectures/AVL/Agile_SLAM/scripts/gui.sh
```

Alternatively, from a WSL terminal at the repository root, run `bash scripts/gui.sh`.

The launcher opens `agile-slam-gazebo` and `agile-slam-rviz` as GUI-only clients. They share the running simulator's network namespace, ROS domain, and Gazebo partition. X11 is forwarded through the WSLg socket and rendering uses Mesa software rendering. The simulator is not restarted.

RViz uses `base_link` as its fixed frame and displays the robot model, LiDAR cloud, and front camera. This local view deliberately does not add a ground-truth operational odometry transform. Large cloud/image displays use reliable QoS.

Close the windows or stop the clients with:

```powershell
docker stop agile-slam-gazebo agile-slam-rviz
```

The simulation server continues running. Stop GUI clients before recreating the simulation container, then run the launcher again against the new server. The GUI containers reuse the same network namespace; this is not the separate-container DDS transport acceptance gate.
