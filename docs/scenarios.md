# Repeatable dynamic simulation scenarios

The scenario runner operates only the isolated `agile-slam-next` Compose project. It resets the simulation between routes and fault cases, disables the mock on exit, and does not expose CAN or USB devices. It closes existing GUI services during cold resets; reopen them after testing if needed.

```powershell
python -m pip install -r scripts/requirements-scenes.txt
python scripts/validate_scenarios.py
python scripts/deploy.py build
python scripts/run_scenarios.py curves
python scripts/run_scenarios.py faults
python scripts/run_scenarios.py intersection-left
python scripts/run_scenarios.py intersection-right
python scripts/run_scenarios.py all --repeat 3
python scripts/deploy.py up --gui
```

The runner checks each selected destination footprint against occupied/unknown map cells before resetting services. This uses Pillow from the existing scene-tool requirements and verifies pose placement, not path feasibility.

The last example is an extended acceptance run, not a claim that all scenarios have passed. Inspect the actual manifests. Do not run two scenario runners against the same project at the same time.

## Reports

Each run writes `artifacts/scenarios/<UTC run ID>/manifest.json`, individual JSON reports, stdout/stderr logs and final disabled status. The manifest records git revision and dirty state, image ID, source/configuration and map/world SHA-256 hashes, suite, timestamps and pass/fail results. A failed command preserves its output and returns a failing exit code. Raw artifacts remain ignored by Git; concise reviewed evidence belongs in `docs/validation/`.

A route starts from a cold known pose and sends one goal at a time. Curves include consecutive offset goals and require command evidence in both steering directions. Intersection scenarios request a final heading of plus/minus 90 degrees. The evaluator checks Nav2 SUCCEEDED, wheel and ground-truth position error <=0.4 m, ground-truth yaw error <=0.35 rad, nonzero path/command observations, zero sampled static footprint overlaps and fresh wheel feedback at rest after arrival. Ground truth is evaluator-only. Overlap sampling is not a Gazebo contact-event guarantee, and wheel-feedback rest is not a measured physical braking model.

## Moving fault injection

The ROS observer first requires ready/enabled mock, fresh truth and speed above 0.15 m/s while publishing a 0.3 m/s command. An atomic event file then tells the host runner when to inject the fault.

- `controller-stop`: stop vehicle-control while moving; require mock watchdog disable and fresh speed/truth at rest. Restart the controller while continuing to publish commands; require no automatic enable and a fresh three-second rest hold.
- `backend-pause`: pause the entire simulation backend while moving; require shared readiness fault/inhibit. Resume it; require fresh feedback, disabled mock and no automatic movement despite continuing commands.

Backend pause freezes Gazebo physics and its sensors. No physical stop observation is available during the pause. The report's elapsed wall time includes host orchestration and is not ECU timing or stopping distance. A full backend stop has the same observability limitation until a new simulation starts; the earlier at-rest stop test remains separate.

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
