# Small-city validation

Date: 2026-10-15. Host: Windows / WSL2, Docker Desktop, ROS 2 Humble / Gazebo Fortress. Accepted rendering profile: software Ogre2, headless server. GUI clients were opened after these measurements.

## Passed checks

- Pinned dependency closure: 36 models, 185 world includes, nine converted road strips, 198 conservative collision footprints. No unresolved model dependency remains in the fetch stage.
- Controllers activate and Nav2 lifecycle nodes become active. Startup takes approximately 30 seconds with the complete city; spawner switch and service deadlines accommodate initialization.
- Fifteen-second sensor sanity window: valid 800x600 RGB8 image payload, matching CameraInfo/optical frame, 30,000-point cloud with 26,283 finite points, expected LiDAR/IMU frames, gravity norm 9.8 m/s^2, no backward timestamps.
- Acquisition-time LiDAR / IMU rates: 10 / 50 Hz. Virtual obstacle scan contains 463 finite bins in the measured stationary window.
- Sequential forward Nav2 goals at (3,0), (8,0), (16,0): all passed the independent evaluator after tighter tolerances. Truth rear-axle errors: 0.326 / 0.347 / 0.358 m. Wall durations: 19.7 / 30.4 / 36.1 seconds. No sampled overlap with the conservative static collision hulls. These are one sequential route, not three independent fixed-start repetitions.
- Canceling an active goal returns CANCELED (5) and a zero Twist command. An occupied off-road goal at (0,10) returns ABORTED (6), with no nonzero Twist output for that goal. This tests command behavior, not physical braking distance.
- A stationary 19.48-second wall-time SQLite bag contains 8,841 messages / 286.4 MiB, including two tf_static messages and all sensor streams. Commands have zero messages because the vehicle was stationary during recording. Playback on ROS domain 43 passes the sensor sanity checker while the live simulation remains on domain 42. Recorded /clock is replayed; no additional player-generated clock is enabled.
- Fourteen source/geometry/control unit checks and generated simple-scene consistency checks pass.

Machine-readable evidence: [results](small_city_results.json). Large bags and mesh assets remain local in ignored storage.

## Failures discovered and corrected

The first goal reported Nav2 success but had 0.430 m truth error and failed the evaluator. Planner tolerance was reduced from 0.3 to 0.1 m and controller XY tolerance from 0.3 to 0.2 m. Acceptance now explicitly checks truth error <=0.4 m as well as wheel-odometry error. The unsuccessful attempt is retained locally.

Classic texture paths and COLLADA XML serialization required adaptation. WSLg NVIDIA D3D12 exposes accelerated OpenGL, but Ogre2 sensor rendering failed in a texture-copy operation; Ogre1 did not finish initialization in the tested setup. The GPU override remains experimental and is not the default.

## Remaining limitations

Estimated RTF is 0.381. Delivered RGB rate is 22.82 Hz in acquisition time / 8.78 Hz wall time, below the nominal 30 Hz. This is an integration pass with an explicit performance warning, not sustained loss/latency acceptance.

The city occupancy map is a conservative, road-constrained projection, not a learned map. Convex hulls can overestimate concave collision geometry. Ground-truth collision-hull sampling does not prove continuous collision freedom or validate all sidewalks, overhangs, slopes, and dynamic actors.

Known-start identity map->odom, wheel-only odometry, inherited GEM e2 geometry, and idealized snapshot LiDAR remain. No point firing times, LIO deskew, e6 dimensions, full sensor suite, calibration, PACMod firmware parity, repeated junction/turning tests, long-duration load test, or complete rosbag TF/clock/recovery regression is claimed.

GUI process check: both clients remained running after opening the city. RViz logged a Mesa indexed-map shader warning and an initial TF-cache drop; visual map rendering and extended GUI sensor delivery are not included in headless acceptance.
