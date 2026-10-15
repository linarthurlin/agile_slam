# Simulation-only Nav2 baseline

This optional profile tests static navigation with known starting alignment. It does not use SLAM, AMCL, PACMod, or ground-truth pose as an estimator input.

## Start

From the repository root in PowerShell:

```powershell
docker compose -f compose.yaml -f compose.navigation.yaml build
docker compose -f compose.yaml -f compose.navigation.yaml up -d
```

Switching profiles recreates the simulation and resets the starting pose. Close GUI clients before recreation. To return to the original baseline, use `docker compose up -d` without the navigation override.

Open GUI clients with the navigation view:

```powershell
wsl -d Ubuntu-22.04 -- bash /mnt/d/UCSD/Lectures/AVL/Agile_SLAM/scripts/gui.sh navigation
```

The view adds map, global path, local costmap, and the Nav2 Goal tool. Select a reachable goal with a forward-compatible heading. The low-speed baseline has no in-place rotate/back-up recovery and no reverse driving.

## Automated checks

With the vehicle stationary:

```powershell
docker compose exec sim /agile_slam_entrypoint.sh python3 /opt/agile_slam_ws/src/agile_navigation/scripts/check_sensors.py
```

Run one goal at a time:

```powershell
docker compose exec sim /agile_slam_entrypoint.sh python3 /opt/agile_slam_ws/src/agile_navigation/scripts/check_navigation.py
docker compose exec sim /agile_slam_entrypoint.sh python3 /opt/agile_slam_ws/src/agile_navigation/scripts/check_navigation.py --ros-args -p goal_x:=16.0
```

These goals are intended as separate fresh-start experiments; recreate the server between reference runs. Do not run manual command tests or another goal producer during an active Nav2 goal.

## Data flow

`joint_states -> wheel odometry -> Nav2 -> cmd_vel -> Twist-to-Ackermann -> ackermann_cmd -> simulated joints`.

`PointCloud2 -> reliable subscriber -> height filter -> virtual LaserScan -> local obstacle layer`.

The rear-axle control frame is `base_rear_axle`, at x=-0.87 m relative to the inherited body ground frame. Wheel odometry integrates rear-wheel speed and steering joint feedback and publishes `odom -> base_footprint`; robot_state_publisher owns the fixed `base_footprint -> base_rear_axle` edge. The Odometry message describes the rear-axle pose/twist consistently with that chain.

A static identity `map -> odom` encodes the known initial map alignment. It does not correct drift. Replace this single authority with AMCL/SLAM in a future localization profile. Ground truth is subscribed only by the test evaluator.

Nav2 uses Smac Hybrid-A* with DUBIN and a 4 m minimum turning radius, plus Regulated Pure Pursuit with 0.6 m/s desired speed. The adapter bounds speed to [0,0.6] m/s and road-wheel angle to +/-0.48 rad. The footprint is a conservative inherited-body rectangle, not a measured e6 envelope. The controller runs at 20 Hz; simulator command expiry remains 0.5 s.

The global map contains known static geometry. The local costmap uses a height-filtered projection of the 3-D LiDAR; it is not a physical 2-D scanner. Unknown/dynamic-obstacle detouring, full perception-based mapping, fault recovery, and real-vehicle controls remain later gates.

## Evidence and limits

See [navigation validation](validation/navigation.md), [scene research](scenes.md), and the [simulation-first plan](plans/simulation_first_plan.md). A passing action/status test is an integration result, not a hardware-accuracy or general collision-safety claim.
