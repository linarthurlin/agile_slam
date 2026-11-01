# GEM e6 canonical sensor frame profile

This directory defines the canonical GEM e6 operational sensor frame contract shared by simulation and vehicle modes. The target `base_link` is the rear-axle center projected to the ground. Both modes use the same operational sensor frame IDs and parentage; the simulator may append connected physics-, visualization-, or explicitly marked legacy-sensor-only frames within the same TF tree.

The Gazebo model remains E2-derived for body geometry and vehicle dynamics, but its active simulated frames and runtime base-frame consumers have been migrated to the shared E6 operational graph. `simulation_nominal_transforms.yaml` records camera, IMU, chassis-origin, and VLP-16 seed transforms derived from the legacy model. They are simulation-only plumbing/geometry values, not E6 measurements, and are never eligible for vehicle mode. The legacy NavSat fixture is retained as `legacy_gnss_sim_link`; it does not represent an E6 antenna phase center or satisfy the GNSS frame contract. The hardware calibration registry remains pending until the actual vehicle and sensor mounts are measured.

## Files

- `sensor_inventory.csv` binds each logical sensor ID to its expected ROS topics and frame names. Fill hardware identifiers and connection details during the P0 vehicle inventory.
- `driver_matrix.yaml` records candidate ROS 2 driver families and the compatibility checks still required in the locked Humble environment.
- `sensors_calibration.yaml` defines the shared fixed-frame parentage and E6 hardware calibration gates. All physical transforms are pending measurement and must not be published as zero-valued hardware extrinsics.
- `simulation_nominal_transforms.yaml` records the E2-derived simulation seed values in the canonical E6 frame names. It must remain simulation-only.

Logical IDs, topics, frames, and parent frames follow `docs/plans/tf_system_integration_plan.md`. Unknown hardware data is marked `TBD`; do not replace it with values copied from the e2 simulator or the reference vehicle image.

## Status meanings

- `pending_inventory`: identify the physical unit, serial, firmware, and connection.
- `pending_compatibility_spike`: build and exercise the driver with the actual model and target ROS distribution.
- `pending_measurement`: obtain and review the physical mount transform.
- `validated`: evidence is recorded, including method, date, source data, and uncertainty.

The profile is not hardware-ready until required inventory, driver, clock, and extrinsic fields have passed their gates. In particular, AVT cameras share one measured mounting height; VLP-16 and GNSS remain children of `top_sensor_rig_link` but use their own independent transforms. `realsense_link` is the only RealSense mount frame owned by the vehicle description; the wrapper owns and publishes its internal stream and IMU frames.

## Commands

From the repository root, run the structural contract check:

```sh
python scripts/validate_e6_profile.py
```

Use `--require-ready` as the integration gate. It returns a failure while any required hardware, calibration, driver, clock, or bandwidth item remains pending. After the gate passes, generate a sensor-frame Xacro include at an explicit output path:

```sh
python scripts/validate_e6_profile.py --require-ready
python scripts/generate_e6_sensor_xacro.py --output /path/to/gem_e6_sensor_frames.generated.xacro
```

The hardware Xacro generator emits its calibration include only after the hardware readiness gates pass. The simulation URDF is not a hardware vehicle description and must not be launched in vehicle mode; a measured e6 body/vehicle description remains a separate required deliverable. Static source validation is required before runtime validation; the latter must be run in the explicitly selected ROS/Gazebo environment.
