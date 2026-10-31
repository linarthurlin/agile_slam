# Split Simulation Runtime Acceptance — 2026-10-31

## Environment

- Host: Windows 11, Docker Desktop Linux engine, WSL2 Ubuntu 22.04 (amd64).
- ROS / simulation: ROS 2 Humble, Gazebo Fortress, CycloneDDS.
- Branch: `feat/simulation-service-split`.
- Source revision at run start: `d5e53f9437d481c114864e866057d909a1647d0d`; the working tree contained the implementation changes described below.
- Runtime image: `agile_slam:humble`, `sha256:d3ae6a4782f0c2807d14d13f1e756c63610dda3c597b5cb770b73f1784b954a9`.
- Detailed local manifest: `artifacts/scenarios/20261031T215229848081Z/manifest.json` (artifact files are git-ignored).

## Implemented for this acceptance

- Replaced the Humble spawner CLI path with `spawn_sim_controllers.py`, which waits for controller-manager services and makes each controller load/configure/activate call once with an explicit response timeout. This avoids Humble's spawner CLI retry behavior that could time out a response after loading a controller, then issue a duplicate load.
- Added an environment override for the command timeout and set it to 1.5 seconds in the simulation Compose overlay. This is limited to the simulator to tolerate a measured WSL2 scheduling gap; the shared default remains 0.75 seconds outside the simulation profile.
- Added a WSL2 GPU + GUI process split: the accelerated sensor server runs headless under Xvfb, while a software-rendered Gazebo GUI client attaches to the same world. RViz remains a separate container. The normal software and headless paths remain unchanged.

## Checks

| Check | Result |
| --- | --- |
| Runtime image build including the controller startup helper | Passed |
| Python unit suite: `python -m unittest discover -s tests -v` | 52 passed |
| PACMod ROS mock runtime checks: `python scripts/deploy.py test` | 13 passed; final state intentionally inhibited |
| GPU renderer preflight and NVIDIA accelerated rendering | Passed |
| Live LiDAR bridge | Passed; ROS `PointCloud2` has 16 × 1875 points, 32-byte point step, and x/y/z/intensity/ring fields |
| Readiness after route cleanup | Passed; clock, point cloud, odometry, vehicle report, TF, and Nav2 active; mock disabled; no latched fault |
| Gazebo / RViz windows | Present before and after each route goal; both GUI containers remained running |

## Visible GPU curve route

Command:

```powershell
python scripts/run_scenarios.py curves --gui --rendering gpu
```

The scenario runner cold-started the split runtime for each curve goal, checked the GUI windows, and explicitly disabled the mock at cleanup. All three goals passed:

| Goal | Target (m) | Ground-truth position error (m) | Yaw error (rad) | Static footprint overlaps |
| --- | ---: | ---: | ---: | ---: |
| `left_offset` | (12, 1) | 0.3151 | 0.0968 | 0 |
| `right_offset` | (28, -1) | 0.3060 | 0.1511 | 0 |
| `return_center` | (36, 0) | 0.3203 | 0.1217 | 0 |

The route generated steering commands in both directions: 1,259 positive and 1,290 negative. Each goal ended with fresh wheel feedback at rest. The final readiness check passed; vehicle speed was effectively zero, PACMod mock was disabled, and there was no override, timeout, watchdog fault, or latched readiness fault.

The captured GUI checks establish that Gazebo and RViz windows were present during the run; the per-goal checks do not measure continuous frame rate. This acceptance is a WSL2 integration check, not a real-time performance claim.

## Scope limits and next acceptance gates

- The vehicle remains an e2-derived surrogate, and PACMod remains a ROS-level mock. No physical PACMod ECU, CAN path, e6 geometry, or vehicle hardware was tested.
- Only the three-goal curves route is accepted on the new split topology. Re-run intersection routes and moving fault injection on this topology before treating them as accepted.
- Extended transport, rosbag record/replay, sensor calibration, rolling-scan LiDAR timing, LIO, and UM982 serial integration remain separate work.
- GPU + GUI was validated on this specific WSL2 / WSLg setup. Other host graphics stacks need their own acceptance run.
