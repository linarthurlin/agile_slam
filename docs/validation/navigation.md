# Nav2 and simple-scene validation

Date: 2026-10-14 (America/Los_Angeles).

The optional navigation profile builds four ROS packages and activates map_server, planner_server, controller_server, and bt_navigator. The known-start map, wheel odometry, rear-axle frame, virtual obstacle scan, and bounded Ackermann adapter are wired end to end.

## Checks

- Straight NavigateToPose goal [3,0] from a fresh start: succeeded in approximately 8.7 s; sampled truth endpoint error approximately 0.365 m.
- Static-box detour NavigateToPose goal [16,0] from a fresh start: succeeded in approximately 39.0 s; sampled truth endpoint error approximately 0.299 m and maximum lateral odometry displacement approximately 2.69 m.
- Independent evaluator samples ground-truth rear-axle pose and a conservative body footprint against the three scene boxes. No footprint overlap was sampled in the successful runs.
- A 15-second stationary sensor window validates frames, monotonic stamps, RGB encoding/payload size, CameraInfo dimensions, IMU gravity magnitude, valid cloud points, and virtual scan ranges.
- Nine unit/regression checks cover the existing watchdog/readiness fixes and independent vehicle geometry/integration cases.
- Scene SDF, occupancy map, and inventory are generated from one JSON specification and checked for consistency.

Machine-readable measurements: [navigation summary](navigation_summary.json).

## Performance observations

The final recorded stationary window had an estimated RTF of approximately 0.82. LiDAR and obstacle scan acquisition-stamp rates were 10 Hz; IMU was 50 Hz. RGB delivery was approximately 19 Hz in acquisition time and 15.5 Hz in wall time despite a nominal 30 Hz configuration, so the checker emits a rate warning. CameraInfo continued at approximately 30 Hz in acquisition time.

The nearest projected obstacle at the initial pose was approximately 5.591 m, consistent with the closest corner of the known off-axis landmark at approximately 5.590 m. This is a simple scene/projection sanity observation, not a calibration accuracy claim.

## Limits

- Results are short, low-speed integration checks, not statistical robustness or full collision/contact validation.
- Goal poses and errors refer to the rear-axle control frame. Action success, sampled odometry error, and truth error are reported separately; asynchronous samples can be slightly outside the configured goal-checker tolerance.
- Footprint-overlap sampling checks the specified boxes, not all contacts, obstacles, or continuous swept volume.
- The map is known in advance and initially aligned to odom. No AMCL/SLAM drift correction is running.
- Global planning uses static geometry. Dynamic/unknown-obstacle detouring is not validated.
- The LiDAR remains a snapshot with no per-point time. The virtual scan is a height-filtered projection, not another physical sensor.
- Ground truth is consumed only by the evaluator. The estimator reads joint feedback; Nav2 receives wheel odometry and the configured map.
- Repeated seeds, long-duration sensor loss/latency, recording/replay, cancel/unreachable goals, GPU rendering, and real PACMod remain future gates.
