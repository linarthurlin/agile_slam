# Small City Simulation Profile

The selected outdoor scene is `small_city` from leonhartyao/gazebo_models_worlds_collection. Its Classic world is converted locally for ROS 2 Humble / Gazebo Fortress. Missing model dependencies are fetched from the official `osrf/gazebo_models` repository. Exact source revisions are recorded in `config/scenes/small_city_sources.json`.

## Prepare and run

Run from the repository root in PowerShell:

```powershell
python -m pip install -r scripts/requirements-scenes.txt
python scripts/prepare_small_city.py
python scripts/convert_small_city.py
python scripts/prepare_base.py
python scripts/deploy.py build
python scripts/deploy.py up
```

Assets, adapted worlds, and maps remain in the ignored `assets/small_city/` cache and are mounted read-only. Downloads are required during preparation only. Preserve upstream licenses with the local asset cache; the collection declares GPL-3.0 and aggregates assets from other authors. Review individual asset terms before redistributing any downloaded assets.

The curve route starts at body pose (0,0,0) and runs three consecutive goals at (12,1), (28,-1), and (36,0). Intersection fixtures start at body pose (30,0,0). Static parked vehicles are part of the scene. See [Nav2 simulation baseline](navigation.md) and [repeatable scenarios](scenarios.md).

## Conversion

The converter adds Fortress systems, converts nine Classic road strips to static visuals, resolves material/image paths, and retains the source world. The runtime cache contains 36 model directories. Large meshes are not built into the application image or checked into this repository.

The initial occupancy map is generated from road corridors and conservative collision footprints at 0.2 m resolution. Off-road space is occupied. It is a navigation aid, not a map learned by SLAM or a complete model of overhangs and terrain.

## Rendering

Software Ogre2 remains the default. The WSL2 NVIDIA GPU profile passed its renderer preflight and sensor startup checks. With GUI enabled, the GPU-accelerated sensor server runs headless under Xvfb and a separate software-rendered Gazebo GUI client attaches to the same world; RViz runs in its own container. This split was accepted for the three-goal curve route on 2026-10-31. It is specific to the tested WSL2 / WSLg setup and does not establish real-time performance. Closing the Gazebo GUI exits the attached server; restart the full runtime before continuing.

See the [current runtime acceptance report](validation/simulation-runtime-2026-10-31.md) for image and route details. Intersection navigation, dynamic fault injection, and long-duration operation still need acceptance on the split topology.
