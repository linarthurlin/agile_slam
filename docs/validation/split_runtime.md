# Initial split-runtime validation

Date: 2026-10-15. Platform: Docker Desktop / WSL2 Ubuntu 22.04, Humble / Fortress, amd64, software rendering. See [machine-readable evidence](split_runtime_results.json) and [operation](../runtime.md).

## Results

- Source/configuration checks and 28 unit tests passed.
- All five ROS packages built in the inherited bootstrap image.
- Cross-container sensor stream smoke check passed before the final navigation-only change. Sustained rate/loss/latency testing remains open.
- Cold-start Nav2 readiness succeeded in two final starts, including a start with both GUI clients.
- Sequential goals at x=3, 8 and 16 metres returned SUCCEEDED. Ground-truth rear-axle errors were 0.313, 0.319 and 0.321 metres. This is one sequential route, not three independent repeatability trials.
- The 8/16 metre evaluations used the small_city obstacle manifest and observed zero footprint-overlap samples. The initial headless 3 metre check used the default manifest; its collision result is not accepted for small_city. A fresh GUI-enabled 3 metre run used the correct small_city manifest, succeeded with 0.320 metre truth error and zero overlap samples.
- All 13 PACMod integration checks passed: exclusive mock actuation, no direct bypass, disabled rest, explicit enable, closed-loop movement, original-command expiry, override stop, no auto-enable after override clear, fault stop, no auto-enable after fault clear, invalid setpoint stop, invalid report inhibition and final disabled rest.
- Stopping vehicle-control at rest caused mock timeout/disable. Restarting it did not enable the mock. This process test does not establish a moving-process-loss braking distance.
- Stopping backend-sim at rest left shared services running and latched readiness fault/control inhibit. A full cold restart recovered the simulation.
- Gazebo rendered small_city and the vehicle; RViz displayed vehicle, point cloud, camera, map and costmap. Restarting RViz preserved the core PID and ready status. Some inherited scene materials remain magenta/missing and are not accepted for photometric camera testing.

- Nav2 cancellation returned CANCELED with a zero final command; an occupied goal returned ABORTED with no nonzero command. This checks action output, not physical braking distance.

## Fixes discovered during validation

The renamed simulation actuator adapter initially missed its legacy parameter namespace; launch now passes the resolved parameter dictionary and common wheel diameter. One cold boot encountered planner configuration failure during concurrent map startup; map lifecycle is now separate and Nav2 starts after map readiness. Two final starts passed, which is useful evidence but not a long-run stability claim.

Near the destination, repeated Dubins replanning could abort navigation even though the vehicle was close to its goal. The new single-goal tree retains an existing path inside one metre; FollowPath still determines success. No goal-checker or evaluator acceptance threshold was relaxed. Active goal replacement remains unaccepted.

Windows GUI startup also exposed backslash handling by wslpath; the wrapper now passes a forward-slash Windows path.

## Remaining gates

M0–M2 have an initial working implementation, not complete milestone acceptance. Moving controller/backend failure, simulated pause/reset, feedback delay/dropout, all gear transitions in live ROS, active goal preemption, NavigateThroughPoses, left/right turns, intersections, yaw error, repeated fixed-start routes, collision events, long-run DDS performance and dynamic bag/replay still require acceptance. Unit coverage does not substitute for these integration tests.

The vehicle geometry, steering map and plant are provisional e2 values. The PACMod mock validates ROS control contracts only. Real CAN/ECU, firmware, measured actuator response and actual hardware configuration remain unverified. LIO, rolling-scan timing, sensor calibration and hardware deployment are subsequent work.
