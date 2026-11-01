# E6 Canonical TF and Simulation Runtime Validation

Date: 2026-11-01 (America/Los_Angeles).

## Environment

- Windows 11, WSL2 Ubuntu 22.04, Docker Desktop, Docker Engine 29.5.2.
- ROS 2 Humble and Gazebo Fortress on amd64.
- Runtime image: `agile_slam:humble`, built from `agile_control_ros2:baseline-20261014`.
- The Compose runtime explicitly builds the Dockerfile `runtime` target. The Dev Container keeps the separate `dev` target.

## Build and Static Validation

- Full host unit suite: 71 tests passed.
- Docker colcon build: `gem_description`, `gem_gazebo`, `avl_bringup`, `agile_vehicle`, and `agile_navigation` all built.
- Runtime Xacro expansion produced 39 links, one root (`base_link`), and the canonical LiDAR and RealSense parent frames.
- Compose configuration validation passed for the split simulation services and their Gazebo health dependency.

## Split Compose Sensor Validation

The 15-second `check_sensors.py` window passed. Sensor timestamps were monotonic, and all required streams carried valid messages.

| Stream | Frame / payload | Acquisition rate | Wall rate |
| --- | --- | ---: | ---: |
| Velodyne point cloud | `velodyne_link`, 30,000 points, fields `x/y/z/intensity/ring` | 10.0 Hz | 3.85 Hz |
| IMU | `realsense_imu_frame`, acceleration magnitude 9.80 m/s² | 50.0 Hz | 19.42 Hz |
| RGB image | `realsense_color_optical_frame`, 800×600 `rgb8` | 29.08 Hz | 11.25 Hz |
| Camera information | `realsense_color_optical_frame`, 800×600 | 30.30 Hz | 11.80 Hz |
| Virtual obstacle scan | `base_link`, 440 finite ranges | 10.0 Hz | 3.85 Hz |

The estimated real-time factor in this window was 0.388. The 30,000-point cloud contained 26,165 finite points. `obstacle_scan` now removes non-finite points before matrix multiplication; the prior NumPy invalid-value warning did not recur.

## Navigation and PACMod2 Mock

- Readiness passed with fresh clock, cloud, odometry, vehicle reports, TF, and active Nav2.
- The simulation-only PACMod2 mock was explicitly enabled through `/pacmod/mock/enable` after readiness passed.
- A short `NavigateToPose` goal from `[-0.87, 0.0]` to `[1.0, 0.0]` succeeded (action status 4). Truth endpoint error was 0.298 m, yaw error 0.116 rad, no configured footprint overlap was sampled, and the vehicle met the consecutive-rest condition.
- The mock was explicitly disabled after the motion test. Final control diagnostics showed a live readiness lease, no lease fault, zero target speed, and `enabled=false`.

## Integrated Backend Smoke Test

The disposable all-in-one `backend_sim.launch.py` run started Gazebo, spawned the GEM, activated all seven simulated controllers, and passed the same sensor sanity checker in headless mode. Acquisition rates were 10 Hz LiDAR, 50 Hz IMU, and approximately 29–30 Hz RGB/CameraInfo. The estimated real-time factor was 0.305.

After switching back to split Compose, the Gazebo clock restarted. The still-running autonomy process correctly latched its clock-rewind guard; restarting autonomy and vehicle-control established a fresh readiness session and cleared the stale lease state. The final split stack passed the readiness check and remained with the PACMod2 mock disabled.

## Limits

- Sensor rates in simulated acquisition time match their configured rates, while wall-time delivery is reduced by RTF values of approximately 0.31–0.39 in these runs.
- The nominal E6 sensor mounts still derive from E2 geometry and are simulation-only. They are not calibration evidence for vehicle mode.
- The VLP-16 model publishes a snapshot cloud without per-point timestamps; rolling-scan timing, deskew, LIO accuracy, and hardware data-format equivalence remain unvalidated.
- This validation did not use Gazebo/RViz GUI windows, physical sensors, CAN, or the real GEM e6.
