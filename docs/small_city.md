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

The vehicle starts at (0,0) on the main east-west street. The initial navigation goals are (3,0), (8,0), and (16,0), each from a fresh simulator start. Static parked vehicles are part of the scene. See [Nav2 simulation baseline](navigation.md) and [repeatable scenarios](scenarios.md).

## Conversion

The converter adds Fortress systems, converts nine Classic road strips to static visuals, resolves material/image paths, and retains the source world. The runtime cache contains 36 model directories. Large meshes are not built into the application image or checked into this repository.

The initial occupancy map is generated from road corridors and conservative collision footprints at 0.2 m resolution. Off-road space is occupied. It is a navigation aid, not a map learned by SLAM or a complete model of overhangs and terrain.

## Rendering

Software Ogre2 remains the default. WSLg D3D12 can expose the NVIDIA GPU to OpenGL, but this alone does not establish Fortress sensor-renderer compatibility. The GPU overlay remains experimental and should only be used after its capability preflight. Closing the integrated Gazebo GUI exits the Gazebo server; restart the full runtime before continuing.

Historical scene and rendering validation predates the current split runtime. Rerun it after the new Compose topology is built.
