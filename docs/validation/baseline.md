# Baseline validation

Date: 2026-10-14 (America/Los_Angeles).

Machine-readable evidence: [baseline summary](baseline_summary.json).

## Environment

- Windows 11 with Docker Desktop 4.76.0 and Docker Engine 29.5.2.
- WSL2 kernel 6.6.114.1; Ubuntu-22.04 and Docker Desktop integration.
- Base image ID: `sha256:a6acca67607edcb48e66adfec152714ad480b0b0854587c6dcca72034f2084ca`.
- ROS 2 Humble; Gazebo Fortress; software rendering through Xvfb/Mesa.
- Single simulation container, isolated bridge network, no hardware device access.

## Passed

- Clean colcon build: `gem_description`, `gem_gazebo`, `avl_bringup`.
- Vehicle spawn and seven active controllers.
- ROS delivery: clock, 30,000-point LiDAR cloud, IMU, RGB image, camera information, joint states, and isolated ground-truth odometry.
- Cloud fields: `x`, `y`, `z`, `intensity`, `ring`.
- IMU frame: `IMU_link`; stationary acceleration approximately +9.81 m/s2 on z.
- Camera image and information use `camera_front_optical_frame`.
- No publisher on `/odom` or `/odometry/local` during the baseline check.
- A low-speed command test produced nonzero wheel commands and vehicle motion; all sampled commands after expiry were zero.
- Python/XML parsing and four regression tests covering command expiry, clock rewind, TF direction, and delayed geometry readiness.

The command test sent 0.5 m/s and 0.1 rad for two wall-clock seconds. One observed run moved approximately 0.91 m longitudinally and 0.06 m laterally. This is evidence of control connectivity, not a vehicle dynamics calibration.

## Observed limitations

Initial best-effort large-message subscribers lost most cloud samples and received no complete RGB image despite visible publishers. Reliable subscriptions passed immediately after transport tuning. The baseline checker therefore uses reliable subscriptions for clouds/images, matching the bridge publishers. Do not treat this short presence check as a frequency, latency, or best-effort throughput acceptance test.

The snapshot cloud has no per-point time field. FAST-LIO accuracy and deskew remain unvalidated. No artificial point times were added. The body is still an imported e2-derived surrogate, not measured e6 geometry.

Fortress control libraries were present but required `IGN_GAZEBO_SYSTEM_PLUGIN_PATH` to find the ROS plugin. The installed `ign_ros2_control` compatibility package resolves to a `gz_ros2_control` implementation with legacy aliases; use the validated image rather than inferring the simulator version from package names.

GPU rendering, rolling scans, calibration, cross-container DDS, long-duration load, reset behavior, measured e6 parameters, and real CAN are later gates. Full local logs are kept under ignored `artifacts/`; a small sanitized JSON summary is committed alongside this report.
