# Scene catalog

Research date: 2026-10-14. External scenes below have been inspected as candidates; they have not been imported or runtime-validated in this repository.

| Candidate | Use | Compatibility and import notes |
|---|---|---|
| [Gazebo Fortress examples](https://github.com/gazebosim/gz-sim/tree/ign-gazebo6/examples/worlds) | Small geometry, sensor, and physics experiments | Use the `ign-gazebo6` branch rather than current Harmonic/Jetty plugin names. Prefer standalone examples first. |
| [TurtleBot4 humble worlds](https://github.com/turtlebot/turtlebot4_simulator/tree/humble/turtlebot4_ignition_bringup/worlds) | Warehouse, depot, and maze navigation | The [official manual](https://turtlebot.github.io/turtlebot4-user-manual/software/turtlebot4_simulator.html) pairs Humble with Fortress. Reuse scene geometry, not differential-drive controller or robot footprint parameters. |
| [TurtleBot4 warehouse](https://github.com/turtlebot/turtlebot4_simulator/blob/humble/turtlebot4_ignition_bringup/worlds/warehouse.sdf) | Shelves, barriers, and structured features | Uses OpenRobotics/MovAi/other Fuel assets. The bringup package declares Apache 2.0, but each referenced asset's license/version must be checked separately. Pre-cache assets and pin versions/hashes. |
| [AWS Small Warehouse](https://github.com/aws-robotics/aws-robomaker-small-warehouse-world/tree/ros2) | Rich warehouse assets | Its original README launches Classic `gazebo`; convert plugins/launch/resource URIs for Fortress. The repository is archived and unmaintained. The historical ros2 branch retains its license; record source/asset licenses rather than assuming live support. |
| Original golf-cart tracks | Outdoor loops and regression | Already available locally, but source-specific mesh licensing, collision geometry, and vertical SLAM features need review before publication/reuse. |

## Current local scene

`config/scenarios/navigation.json` generates `navigation.sdf`, its occupancy map, and a scene inventory. It uses primitive geometry only and does not download online assets.

The initial map is 40 x 24 m at 0.1 m/cell, with perimeter walls, a central 2 x 2 x 2 m box at [8,0], and two off-axis landmarks. The map and scene are generated together with `python scripts/generate_scene.py`; `--check` verifies they have not diverged.

## Import gate

For a future external world, record the upstream commit, model owner/version, checksums, licenses, simulator/SDF version, resource paths, download/cache steps, collision meshes, clearances, and measured rendering load. Preserve a small offline scene for CI and first-line debugging.
