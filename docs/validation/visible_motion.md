# Visible low-speed motion test

Date: 2026-10-15 (America/Los_Angeles). Scene: small_city, software Ogre2. Both Gazebo and RViz clients remained open during the tests. Gazebo followed gem using its native /gui/follow and /gui/follow/offset services. The motion RViz configuration follows base_footprint while retaining map as the fixed frame.

The simulator and both clients were initially stopped. They were restarted for a fresh initial pose. Sequential Nav2 goals at (3,0) and (8,0) completed successfully with a 0.6 m/s configured speed cap. Independent truth rear-axle errors were 0.336 m and 0.331 m; wall durations were 24.2 s and 31.4 s. The evaluator observed no overlap with the conservative static collision hulls.

Captured Linux client windows show the cart and surrounding street in Gazebo, and the vehicle model, map, live cloud, costmap, and front camera in RViz. The second-segment captures were taken while the goal was active. Screenshot files remain local under artifacts/visible_motion_*; they are not committed as external city assets.

A concurrent 15-second sensor check passed: LiDAR 10 Hz, IMU 50 Hz, and delivered RGB 26.03 Hz in acquisition time, with valid image payload and no backward timestamps. Estimated RTF was 0.315, so acquisition-time rates must not be confused with wall-time throughput. This is a short delivery check, not proof of loss-free sustained operation.

A subsequent 10-second rest check observed 89 wheel-odometry samples and 152 truth samples. Maximum wheel speed was approximately 1e-18 m/s and truth displacement was zero. This validates remaining at rest after arrival, not physical stopping distance.

Known limitations remain: inherited GEM e2 geometry, known-start map alignment, snapshot LiDAR, conservative collision projection, incomplete city materials, and software-rendering performance. Visible magenta terrain/material regions remain a rendering issue; they are not treated as sensor-calibration acceptance. Turning, junctions, full calibration, SLAM, and PACMod mock are separate gates.

## Repeat

Start the city server, then open the tracking view:

```powershell
wsl -d Ubuntu-22.04 -- bash /mnt/d/UCSD/Lectures/AVL/Agile_SLAM/scripts/small_city.sh
wsl -d Ubuntu-22.04 -- bash /mnt/d/UCSD/Lectures/AVL/Agile_SLAM/scripts/gui.sh motion
```

After the city is visible, enable Gazebo follow:

```powershell
docker exec agile-slam-gazebo /agile_slam_entrypoint.sh ign service -s /gui/follow --reqtype ignition.msgs.StringMsg --reptype ignition.msgs.Boolean --timeout 3000 --req 'data: "gem"'
docker exec agile-slam-gazebo /agile_slam_entrypoint.sh ign service -s /gui/follow/offset --reqtype ignition.msgs.Vector3d --reptype ignition.msgs.Boolean --timeout 3000 --req 'x: -9, y: -9, z: 7'
```

Use the navigation checker from docs/small_city.md, one goal at a time. The post-arrival rest helper runs through the ROS entrypoint after copying scripts/check_motion_stop.py into the sim container. scripts/capture_x11.py captures exactly one mapped Linux client window by its current title; xwininfo -root -tree lists titles. WSLg root-window capture is unsupported in this setup, so the helper captures the individual client window.

Machine-readable evidence: [results](visible_motion_results.json).
