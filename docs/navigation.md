# Nav2 Simulation Baseline

Nav2 is available in the simulation deployment only. It uses known-start map alignment and wheel-feedback odometry; it does not use SLAM, AMCL, or Gazebo truth as a localization input.

## Start

Prepare the runtime as described in [setup](setup.md), then run:

```powershell
python scripts/deploy.py up
python scripts/deploy.py check
```

To launch GUI visualization, stop and restart the full profile with `python scripts/deploy.py down` followed by `python scripts/deploy.py up --gui`. Gazebo GUI runs in the Gazebo container; RViz is an optional separate container.

## Data flow

```text
Gazebo joint states -> localization -> odometry / TF -> Nav2
Nav2 /cmd_vel -> vehicle-control -> pacmod2_msgs -> sim-bridge mock
    -> /simulation/actuation -> Gazebo joint controllers
```

PointCloud2 is height-filtered into a virtual LaserScan for the local obstacle layer. This is a projected 3-D simulation sensor, not a physical 2-D scanner. Sensor messages enter ROS through `sim-bridge`.

The rear-axle control frame is `base_rear_axle`, at x=-0.87 m relative to the inherited body ground frame. Wheel odometry integrates rear-wheel speed and steering joint feedback and publishes `odom -> base_footprint`. Robot state publisher owns fixed vehicle/sensor transforms. A static identity `map -> odom` represents known-start alignment only and does not correct drift. Ground truth is consumed by test evaluators only.

Nav2 uses Smac Hybrid-A* with DUBIN and a 4 m minimum turning radius, plus Regulated Pure Pursuit with 0.6 m/s desired speed. The controller bounds speed to [0,0.6] m/s and road-wheel angle to +/-0.48 rad. The footprint is an inherited-body estimate, not a measured e6 envelope.

## Checks and limits

Use the scripts in [scenario operations](scenarios.md) for repeatable routes and fault injection. The curve route has passed on the split container topology with Gazebo and RViz open; its run record is in the [current runtime acceptance report](validation/simulation-runtime-2026-10-31.md). Historical intersection and fault results in [navigation validation](validation/navigation.md) are from the previous topology and must be rerun before they count as acceptance for this split.

Dynamic-obstacle detouring, full perception-based mapping, accepted SLAM localization, measured e6 geometry, and vehicle controls remain future gates.
