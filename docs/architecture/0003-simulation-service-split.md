# ADR 0003: Split simulation and development services

Status: Accepted; initial implementation is in progress.
Date: 2026-10-31.
Supersedes the runtime packaging portion of ADR 0001/0002 after runtime acceptance. The Ubuntu 22.04 / ROS 2 Humble / Gazebo Fortress baseline remains unchanged.

## Context

The previous Compose definition grouped the Gazebo server, ROS bridges, model spawn, simulated controllers, and PACMod mock in one service. It also used a separate GUI-only Gazebo container. That made the application layers and the simulator backend share a lifecycle and obscured the intended sensor and vehicle-control boundaries.

The project needs one codebase that supports desktop simulation and a future Linux vehicle computer. The user selected a separate development environment, a separate vehicle-control service, a separate localization service, a ROS-level PACMod2 mock for simulation, and hardware services grouped by device access or SDK. Sensor protocols do not need simulation.

## Decision

- Keep `compose.yaml` as the common runtime definition and add small mode-specific Compose overlays.
- Run `autonomy`, `localization`, and `vehicle-control` as independent ROS services.
- Run Gazebo server and its optional GUI in one `gazebo` service. Headless mode is the default; `deploy.py up --gui` selects the GUI process and starts RViz.
- Run Gazebo↔ROS sensor bridges, robot spawn/controller setup, and the `pacmod2_msgs` mock in `sim-bridge`.
- Keep one runtime image across the compatible ROS services. Keep a separate Dockerfile `dev` target and Compose project for editor/build tools; opening the Dev Container must not start the simulation.
- Use explicit runtime container names beginning with `0025-`.
- Simulated sensors publish ROS sensor data. Do not emulate serial, USB, Ethernet sensor transport, NTRIP/RTCM, SocketCAN, or CAN frames. PACMod simulation ends at the ROS command/report interface and maps commands to Gazebo joints.
- Do not enable a vehicle Compose mode until its real sensor drivers, UM982 serial ownership, PACMod2 driver/CAN access, clock, TF, and safe read-only startup behavior have explicit implementation and acceptance evidence.

## Consequences

- A Gazebo failure no longer directly terminates the autonomy or vehicle-control processes. Readiness must inhibit navigation and motion when required data stops.
- ROS 2 DDS and Gazebo Transport must work across the configured service network. The previous same-container or shared-network-namespace validation does not prove this new topology.
- Gazebo owns simulation time. Restarting or changing its GUI/rendering mode requires restarting all clock-sensitive services together.
- Closing the integrated Gazebo GUI closes the Gazebo process and server. This is accepted for the initial mode-selection interface; RViz remains a separate optional service.
- `compose.vehicle.yaml` and a replay deployment are deferred until their runtime contracts and drivers are implemented. A placeholder mode must fail closed rather than start simulator data under a hardware label.

## Initial acceptance gates

1. Build the runtime and developer image targets from the pinned local base.
2. Start all five headless simulation containers with the expected names and one ROS domain.
3. Verify cross-container delivery of `/clock`, `/tf`, sensor topics, PACMod reports, and command traffic.
4. Confirm Nav2 reaches the Gazebo joints only through `pacmod2_msgs` and the simulation mock.
5. Repeat the existing route and moving-fault checks on the new topology.
6. Confirm that opening and closing the Dev Container does not start, stop, or reset the simulation.

Until these gates pass, prior validation reports remain historical evidence for the previous topology.
