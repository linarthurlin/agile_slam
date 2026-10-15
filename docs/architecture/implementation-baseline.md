# Implementation baseline: shared Humble platform

Status: Implementation specification; the split runtime and PACMod mock are not yet implemented.
Date: 2026-10-15.

This document and the linked Traditional Chinese execution plan consolidate ADR 0002 and the earlier deployment research. ADR 0001's Jazzy platform proposal is superseded. The current repository remains a working single-runtime simulation baseline.

## Fixed decisions

- Ubuntu 22.04 amd64, ROS 2 Humble, Gazebo Fortress, CycloneDDS.
- Windows/WSL2 Ubuntu 22.04 with Docker Desktop for development; native Linux with Docker Engine for the vehicle. Vehicle OS is believed to be Ubuntu 22 but is unverified.
- Shared application source and release image digests; host-specific network, display, device, time, and tuning overlays.
- Private bridge networking for desktop containers; initially Linux host networking for vehicle ROS/data-plane services. No service relies on the simulator network namespace.
- Independent core, localization, vehicle-control, and backend lifecycles. Compatible services may share images and contain multiple ROS processes.
- Sim, vehicle-readonly, vehicle, and replay are mutually exclusive deployment modes. GUI/recording are optional. Hardware modes remain unavailable until their actual backend is implemented and verified.
- Keep inherited e2 geometry and small_city. e6 references remain inactive. Keep software rendering as the accepted baseline; GPU rendering is experimental.

## Service responsibilities

| Service | Responsibilities | Backend dependence |
|---|---|---|
| core | robot description/static TF, obstacle projection, map/Nav2, readiness coordination | consumes sensor/pose contracts; does not launch or own Gazebo |
| localization | initially wheel-debug odometry; later LIO/localization | wheel-debug depends on sim joint feedback and is not a hardware-ready estimator |
| vehicle-control | setpoint conversion, speed feedback control, arbitration/freshness, PACMod message adapter | consumes backend reports; never owns real or simulated hardware |
| backend-sim | Gazebo, spawn, sim controllers, sensor bridges, PACMod mock/actuator adapter | publishes measurements, reports, and the only simulation clock |
| backend-hardware | verified physical sensor/PACMod drivers and transport | requires actual inventory, board/firmware/DBC, and host setup |
| tools | RViz, Gazebo GUI, recording and independent evaluation | optional and individually restartable |

## Contracts

Humble Nav2 keeps geometry_msgs/Twist on /cmd_vel. Vehicle-control normalizes speed and road-wheel angle into ackermann_msgs/AckermannDriveStamped on /vehicle/setpoint (planned). This setpoint is not an actuator bypass: only the vehicle-control/PACMod controller may consume it to generate PACMod commands. Separate the setpoint converter and controller internally so their timeouts cannot be refreshed by stale values.

The provisional PACMod contract uses installed pacmod2_msgs, including PositionWithSpeed, SystemCmdFloat, SystemCmdInt, VehicleSpeedRpt, and GlobalRpt. Exact driver endpoint/remapping and report availability must be checked against the installed ROS2 package, not copied from the upstream default-branch ROS1 README. Full raw sensor/PACMod schemas will be machine-checked before the new runtime is accepted.

The simulated actuator adapter is backend-private. In the mandatory mock profile, no legacy /cmd_vel-to-joint or /vehicle/setpoint-to-joint route is allowed. Reports come from simulated feedback, not command echo. The mock's vehicle response and steering map are engineering assumptions until calibrated.

/clock has one owner in sim/replay and no simulator owner in vehicle. Each TF edge has one authority. Known-start map->odom and wheel-debug odometry are sim-only. LIO and wheel feedback must not publish competing odom transforms or be fused without accounting for correlated inputs.

## Startup and failure behavior

Avoid circular Compose dependencies: start description/core infrastructure, then the backend, then wait for controller/sensor/report readiness. Start the estimator and activate Nav2 only after required TF/pose inputs exist. Vehicle-control starts disabled. Docker process state and depends_on ordering are not ROS readiness.

If the backend exits, core may remain alive but navigation must deactivate/cancel and vehicle-control must reject further actuation. Restart does not automatically enable vehicle control. Define monotonic receipt freshness separately from message acquisition time, simulation pause/reset, and replay timing.

Vehicle-readonly requires an enforced transmit policy. A driver that sends startup, heartbeat, enable, or command frames is not automatically passive just because no Nav2 command producer exists. Verify a real read-only path, or use a passive report receiver and leave the transmitting driver disabled. Replay never opens real actuator transport.

## Acceptance sequence

1. Capture current package/message/image provenance and pin the shared configuration.
2. Build an isolated split-runtime simulation on a distinct project/domain/Gazebo partition. Preserve the current working stack.
3. Verify cross-container sensor/TF delivery, independent GUI restarts, cold starts, backend-stop handling, and existing 3/8/16 m routes.
4. Make the PACMod mock route mandatory and test enable, gear, override/fault, command/report timeout, invalid/NaN input, clock reset, restart, and accelerator/brake exclusivity.
5. Add repeated turns/junctions, dynamic bag/replay, long-duration delivery and performance tests.
6. Add rolling-scan/LIO and calibration only behind their own fidelity gates. Qualify hardware afterward.

Source checks currently do not constitute runtime, CAN, driver, or sustained-performance validation. All missing physical inventory remains explicit and does not block simulation-only refactoring.

Detailed scope, target files, and exit criteria: [execution baseline](../plans/implementation_baseline.md).
