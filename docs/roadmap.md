# Pending Task Roadmap

Status date: 2026-10-31
Implementation state: the simulation service split and Dev Container configuration are implemented. The Humble image was built and the split runtime passed its visible GPU curve-route acceptance (3/3 goals). Split-runtime intersection routes, moving-fault suite, sustained transport and record/replay remain open. The user's edits to `docs/plans/simulation_first_plan.md` remain preserved.
Platform: Ubuntu 22.04 / ROS 2 Humble / Gazebo Fortress on Windows + WSL2 + Docker Desktop.

## Mission and boundaries

The current stack is a simulation and software-integration baseline. It is not a measured GEM e6 digital twin, a validated LIO/SLAM system, or a real-vehicle deployment. The PACMod mock is part of the simulated control path at the pacmod2_msgs ROS command/report layer only; simulation does not emulate CAN. No physical CAN interface or PACMod driver is enabled.

Keep simulation and hardware backends behind the same ROS contracts where possible. Treat hardware mode as unavailable until its sensor inventory, vehicle host, PACMod generation, firmware, DBC and safety behavior are verified. Do not use simulator truth as an operational localization input.

## Current baseline

- The split Compose runtime has five core containers: autonomy, localization, vehicle-control, Gazebo, and sim-bridge. RViz is an optional sixth runtime container; the Dev Container is separate from runtime.
- The Humble image build, 52 Python unit tests, 13 PACMod ROS mock checks, GPU renderer preflight, live LiDAR bridge and visible GPU curve-route acceptance passed on 2026-10-31; see [the split runtime report](validation/simulation-runtime-2026-10-31.md).
- Only the curve route is accepted on the split topology so far. Intersection and moving-fault suites still need acceptance on this topology; historical passes on earlier deployment layouts do not transfer automatically.
- Shared Nav2 → vehicle-control → PACMod ROS commands → PACMod mock → simulated joints path.
- Wheel odometry and known-start map alignment; no operational LIO/SLAM.
- Snapshot LiDAR with x/y/z/intensity/ring and no per-point time.
- 52 Python unit tests pass; source/config, generated scene/map and vehicle/interface checks pass.
- Historical sensor, route and fault reports remain useful evidence but do not replace tests on the current split topology. Repeated routes, dynamic record/replay and sustained GUI transport remain open.
- Check local WSL/Docker state before each runtime session; this roadmap does not assert that the simulator is currently running.

## Priority definitions

- P0: Must be resolved before real-vehicle actuation.
- P1: Required for the next dependable simulator release or before the dated support transition.
- P2: Important capability expansion after the baseline is repeatable.
- P3: Later optimization or research after the preceding gates pass.

## Roadmap

### R0 — Restore one accurate project status

**Priority:** P1
**Status:** Open

The existing docs/current_state.md describes an earlier single-container deployment and stale image/domain values. Align the canonical state page with the six-service Compose runtime and link the current system report.

**Acceptance criteria**

- Record the reviewed commit, local modifications, image/base provenance, service names, ROS domain and Gazebo partition.
- Separate verified facts from configured values, assumptions and unknown vehicle hardware.
- Link the latest passing and failing validation evidence; preserve historical failures.
- Keep user-authored changes to the simulator-first plan intact.

### R1 — Close readiness and input-validation gaps

**Priority:** P1 for simulator reliability; P0 before hardware use
**Status:** Open

- Add a steady-time freshness check for dynamic TF used by readiness; reject stale or non-advancing transforms.
- Validate JointState names, array lengths, finite position/velocity values and stamps before steering kinematics.
- Add malformed sensor, stale-but-republished report, readiness-process loss and stale-TF regression cases.
- Verify the controller and mock remain inhibited on each failure and require explicit re-enable after recovery.
- Keep ROS/simulation time separate from monotonic safety receipt time.

**Acceptance criteria**

- Each injected fault has a machine-readable case report and retained first-fault diagnostics.
- Stale or malformed input cannot satisfy readiness or renew actuation permission.
- Recovery never automatically enables the mock.

### R2 — Re-establish repeatable simulator acceptance

**Priority:** P1
**Status:** Open; split-runtime intersection and fault acceptance pending

- Follow the staged gates in [the next simulation test plan](plans/simulation_test_phase_2.md).
- First run left and right intersection routes on the split runtime, then its three moving-fault cases.
- Integrate cancellation, goal replacement and NavigateThroughPoses acceptance into the scenario suite.
- Add 120-second simulated-time sensor rate/gap and transport measurements, then dynamic obstacle/contact-event checks and dynamic bag/replay.
- After single-run cases pass, run three repeated suites and a separate 20-minute dual-GUI soak.
- Track simulation time and wall time separately; capture RTF, topic stamp rate, wall receive rate, freshness faults, DDS/IP counters, CPU, memory and restart state.

**Acceptance criteria**

- Every route passes existing position/yaw and consecutive-rest criteria in repeated cold runs.
- No unexplained readiness latch, sensor timestamp regression or automatic re-enable occurs.
- Publish measured RTF and wall-time sensor throughput; do not label a slower-than-wall simulator real time.

### R3 — Complete transport and dynamic record/replay

**Priority:** P1
**Status:** Partial: stationary smoke evidence exists; dynamic acceptance remains open

- Record moving routes with required sensor, TF, clock, odometry, command and diagnostic topics.
- Define recording QoS overrides and a run manifest with source, image, configuration, scene and sensor profile fingerprints.
- Test late subscribers to transient/static TF, replay clock ownership, pause/reset/rewind and independent ROS domain playback.
- Measure sustained message loss and latency rather than relying only on topic presence or monotonic stamps.

**Acceptance criteria**

- A recorded route replays with one authoritative /clock and valid TF for late joiners.
- Sensor schema and deterministic scenario metrics meet documented tolerances.
- Missing messages, QoS incompatibility and replay time errors fail with clear diagnostics.

### R4 — Confirm physical vehicle and sensor inventory

**Priority:** P0 before hardware integration
**Status:** Blocked on physical facts

Collect and version a hardware manifest for:

- GEM e6 model year, measured wheelbase/track, axle origin, steering ratio/rate and sensor mounting positions.
- Vehicle computer CPU, Linux distribution/kernel, network interfaces, GPU and available container runtime.
- Velodyne model and firmware; three front LiDAR models; camera and RealSense models, serials and available streams.
- PACMod board generation/revision, firmware, vehicle type, DBC, CAN adapter and existing ROS driver.
- IMU and GNSS model (UM982 if selected), receiver/carrier/firmware, dual-antenna baseline, frame convention, timestamp source and synchronization method.

The chosen software contract is pacmod2_msgs/PACMod2 for both simulation and vehicle profiles. The physical board, firmware and DBC must still be verified before vehicle use; a ROS mock validates neither CAN frames nor ECU behavior.

**Acceptance criteria**

- Unknowns are either measured or explicitly tagged unresolved; no inferred e6 parameters silently replace the e2 simulation values.
- Sensor topic, frame, unit, timestamp, QoS and driver version contracts are recorded.

### R5 — Build hardware-faithful sensor and calibration profiles

**Priority:** P2
**Status:** Not started

- In simulation, generate sensor values in Gazebo or ROS adapters and publish ROS messages directly using the selected hardware-facing data contract. Do not emulate serial, USB, NTRIP/RTCM, CAN, or sensor Ethernet protocols; keep device and protocol tests in vehicle-only or hardware-bench work.
- For the actual Velodyne, implement and validate scan cadence, ring mapping, return/intensity semantics, point ordering and per-point acquisition times needed by the selected driver/LIO input.
- Define camera intrinsics, optical frames, depth scale/encoding, IMU axes/noise and GNSS frame/time behavior from device specifications and measurements.
- Keep GNSS simulation data-level: Gazebo/ROS adapters publish NavSatFix plus normalized heading/quality diagnostics with configurable covariance, noise, latency, drift, jumps and dropouts. Do not emulate serial ports, UM982 byte protocols, USB devices, NTRIP/RTCM transport, CAN, or receiver carrier-phase solving in simulation.
- Integrate the UM982 hardware driver only in the vehicle overlay behind the same ROS data contract. Audit Humble compatibility, serial endpoint enumeration, parsing, timestamps, heading reference, covariance, diagnostics and license before adopting an upstream driver.
- Record dual-antenna heading, measured baseline and lever arms, the actual serial endpoint mapping, PPS/time source, and the external NTRIP or Base-to-Rover RTCM path when that correction source is identified. Use captured receiver bytes for offline parser unit tests if needed; physical serial/RTK behavior requires the real receiver.
- Keep calibration truth separate from estimator inputs; add known-target and held-out calibration tests.
- Include timing offset, jitter, dropout, noise and extrinsic perturbation sweeps.

**Acceptance criteria**

- Simulated message schemas match the selected hardware-driver contract.
- LIO deskew is evaluated against independently known motion and scan timing.
- Calibration results include uncertainty, configuration version and held-out residuals.

### R6 — Integrate and evaluate localization / SLAM

**Priority:** P2
**Status:** Not started; FAST-LIO in the inherited image is not a validated running pipeline

- Pin the source revision and dependency chain for the chosen LIO/SLAM implementation.
- Define one owner per TF edge; remove known-start identity alignment from SLAM evaluation.
- Validate LiDAR/IMU extrinsics, timestamps, frame transforms, initialization and reset behavior.
- Evaluate GNSS separately from LIO: transform NavSatFix with a validated heading/datum, fuse only measured covariance, and ensure there is one TF authority.
- Evaluate map quality, ATE/RPE, drift, loop closure, degraded geometry and sensor failure on repeatable routes and recorded bags.

**Acceptance criteria**

- Estimator consumes only sensor inputs; ground truth is restricted to the evaluator.
- Results can be replayed from a versioned bag and manifest.
- Failure and recovery behavior is documented, not hidden by map alignment.

### R7 — Make images reproducible and prepare the support transition

**Priority:** P1
**Status:** Open

The build inherits a local base-image tag and leaves some apt dependencies floating. Additionally, ROS 2 Humble, Gazebo Fortress and Ubuntu 22.04 standard support are scheduled to end in May 2027. See the official [ROS 2 Humble release announcement](https://discourse.ros.org/t/ros-2-humble-hawksbill-released/25729), [Gazebo release schedule](https://gazebosim.org/docs/latest/releases/) and [Ubuntu release cycle](https://ubuntu.com/about/release-cycle).

- Capture and enforce the base image digest, package versions, source revisions and third-party renderer patch provenance.
- Produce a clean build without relying on undocumented local packages; retain license notices.
- Before 2027-02, choose a support strategy with the vehicle computer and driver inventory in hand.
- Evaluate a separate Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic candidate; keep Humble/Fortress as the rollback baseline until all ROS packages, sensor drivers, PACMod interfaces, rendering and route acceptance pass.
- Do not assume a container OS choice removes host kernel, SocketCAN, USB, NIC or GPU compatibility requirements.

**Acceptance criteria**

- An independent clean host can build or pull an immutable release image and verify its provenance.
- A selected supported platform has repeatable CI and simulator evidence before production migration.
- The transition plan accounts for OS, ROS, Gazebo and vendor-driver support separately.

### R8 — Implement real vehicle modes and PACMod backend

**Priority:** P0 before any actuator test
**Status:** Not started; CLI currently fails closed for hardware/replay modes

- Implement an explicit hardware sensor/vehicle backend and a verified passive vehicle-readonly mode.
- Use the driver matching the confirmed PACMod board; validate actual command/report topics and DBC.
- Isolate CAN device access and make actuator enable a separate, explicit operation.
- Test boot, disable, gear, command limits, steering conversion/rate, accelerator/brake interlock, stale reports, override, CAN timeout, process restart and emergency stop on a bench setup.
- Prove vehicle-readonly transmits no actuator/control frames; absence of Nav2 alone is not proof of passive operation.
- Keep replay unable to open actuator transport.

**Acceptance criteria**

- Bench CAN captures prove the expected frames and no transmission in read-only/replay mode.
- Every communication or readiness fault inhibits commands, records a cause and requires deliberate recovery.
- Only after bench acceptance, perform an approved low-speed closed-course validation with a measured vehicle configuration.

### R9 — Add an optional development container

**Priority:** P3
**Status:** Configuration implemented; clean build and editor lifecycle acceptance pending

A Dev Container is VS Code configuration for opening a development environment inside a container. It can reuse Docker Compose, but it is not a replacement for the runtime Compose architecture and does not imply one container per ROS node or sensor.

- The initial Dev Container inherits the existing local Humble image. Replace that dependency after the build becomes source-reproducible (R7).
- `.devcontainer/devcontainer.json` and `compose.dev.yaml` add a development-only service and Dockerfile target.
- The configured startup runs colcon in the mounted workspace and does not request Gazebo, RViz, PACMod, or hardware drivers.
- Do not mount the Docker socket, CAN device or physical sensor devices into the default development container.
- Keep normal simulation and vehicle runtime launched through the existing explicit deployment commands.

**Acceptance criteria**

- A WSL checkout opens the development container and builds the ROS workspace from the mounted source.
- Opening/rebuilding the Dev Container does not start or reset the simulator or a hardware mode.
- The runtime Compose files remain the source of truth for deploying the simulator and future vehicle profile.

## External compatibility references

- [ROS 2 Humble release announcement](https://discourse.ros.org/t/ros-2-humble-hawksbill-released/25729)
- [Gazebo ROS/Gazebo pairings](https://gazebosim.org/docs/jetty/ros_installation/)
- [Gazebo release schedule](https://gazebosim.org/docs/latest/releases/)
- [Ubuntu release cycle](https://ubuntu.com/about/release-cycle)
- [PACMod2 upstream driver](https://github.com/astuff/pacmod2)
- [ros_gz_bridge Humble message mappings](https://github.com/gazebosim/ros_gz/blob/humble/ros_gz_bridge/README.md)
- [Unicore UM982 specification](https://en.unicorecomm.com/products/um982/)
- [Unicore UM982eb evaluation board](https://en.unicorecomm.com/products/um982eb/)
- [Dev Containers documentation](https://code.visualstudio.com/docs/devcontainers/create-dev-container)
 [ros_gz_bridge NavSat conversion implementation](https://github.com/gazebosim/ros_gz/blob/humble/ros_gz_bridge/src/convert/sensor_msgs.cpp)
- [ROS REP 103 coordinate conventions](https://github.com/ros-infrastructure/rep/blob/master/rep-0103.rst)
- [robot_localization navsat_transform_node](https://github.com/cra-ros-pkg/robot_localization/blob/rolling-devel/doc/navsat_transform_node.rst)
- [UM982 ROS 2 community driver](https://github.com/AIRLab-POLIMI/um982_ros2_driver)
- [UM982eb user manual](https://en.unicorecomm.com/uploads/file/UM982eb_User%20Manual_EN_R1.2.pdf)

## Related project evidence

- [System inspection and code review (Traditional Chinese)](reviews/system_report_20261028.md)
- [Runtime operations and current limitations](runtime.md)
- [GPU/runtime validation](validation/gpu_runtime.md)
- [Dynamic scenario validation](validation/dynamic_scenarios.md)
- [Traditional Chinese simulator-first implementation plan](plans/simulation_first_plan.md)

