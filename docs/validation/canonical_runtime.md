# Canonical runtime and transport regression

Date: 2026-10-16. Ubuntu 22.04 / Humble / Fortress on Docker Desktop / WSL2, amd64, software rendering.

## Docker consolidation

The active image was preserved and retagged as `agile_slam:humble`. The retired `humble-baseline` image and both old deployment sets were removed. Unrelated images and the `agile_control_ros2` build base were preserved. Root `compose.yaml` is the sole active definition; legacy overlays and `deploy/compose.next.yaml` remain recoverable in Git history.

Project: `agile-slam`. Explicit container names: `agile-slam-core`, `agile-slam-localization`, `agile-slam-vehicle-control`, `agile-slam-simulator`, `agile-slam-gazebo`, `agile-slam-rviz`. The last two are optional GUI services. Both shell entrypoints delegate to `scripts/deploy.py`.

## Transport investigation

Independent Gazebo Transport statistics were added to navigation trials, with host reception times, source simulation time, source iteration counts, IP counters and timestamped runtime logs. These help distinguish a ROS delivery gap from a complete world-update stall; they are not deterministic real-time measurements.

A pre-change right turn passed. A subsequent full left approach failed early: ROS cloud age exceeded 2.05 s while clock and valid PACMod reports remained fresh. Independent world statistics continued, with no gap above 0.484 s. The same trial also logged a Nav2 action acknowledgment timeout before readiness inhibition. Thus this failure was not a complete Gazebo freeze, and a single root cause for all historical stalls is not established.

The core interface MTU was 1500 bytes, but CycloneDDS allowed 65500-byte messages and 4000-byte fragments. A cumulative kernel snapshot recorded ReasmReqds=656404, ReasmOKs=15839, ReasmFails=2 and ReasmTimeout=1. This shows actual IP fragmentation/reassembly failures, although it is not a per-route causal trace.

The desktop DDS profile now uses MaxMessageSize=1400B and FragmentSize=1280B. Primary sensor schemas/rates, vehicle geometry, goal tolerances and watchdog thresholds are unchanged. No host sysctl was modified. CycloneDDS documents limiting datagrams below MTU to avoid IP fragmentation; ROS 2 documents how fragment reassembly limits can disrupt large-message delivery. [CycloneDDS configuration](https://cyclonedds.io/docs/cyclonedds/latest/config/config_file_reference.html), [ROS 2 DDS tuning](https://docs.ros.org/en/humble/How-To-Guides/DDS-tuning.html).

Acceptance is determined by the recorded post-change runs. Passing selected trials supports this correction but does not prove every historical stall is resolved. Independent source statistics, ROS freshness, transport counters and long-duration tests remain necessary for broader stability claims.

## Recorded navigation outcomes

| Desktop DDS profile | Trial | Result | Truth position / yaw error |
| --- | --- | --- | --- |
| 65500B / 4000B | Right turn, start x=30 | Passed | 0.220 m / 0.001 rad |
| 65500B / 4000B | Full left approach, start x=0 | Failed early; ROS cloud stale while world statistics progressed | Not accepted |
| 1400B / 1280B | Full left approach, start x=0 | Passed, fresh rest, zero overlap samples | 0.351 m / 0.083 rad |
| 1400B / 1280B | Repeated right-turn suite, first trial | CANCELED by freshness fault | 0.300 m / 0.002 rad; not accepted |

The repeated-right suite requested two cold-start trials but stopped on its first failure; the second trial was not executed. The corrected full left approach ran for 245.5 wall seconds. During its independent monitoring window, both core and backend IP fragmentation/reassembly counters remained zero; maximum statistics reception gap was 0.875 s.

The corrected right-turn failure also had zero IP fragmentation/reassembly counters, but independent statistics had a 3.954 s gap with only 0.032 s / 32 iterations of source simulation progress. Mock control commands remained fresh. This shows an additional simulation-progress stall beyond the corrected IP-fragmentation problem. Host reception timing alone does not identify whether rendering, physics, an engine callback or scheduling caused that stall. The safety latch worked; the route remains unaccepted.

Next debugging should sample server thread CPU/wait states during the independent-statistics gap and correlate rendering/physics/ROS-control callbacks. Keep the same watchdog and goal thresholds; do not classify a close-to-goal canceled run as success.

## Final regression and deployment state

Both moving-fault cases passed after the transport change: controller loss disabled the mock, restart did not auto-enable it, and backend pause/resume retained the readiness latch. All seven checks in each case passed.

Gazebo and RViz were then opened in the canonical project. A 3 m goal and 30-second primary-sensor check ran concurrently: navigation passed with 0.309 m truth position error, sensor validation passed without warnings, and the simulated-time rate remained slower than wall time (RTF about 0.235 under software rendering and both clients). This is a short loaded regression, not a sustained-rate or real-time guarantee.

Final inventory verified exactly one application image (`agile_slam:humble`), one Agile SLAM Compose project (`agile-slam`) and all six explicitly named containers, with no numeric suffixes. The current image identity was preserved; unrelated images and the build base were untouched. Assets, bags and reports remain on the host. The simulation was left ready with the mock explicitly disabled.

Reviewed results, independent statistics, network counters and final inventory: [JSON evidence](canonical_runtime_results.json). The repeated right-turn failure is retained; the overall run collection is not all-green.
