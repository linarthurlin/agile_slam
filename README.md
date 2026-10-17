# Agile SLAM

A ROS 2 platform for GEM sensor integration, calibration, and SLAM experiments.

The first milestone ports the existing GEM simulator onto a pinned Ubuntu 22.04 / ROS 2 Humble image. The imported vehicle remains an e2-derived surrogate; it is not yet a measured GEM e6 model.

## Split PACMod runtime

The isolated multi-service simulation is available through scripts/deploy.py. See [runtime operation and limitations](docs/runtime.md) and [dynamic scenarios](docs/scenarios.md). It uses the shared vehicle controller and PACMod mock; the legacy deployment is retained in Git history.

## Layout

- `containers/`: derived runtime and entrypoint.
- `ros2_ws/src/`: simulator packages and platform bringup.
- `config/`: shared runtime configuration.
- `scripts/`: environment audit and validation tools.
- `docs/`: setup, validation, and implementation plans.
- `third_party/`: source provenance and retained license information.

## Baseline

The local base image is `agile_control_ros2`, image ID `sha256:a6acca67607edcb48e66adfec152714ad480b0b0854587c6dcca72034f2084ca`. It includes Humble, FAST-LIO, PACMod2, Nav2, and RViz. It is not distributed by this repository.

```powershell
python scripts/doctor.py
python scripts/prepare_base.py
python scripts/deploy.py build
python scripts/deploy.py up
python scripts/deploy.py check
python scripts/deploy.py up --gui
python scripts/deploy.py enable
python scripts/deploy.py disable
python scripts/deploy.py down
```

The canonical `compose.yaml` uses image `agile_slam:humble`, project `agile-slam`, and explicit container names without numeric suffixes. The default profile uses software rendering and a private Docker bridge network. It starts simulation only, with no CAN or USB access. Ground-truth odometry is isolated under `/ground_truth/odometry`; no operational odometry TF is fabricated from it.

To open Gazebo and RViz, run `bash scripts/gui.sh` from WSL after starting the simulator. See the setup guide for the PowerShell command.

See [setup](docs/setup.md), [validation](docs/validation/baseline.md), [roadmap](docs/roadmap.md), and the [implementation plan](docs/plans/implementation_plan.md). Plans are written in Traditional Chinese; code, configuration, operational documentation, and commit messages are written in English.

## Validation status

The current image builds five ROS packages. Sensor streams, PACMod mock interlocks and selected Nav2 scenarios have local validation; historical baseline evidence remains available. Large image/cloud checks use reliable subscriptions; best-effort transport loss was observed and remains a separate performance gate. See the validation report for evidence and limits.

The [renderer investigation](docs/validation/render_stalls.md) retains the software-renderer failures. The WSL NVIDIA candidate adds a checksum-verified matching Ogre renderer plugin and a city terrain visual mesh. See [GPU remediation validation](docs/validation/gpu_runtime.md) for executed evidence and remaining gates. Use `python scripts/deploy.py up --gui --rendering gpu` for that capability-checked path; the default remains software.

## Navigation experiments

The current Nav2 runtime adds a generated obstacle scene, wheel-feedback odometry, a filtered obstacle scan, Smac Hybrid-A* planning, and Regulated Pure Pursuit control. See [navigation setup](docs/navigation.md), [scene candidates](docs/scenes.md), and the [simulation-first plan](docs/plans/simulation_first_plan.md).

The selected outdoor scene is [small_city](docs/small_city.md), with pinned asset preparation, Fortress conversion, and a conservative road map.

## Scope

Basic sensor schema/rate checks and known-start static Nav2 navigation are available. Sustained transport/recording, FAST-LIO, measured e6 geometry, full sensor profiles, calibration, and real-vehicle PACMod bringup remain subsequent milestones. The existing snapshot LiDAR must not be presented as a validated rolling-scan or deskew model. Humble/Fortress remains the active platform; maintenance migration is planned.

## Attribution

Imported GEM assets retain their upstream BSD licenses. See [third-party notices](third_party/README.md). The base image contains additional dependencies with their own licenses; publishing this source repository does not redistribute that image.
