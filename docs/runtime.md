# Split simulation runtime

This experimental profile uses Ubuntu 22.04, ROS 2 Humble, Gazebo Fortress and CycloneDDS on amd64. The sole active deployment is root `compose.yaml`, project `agile-slam`, image `agile_slam:humble`. Legacy deployments remain in Git history.

## Services

| Service | Container | Responsibility |
| --- | --- | --- |
| core | agile-slam-core | Description, obstacle scan, map, Nav2 and readiness |
| localization | agile-slam-localization | Wheel odometry and known-start alignment |
| vehicle-control | agile-slam-vehicle-control | Speed control and PACMod commands |
| backend-sim | agile-slam-simulator | Gazebo server, bridges, mock and joint adapter |
| gazebo-gui | agile-slam-gazebo | Optional Gazebo client |
| rviz | agile-slam-rviz | Optional visualization client |

All services share a private bridge, ROS domain 44 and Gazebo partition `agile-slam`. GUI services do not borrow a simulator network namespace. Images and service boundaries are independent concepts: these services currently share one bootstrap image.

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

Enable is explicit and intended only for the simulated backend. Starting services never enables actuation. `up --gui` delegates to Ubuntu-22.04 under WSL on Windows; override the distribution with `AGILE_WSL_DISTRO`. Software rendering remains the default fallback. For the validated WSL NVIDIA capability path, use `python scripts/deploy.py up --gui --rendering gpu`. GPU preflight rejects missing acceleration, copy-image support or mismatched patched-plugin provenance.

`python scripts/deploy.py test` exercises the ROS PACMod mock contract, including invalid reports. It deliberately latches a readiness fault and leaves the mock disabled. Restart core to clear that latch, check readiness, then explicitly enable if needed. Backend restart resets simulation time: perform `down`, then `up` to restart all clock-sensitive services together.

Hardware, vehicle-readonly and replay CLI modes currently reject execution. No CAN devices are exposed by this profile.

## Control and readiness

Nav2 publishes `/cmd_vel`; shared vehicle-control produces PACMod acceleration, brake, steering-shaft and shift commands. The mock consumes complete command cycles and publishes `/simulation/actuation` to the joint adapter. Reports use measured simulated wheel and steering feedback. The legacy direct Twist adapter is absent.

Monotonic receipt timestamps enforce command and report freshness. Startup waits for advancing clock, sensor/odometry/report streams, map and TF before activating Nav2. Stream loss inhibits control, cancels navigation and latches a fault. Clearing an override or mock fault never automatically enables actuation.

The single-goal navigation tree computes an initial path, checks its validity at 1 Hz, and replans only if it becomes invalid. FollowPath still owns goal acceptance and local collision checking. A failed initial plan or failed replacement of an invalid path aborts the task. Goal replacement during an active approach and NavigateThroughPoses have not been accepted; cancel the active goal before sending another.

## Configuration and limits

`gem_description/config/vehicle.json` is the common controller/odometry/navigation geometry reference. `scripts/validate_contracts.py` checks it against inherited URDF geometry before deployment. `config/interfaces/runtime.json` records the provisional interface contract.

The vehicle remains an e2 surrogate. PACMod2 interfaces, steering ratio and plant gains are provisional, not measured e6 values. No CAN, ECU firmware, braking-distance or actual actuator calibration claim follows from these tests. Localization is wheel odometry with known-start map alignment, not LIO. The LiDAR remains a snapshot sensor without per-point firing times.

The image still inherits the user's local `agile_control_ros2` base, including its PACMod messages. Its source provenance is incomplete; a clean source-pinned image is a later milestone. The Dockerfile records installed Debian packages but does not make the inherited base publicly reproducible.

Repeatable curved-route and moving-fault scenarios are available through `scripts/run_scenarios.py`. See [scenario operation and report semantics](scenarios.md). The runner cold-resets the isolated simulation and leaves actuation disabled.

## Navigation sensor profile

`gem_description/config/simulation.json` selects the split navigation sensor workload. It disables the inherited unbridged depth and secondary RGB cameras. The bridged front RGB definition remains 800x600 at 30 Hz; LiDAR remains 10 Hz, IMU 50 Hz and GPS 20 Hz. The legacy xacro default keeps auxiliary cameras enabled. Changing this installed configuration requires rebuilding the image and restarting the whole simulation.

This removes unused rendering work; it is not a validated full sensor suite or a guaranteed fix for backend stalls. The current scene's material defects and missing LiDAR firing times remain limitations.

Desktop DDS datagrams are capped at 1400 bytes with 1280-byte DDS fragments for the observed 1500-byte bridge MTU. Independent per-route monitors record MTU and IP fragmentation/reassembly counters. This corrects observed fragmentation exposure but does not eliminate all simulation-progress stalls; see [current validation](validation/canonical_runtime.md).


## Software renderer baseline

The simulation backend sets `LP_NATIVE_VECTOR_WIDTH=128` for Mesa llvmpipe. The original camera resolution/rate/noise and LiDAR sampling/rate remain enabled. This is a headless-tested desktop workaround, not a GPU configuration or a change to the vehicle application images. Dual-GUI navigation still has a reproduced rendering stall and is not accepted. Mesa documents vector-width selection in its [LLVMpipe guide](https://docs.mesa3d.org/drivers/llvmpipe.html).

Reducing renderer workers to four and removing the camera Gaussian noise pass both failed isolation tests; neither change is retained. Read `docs/validation/render_stalls.md` for positive and negative evidence and the remaining acceptance limits.

## WSL NVIDIA renderer

`deploy/desktop-gpu.yaml` is an overlay of the same project and image, not a second stack. Only the simulator receives `/dev/dxg`, read-only WSL libraries and WSLg display access. Application services retain their existing boundaries and private network.

The GL3Plus plugin is rebuilt from checksum-verified Ubuntu Ogre 2.2.5 sources with an NV_copy_image fallback. Generated Ogre feature definitions must match the installed core exactly; only the renderer plugin is replaced. See `third_party/ogre_next.json`. No OpenGL version or extension is fabricated. Compute-based Terra terrain rendering is replaced during city conversion by a visual mesh sampled from the source height image; existing collision geometry is unchanged. Terrain texture blending is not reproduced.

Readiness now publishes a session and advancing heartbeat sequence. Vehicle-control requires a live 0.5-second steady-time lease; its expiry latches inhibition until an explicit disable/enable cycle after readiness returns. Late lifecycle startup success cannot clear a readiness fault. PACMod cycles are buffered by distinct ROS stamps with bounded age and capacity. Repeated frozen-clock stamps do not refresh the mock watchdog. These remain simulation software contracts, not validated ECU timings.

Switching rendering modes recreates backend services. Run `down` before `up --rendering gpu` or returning to software so all clock-sensitive nodes restart together. Keep the same `--rendering` selection when adding GUIs to a running stack.
