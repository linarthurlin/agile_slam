# Split simulation runtime

This experimental profile uses Ubuntu 22.04, ROS 2 Humble, Gazebo Fortress and CycloneDDS on amd64. It preserves the original Compose baseline, but the two profiles should not run together on a resource-limited desktop.

## Services

| Service | Responsibility |
| --- | --- |
| core | Robot description, obstacle scan, map, Nav2 and readiness |
| localization | Wheel-feedback odometry and known-start map alignment |
| vehicle-control | Command freshness, speed feedback control and PACMod commands |
| backend-sim | Gazebo, sensor bridges, PACMod mock and private joint adapter |
| rviz / gazebo-gui | Optional independent WSLg clients |

All services share a private bridge, ROS domain 44 and Gazebo partition `agile-slam-next`. GUI services do not borrow a simulator network namespace. Images and service boundaries are independent concepts: these services currently share one bootstrap image.

## Operation

Prepare the existing local base image and small_city assets using the setup guides first. From the repository root:

```powershell
python scripts/deploy.py build
python scripts/deploy.py up
python scripts/deploy.py check
python scripts/deploy.py enable
python scripts/deploy.py up --gui
python scripts/deploy.py disable
python scripts/deploy.py status
python scripts/deploy.py down
```

Enable is explicit and intended only for the simulated backend. Starting services never enables actuation. `up --gui` delegates to Ubuntu-22.04 under WSL on Windows; override the distribution with `AGILE_WSL_DISTRO`. Software rendering is the supported desktop baseline.

`python scripts/deploy.py test` exercises the ROS PACMod mock contract, including invalid reports. It deliberately latches a readiness fault and leaves the mock disabled. Restart core to clear that latch, check readiness, then explicitly enable if needed. Backend restart resets simulation time: perform `down`, then `up` to restart all clock-sensitive services together.

Hardware, vehicle-readonly and replay CLI modes currently reject execution. No CAN devices are exposed by this profile.

## Control and readiness

Nav2 publishes `/cmd_vel`; shared vehicle-control produces PACMod acceleration, brake, steering-shaft and shift commands. The mock consumes complete command cycles and publishes `/simulation/actuation` to the joint adapter. Reports use measured simulated wheel and steering feedback. The legacy direct Twist adapter is absent.

Monotonic receipt timestamps enforce command and report freshness. Startup waits for advancing clock, sensor/odometry/report streams, map and TF before activating Nav2. Stream loss inhibits control, cancels navigation and latches a fault. Clearing an override or mock fault never automatically enables actuation.

The single-goal navigation tree computes an initial path, replans until within one metre, and retains that path during the final approach. FollowPath still owns goal acceptance and obstacle checking; the one-metre condition does not report navigation success. Goal replacement during an active approach and NavigateThroughPoses have not been accepted; cancel the active goal before sending another.

## Configuration and limits

`gem_description/config/vehicle.json` is the common controller/odometry/navigation geometry reference. `scripts/validate_contracts.py` checks it against inherited URDF geometry before deployment. `config/interfaces/runtime.json` records the provisional interface contract.

The vehicle remains an e2 surrogate. PACMod2 interfaces, steering ratio and plant gains are provisional, not measured e6 values. No CAN, ECU firmware, braking-distance or actual actuator calibration claim follows from these tests. Localization is wheel odometry with known-start map alignment, not LIO. The LiDAR remains a snapshot sensor without per-point firing times.

The image still inherits the user's local `agile_control_ros2` base, including its PACMod messages. Its source provenance is incomplete; a clean source-pinned image is a later milestone. The Dockerfile records installed Debian packages but does not make the inherited base publicly reproducible.
