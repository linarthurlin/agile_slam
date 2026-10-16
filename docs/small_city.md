# Small-city simulation profile

Current deployment: use [runtime operations](runtime.md) and root `compose.yaml`. Legacy launch/overlay commands below describe the historical baseline and are retired; asset preparation and historical evidence remain applicable.

The selected scene comes from leonhartyao/gazebo_models_worlds_collection. Its Classic world is converted locally for Humble / Fortress. Missing model dependencies are fetched from the official osrf/gazebo_models repository. Exact revisions are pinned in config/scenes/small_city_sources.json.

## Prepare

Run from the repository root with Python 3 and Git:

```powershell
python -m pip install -r scripts/requirements-scenes.txt
python scripts/prepare_small_city.py
python scripts/convert_small_city.py
docker compose build
wsl -d Ubuntu-22.04 -- bash /mnt/d/UCSD/Lectures/AVL/Agile_SLAM/scripts/small_city.sh
```

Assets, adapted worlds, and maps stay in the ignored assets/small_city cache and are mounted read-only. Downloads are required only during preparation. Keep upstream source checkouts and license notices with that cache. Project code does not relicense upstream assets; the collection declares GPL-3.0 and aggregates other authors' models. Review individual asset terms before redistribution.

## Adaptation

The converter adds Fortress systems, converts nine Classic road strips to static visuals, resolves material/image paths, and retains the original source world. The runtime cache contains 36 model directories. Large meshes are not baked into the image or checked into this repository.

The initial occupancy map is generated from road corridors and 198 conservative collision footprints, with a 0.2 m resolution over [-55,130] x [-60,60] m. Off-road space is occupied. Mesh transforms and COLLADA unit scale are applied; obstacle triangles are clipped to the 0.15–2.5 m vehicle-relevant height band before projecting convex hulls. This is a conservative navigation aid, not a map learned by SLAM or a complete representation of overhangs/terrain.

The vehicle starts at (0,0) on the main east-west street. First reference goals are (3,0), then (8,0), then (16,0), each from a fresh simulator start. Parked vehicles are part of the static city. Use the navigation RViz configuration.

```powershell
docker compose exec -T sim /agile_slam_entrypoint.sh python3 /opt/agile_slam_ws/src/agile_navigation/scripts/check_sensors.py
docker compose exec -T sim /agile_slam_entrypoint.sh python3 /opt/agile_slam_ws/src/agile_navigation/scripts/check_navigation.py --ros-args -p scene_file:=/opt/agile_assets/maps/small_city_scene.json -p goal_x:=3.0
wsl -d Ubuntu-22.04 -- bash /mnt/d/UCSD/Lectures/AVL/Agile_SLAM/scripts/gui.sh navigation
```

Do not run manual commands and Nav2 goals concurrently. Existing GUI clients must be closed before recreating the server.

## Rendering

Software Ogre2 is the default. WSLg D3D12 can expose the NVIDIA RTX 4060 to OpenGL, but this does not establish Fortress sensor-renderer compatibility. The experimental GPU override is retained for investigation; it is not an accepted runtime profile. Ogre2 encountered an unimplemented texture-copy operation through D3D12, and Ogre1 did not complete sensor initialization in the tested configuration. Do not interpret these startup failures as user-triggered GUI closure.

## Remaining gates

See the Traditional Chinese simulation-first plan and the English validation report. Known-start map alignment and the inherited GEM e2 geometry remain explicit limitations; full e6 sensors, PACMod mock, calibration, and LIO require separate implementation and validation.

## Action and bag smoke checks

Copy the host-side helpers into the running container:

```powershell
docker cp scripts/check_nav2_actions.py agile-slam-sim-1:/tmp/check_nav2_actions.py
docker compose exec -T sim /agile_slam_entrypoint.sh python3 /tmp/check_nav2_actions.py
docker cp scripts/bag_smoke.sh agile-slam-sim-1:/tmp/bag_smoke.sh
docker compose exec -T sim /agile_slam_entrypoint.sh bash /tmp/bag_smoke.sh record /artifacts/bags/city_run_02
docker compose exec -T sim /agile_slam_entrypoint.sh bash /tmp/bag_smoke.sh replay /artifacts/bags/city_run_02
```

The action checker briefly drives toward (30,0), cancels, then requests an occupied off-road goal. Run with a clear forward road and no other command producer. Existing bag directories are preserved. Playback uses domain 43 and the recorded clock; it does not send recorded commands to domain-42 controllers. The sensor checker observes 15 seconds and does not establish whole-bag equality or static TF late-join correctness.

For vehicle-following GUI motion tests, use `scripts/gui.sh motion`. See [visible motion validation](validation/visible_motion.md).
