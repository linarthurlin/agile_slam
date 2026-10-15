# Simulator port ledger

The supplied local snapshot is recorded by SHA256 in `third_party/source_manifest.json`. Active packages retain their upstream names during baseline reproduction.

- Import description meshes, Xacro, package metadata, and simulator control code.
- Exclude unrelated racetrack models, hardware files, and real-vehicle launch paths.
- Replace Harmonic control plugin names with Fortress `ign_ros2_control` names.
- Use a small locally defined world with no online asset downloads.
- Bridge canonical sensor topics with Fortress message names.
- Remove duplicate truth bridges and truth-derived operational TF.
- Keep command receipt time separate from control loop time; stop on clock reversal.
- Correct TF lookup direction and reject unavailable geometry instead of silently using a wheelbase fallback.
- Sequence controller startup after successful spawn; do not use fixed sleep delays.
- Use a dedicated bringup package and single build stage.

The vehicle geometry and snapshot LiDAR remain inherited approximations. Package presence in the supplied image does not establish hardware compatibility or algorithm correctness.
