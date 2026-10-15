# Agile SLAM

A ROS 2 platform for GEM sensor integration, calibration, and SLAM experiments.

The first milestone ports the existing GEM simulator onto a pinned Ubuntu 22.04 / ROS 2 Humble image. The imported vehicle remains an e2-derived surrogate; it is not yet a measured GEM e6 model.

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
docker compose build
docker compose up -d
docker compose exec sim /agile_slam_entrypoint.sh python3 /opt/agile_slam_ws/src/avl_bringup/scripts/check_baseline.py
docker compose exec sim /agile_slam_entrypoint.sh python3 /opt/agile_slam_ws/src/avl_bringup/scripts/check_commands.py
docker compose down
```

The default profile uses software rendering and a private Docker bridge network. It starts simulation only, with no CAN or USB access. Ground-truth odometry is isolated under `/ground_truth/odometry`; no operational odometry TF is fabricated from it.

See [setup](docs/setup.md), [validation](docs/validation/baseline.md), and the [implementation plan](docs/plans/implementation_plan.md). Plans are written in Traditional Chinese; code, configuration, operational documentation, and commit messages are written in English.

## Validation status

The local baseline builds all three packages, delivers all seven required streams, and passes a low-speed command-expiry test. Large image/cloud checks use reliable subscriptions; best-effort transport loss was observed and remains a separate performance gate. See the validation report for evidence and limits.

## Scope

Sensor schema/timing checks, FAST-LIO integration, measured e6 geometry, full sensor profiles, calibration, and real-vehicle PACMod bringup are subsequent milestones. The existing snapshot LiDAR must not be presented as a validated rolling-scan or deskew model. Fortress is a legacy reproduction baseline; the supported-platform migration remains planned.

## Attribution

Imported GEM assets retain their upstream BSD licenses. See [third-party notices](third_party/README.md). The base image contains additional dependencies with their own licenses; publishing this source repository does not redistribute that image.
