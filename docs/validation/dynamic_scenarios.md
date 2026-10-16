# Dynamic scenario validation

Date: 2026-10-15. Humble / Fortress on amd64 Docker Desktop / WSL2, software rendering. Operational procedure: [simulation scenarios](../scenarios.md). Reviewed measurements: [JSON evidence](dynamic_scenarios_results.json).

## Navigation change

The earlier one-metre approach rule failed when a consecutive goal returned from an offset to the road centre. The current single-goal tree computes an initial path, validates it at 1 Hz, and replans only after invalidation. This keeps a valid forward-only path instead of repeatedly asking Dubins planning for a new short manoeuvre near the target. FollowPath still determines success and checks local collision risk; initial planning failure or invalid-path replacement failure aborts. Active goal replacement and NavigateThroughPoses remain unaccepted.

Implementation references: Nav2 Humble [IsPathValid](https://github.com/ros-navigation/navigation2/blob/humble/nav2_behavior_tree/plugins/condition/is_path_valid_condition.cpp) and [ComputePathToPose](https://github.com/ros-navigation/navigation2/blob/humble/nav2_behavior_tree/plugins/action/compute_path_to_pose_action.cpp). The Humble timeout is taken from the typed navigator blackboard default; a literal duration port was rejected during development and is absent from the final tree.

## Evidence and limits

Only completed, passing run records establish acceptance. Each recorded route starts at a cold known pose, uses small_city's actual obstacle manifest, and evaluates truth independently of wheel odometry. Goal thresholds remain 0.4 m position and 0.35 rad yaw. Rest requires fresh wheel-feedback observations after the action result. Static footprint overlap is sampled; actual contact-event acceptance remains open.

Fault injection begins only after fresh measured speed exceeds 0.15 m/s. Controller-loss acceptance requires fresh feedback at rest, new controller status after restart and no automatic enable despite live incoming commands. Backend-pause acceptance requires readiness inhibit, fresh feedback after resumption and disabled rest hold. Paused physics cannot establish physical braking performance during the pause.

This is an initial dynamic acceptance pass, not repeatability or full M3 completion. Remaining gates include repeated fixed-start trials, dynamic obstacles/contact events, delayed/dropped reports, clock rewind, long-duration DDS performance, dynamic bag/replay, LIO and real PACMod hardware. Inherited image provenance and e2 surrogate limitations remain unchanged.

## Completed curve and fault runs

| Case | Truth position error | Truth yaw error | Result |
| --- | --- | --- | --- |
| Left offset, (12, 1, 0) | 0.309 m | 0.095 rad | SUCCEEDED, fresh rest, zero overlap samples |
| Right offset, (28, -1, 0) | 0.295 m | 0.148 rad | SUCCEEDED, fresh rest, zero overlap samples |
| Return centre, (36, 0, 0) | 0.317 m | 0.121 rad | SUCCEEDED, fresh rest, zero overlap samples |

These three goals ran consecutively after one cold start. The combined route exercised 972 positive and 850 negative yaw-rate command samples. One run was executed; `--repeat 3` remains a separate gate.

Moving controller-stop and backend-pause both passed all seven case-specific checks. Controller restart did not re-enable the mock despite continued incoming commands; the subsequent three-second truth drift was 0.00085 m. Backend resume preserved the readiness fault latch, disabled mock and rest hold. Reported wall times include orchestration and must not be interpreted as physical brake or ECU timing.

The first intersection pose at x=46 m overlapped occupied map cells once the full vehicle footprint and heading were considered. The corrected pose is x=44 m. A new preflight validates all configured destination footprints; a manual negative check confirmed rejection of the original pose. This is destination validation, not a proof of path feasibility.

## Freshness diagnostics

Readiness status now retains `last_fault`, per-stream monotonic receipt ages and report validity. The mock retains the command/joint/advancing-stamp ages that triggered its watchdog. Navigation and moving-fault reports include these diagnostics so a recovered stream cannot erase the original fault cause. Thresholds were not relaxed.

One corrected 90-degree left-turn trial reached approximately (44.12, 11.37) in ground truth, then readiness canceled the task during a transient data failure. It returned CANCELED, not SUCCEEDED, and did not pass the fresh-rest acceptance window. The pre-instrumentation record cannot identify which stream failed first. This remains a stability observation even if a later trial succeeds; repeated-trial acceptance is still required.

## Sensor workload audit

The inherited model instantiated an unbridged depth camera and secondary RGB camera at 30 Hz each. The split navigation profile now disables those two sensors through an explicit xacro argument, preserving the legacy default. Structural xacro comparison verified that primary RGB, LiDAR and IMU definitions are unchanged. A 15-second live sensor smoke check passed with no warnings: front image/camera info 800x600, IMU about 50 Hz and LiDAR about 10 Hz in message time. Software simulation remained slower than wall time (RTF about 0.44 in that window); this is not sustained performance acceptance.

The instrumented long left-turn failure identified simultaneous Gazebo-side staleness: cloud age 2.043 s, clock age 1.806 s and odometry age 1.889 s at readiness cancellation; the mock then recorded joint age 2.011 s while command age was only 0.018 s. This isolates the symptom to simulation data production/transport rather than command starvation, but does not yet identify a rendering, physics or transport root cause. No freshness threshold was loosened.

## Known-start intersection results

The isolated intersection fixture uses body start (30, 0, 0), with wheel odometry initialized to rear-axle pose (29.13, 0, 0) from the same configured geometry. This fixture does not consume truth measurements.

| Case | Truth position error | Truth yaw error | Result |
| --- | --- | --- | --- |
| Left 90 degrees to (44, 12) | 0.391 m | 0.168 rad | SUCCEEDED, fresh rest, zero overlap samples |
| Right 90 degrees to (44, -12) | 0.337 m | 0.003 rad | CANCELED by freshness fault; not accepted |

The left result is close to the 0.4 m acceptance threshold and requires repeated trials. The right case's position/yaw values were within thresholds, but its result and fresh-rest window failed; proximity alone does not pass a test.

Disabling the unbridged auxiliary cameras did not resolve the long-route stall. Both long left and isolated right failures retained Gazebo-derived clock/cloud/joint staleness while commands remained fresh. Passing the isolated left fixture therefore does not establish whole-scene stability. The long failure remains reproducible with `intersection-left --start-x 0`; isolated right is reproducible with `intersection-right`.

The next investigation should correlate independent Gazebo transport/statistics, ROS receipt times and backend CPU/thread activity during the gap, then isolate rendering, physics and bridge/DDS load. Primary sensor fidelity and existing freshness thresholds remain unchanged. This stall is an open implementation defect, not a completed performance gate.

Final-image moving-fault regression passed both cases again after adding shared spawn fixtures, the explicit sensor workload and retained diagnostics. Controller command age at watchdog trip was 0.766 s while joint age was 0.047 s, correctly identifying command loss. Its post-restart rest drift was 0.00239 m. The backend-pause case retained the readiness cause and remained disabled after fresh feedback resumed. These are separate from the unaccepted scene-stall routes.

The combined JSON deliberately has `all_runs_passed: false`: failed development/stress trials are retained beside accepted cases. It is evidence of the current boundary, not an all-green acceptance certificate.

Final default-origin GUI regression also passed on the final image: x=3 m navigation returned SUCCEEDED with 0.306 m truth position error, 0.039 rad yaw error, fresh wheel-feedback rest and zero sampled overlaps. Nav2 cancellation returned CANCELED with a zero final command; an occupied goal returned ABORTED with no nonzero commands. These action checks do not measure physical braking distance. Both GUI clients remain optional services; actuation was explicitly disabled after the checks.
