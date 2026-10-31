# Repeatable dynamic simulation scenarios

The scenario runner operates only the isolated `agile-slam` Compose project using `compose.yaml` plus `compose.sim.yaml`. It resets the full simulation between routes and fault cases, disables the mock on exit, and does not expose CAN or USB devices. A cold reset also closes the Gazebo GUI; restart with `--gui` when a visible run is needed.

```powershell
python -m pip install -r scripts/requirements-scenes.txt
python scripts/validate_scenarios.py
python scripts/deploy.py build
python scripts/run_scenarios.py curves
python scripts/run_scenarios.py curves --gui --rendering gpu
python scripts/run_scenarios.py faults
python scripts/run_scenarios.py intersection-left
python scripts/run_scenarios.py intersection-right
python scripts/run_scenarios.py all --repeat 3
python scripts/deploy.py up --gui
```

The runner checks each selected destination footprint against occupied/unknown map cells before resetting services. This uses Pillow from the existing scene-tool requirements and verifies pose placement, not path feasibility.

The extended `all --repeat 3` example is not a claim that all scenarios have passed. The curves GUI/GPU run is accepted for the current split runtime; inspect [its report](validation/simulation-runtime-2026-10-31.md) and the actual manifest. Intersection and fault suites still need split-runtime acceptance. Do not run two scenario runners against the same project at the same time.

## Reports

Each run writes `artifacts/scenarios/<UTC run ID>/manifest.json`, individual JSON reports, stdout/stderr logs and final disabled status. The manifest records git revision and dirty state, image ID, source/configuration and map/world SHA-256 hashes, suite, timestamps and pass/fail results. A failed command preserves its output and returns a failing exit code. Raw artifacts remain ignored by Git; concise reviewed evidence belongs in `docs/validation/`.

A route starts from a cold known pose and sends one goal at a time. Curves include consecutive offset goals and require command evidence in both steering directions. Intersection scenarios request a final heading of plus/minus 90 degrees. The evaluator checks Nav2 SUCCEEDED, wheel and ground-truth position error <=0.4 m, ground-truth yaw error <=0.35 rad, nonzero path/command observations, zero sampled static footprint overlaps and fresh wheel feedback at rest after arrival. Ground truth is evaluator-only. Overlap sampling is not a Gazebo contact-event guarantee, and wheel-feedback rest is not a measured physical braking model.

## Moving fault injection

The ROS observer first requires ready/enabled mock, fresh truth and speed above 0.15 m/s while publishing a 0.3 m/s command. An atomic event file then tells the host runner when to inject the fault.

- `controller-stop`: stop vehicle-control while moving; require mock watchdog disable and fresh speed/truth at rest. Restart the controller while continuing to publish commands; require no automatic enable and a fresh three-second rest hold.
- `backend-pause`: pause the entire simulation backend while moving; require shared readiness fault/inhibit. Resume it; require fresh feedback, disabled mock and no automatic movement despite continuing commands.

Backend pause freezes the Gazebo server and its sensors while autonomy and bridge processes remain alive. No physical stop observation is available during the pause. The report's elapsed wall time includes host orchestration and is not ECU timing or stopping distance. A full Gazebo stop has the same observability limitation until a new simulation starts; the earlier at-rest stop test remains separate.

The observer uses monotonic receipt times and fresh samples. Recovery clears no readiness latch automatically. After a backend-pause scenario, cold-start the stack before normal navigation.

## Remaining validation

Actual contact events, dynamic obstacles, delayed/dropped reports, simulated time rewind, active goal replacement, NavigateThroughPoses, long-duration transport and dynamic bag/replay are separate gates. Existing mock gains, steering ratio and geometry remain provisional.

The current navigation policy retains a path while Nav2's `IsPathValid` check succeeds and replans on invalidation. This replaces the initial one-metre approach rule, which failed on a consecutive offset-to-centre goal. Initial planning remains mandatory, and FollowPath retains local collision checking. Active goal replacement remains a separate acceptance gate.

Freshness diagnostics are retained in `/system/readiness.last_fault` and `/pacmod/mock/status.last_watchdog_fault`, including monotonic stream/command ages. Scenario reports include these fields; restoring a stream does not erase the failure snapshot or clear a readiness latch.

## Known-start fixtures

Curved routes and moving faults start at body pose (0, 0, 0). The default 90-degree intersection fixtures start at body pose (30, 0, 0), allowing turning acceptance without the full long approach. The runner passes identical `AGILE_SPAWN_X/Y/YAW` values to the simulation and localization services; wheel odometry starts at the rear axle transformed from that configured body pose. Ground truth remains evaluator-only.

Reproduce the currently failing long approach with:

```powershell
python scripts/run_scenarios.py intersection-left --start-x 0
```

Manifests record effective starts, including command-line overrides. A passing short fixture does not establish acceptance of the long route. After changing start coordinates, restart the entire stack; the runner performs this automatically. The known-start alignment is a simulation fixture, not a real localization solution.

To collect reviewed runs, including failed stress cases, use `python scripts/summarize_scenarios.py RUN_ID ... --output docs/validation/dynamic_scenarios_results.json`. This command summarizes evidence; its successful exit means the summary was written, not that its input trials passed. Inspect `all_runs_passed` and each run's `passed` field.

## Canonical Docker deployment (2026-10-16)

The simulation project combines `compose.yaml` and `compose.sim.yaml`; WSLg and GPU settings are optional overlays. Its five core containers have explicit `0025-` names. RViz is an optional sixth container; the optional Dev Container uses a separate `agile-slam-dev` project. The split topology GPU/GUI curves run passed on 2026-10-31; other suites remain pending as listed above.

Navigation trials also retain independent Gazebo Transport statistics (`*.gazebo.jsonl`, `*.gazebo.summary.json`) and timestamped runtime logs. These probes use `/world/small_city/stats` without the ROS bridge. Correlate their source iteration/simulation-time progression with ROS freshness faults before attributing a gap to physics, rendering or bridge/DDS transport. Collection timing also includes host scheduling and is not a real-time guarantee.


Navigation probes also retain `*.gazebo.process.jsonl`: read-only Linux thread CPU ticks, wait channels, scheduler counters and host pressure. The sampler discovers the server by its command line, runs at four samples per second, and exits with the statistics probe (maximum 450 seconds). It does not require extra container privileges or modify the server. Sampling adds overhead and does not establish real-time performance.

Analyze a completed capture with:

```powershell
python scripts/analyze_gazebo_process.py artifacts/scenarios/RUN_ID/1_right_intersection.gazebo.jsonl
```

The output correlates simulation-progress gaps with active threads. Wait channels and CPU activity alone do not identify a specific shader or prove causality. Native debugger captures are separate intrusive diagnostics and must not count as navigation acceptance.


Use `--gui` to run Gazebo with its GUI and make RViz available across each scenario's cold start, for example `python scripts/run_scenarios.py intersection-right --gui`. The Gazebo GUI and server share `0025-gazebo`; RViz remains separate. The manifest records GUI selection. GUI load is part of that trial; it must satisfy the same goal, freshness and stopping criteria as a headless run.

## Renderer and acceptance updates

Use `python scripts/run_scenarios.py all --gui --rendering gpu` for the WSL NVIDIA overlay. The default remains software; renderer choice is recorded in the manifest. The runner verifies actual body truth and wheel rear-axle pose/yaw before enabling the mock. Every goal has independent 120-second simulation and 360-second wall budgets. Arrival requires advancing fresh truth, fresh ready/enabled diagnostics and at least one consecutive second of fresh wheel rest, rather than a cumulative sample count.

The fault suite also includes `readiness-pause`: SIGSTOP only the uniquely matched readiness node while live commands continue, require lease inhibition and rest, resume the same PID and restart autonomy to clear any readiness data-loss latch, require new ready heartbeats without automatic movement, then explicitly disable/enable and require movement to resume. The observer runs in localization so it survives the autonomy restart. Host cleanup resumes a paused node even when the observer fails. This test checks publisher loss independently of simulator loss.

`python scripts/check_gpu_sensors.py` cold-starts camera-only, LiDAR-only and combined sensor configurations against the baseline wall. It retains renderer provenance, image samples, schema/range results and runtime logs. It does not enable actuation or validate sensor rate, rolling scans, depth cameras, MSAA or calibration accuracy.

New manifests also hash the actual runtime model/generated asset closure. The first GPU city regression retains this closure separately at `artifacts/gpu_runtime_assets.json`; map/world-only hashes would miss an adapted included terrain model.

GUI runs now require both live client containers and nontrivial Gazebo/RViz X11 windows before actuation and after each goal/fault. Window existence does not certify every pixel or continuous rendering performance.
