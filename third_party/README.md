# Third-party notices

The GEM description and simulator files are adapted from the local `golf_cart_sim-main` snapshot, whose README identifies AutonomousVehicleLaboratory/golf_cart_sim and UIUC-Robotics/gem_simulator as upstream sources.

- https://github.com/AutonomousVehicleLaboratory/golf_cart_sim
- https://github.com/UIUC-Robotics/gem_simulator

Original package license files and author metadata are retained. `source_manifest.json` records the SHA256 of every source snapshot file, plus the imported subset. No upstream commit is claimed because the supplied snapshot has no Git metadata. Racetrack assets and unrelated real-vehicle packages are not imported into the baseline.

The source repository does not publish the supplied Docker image, hardware photographs, CAN recordings, calibration data, or private machine configuration.

## Optional city assets

The small_city profile fetches pinned revisions of [gazebo_models_worlds_collection](https://github.com/leonhartyao/gazebo_models_worlds_collection) and [osrf/gazebo_models](https://github.com/osrf/gazebo_models). The collection declares GPL-3.0 and aggregates multiple sources. Assets and locally adapted derivatives remain in an ignored cache, with original checkouts, root notices, source hashes, and provenance. They are not redistributed as project-owned assets. Individual model terms still apply. See [city setup](../docs/small_city.md).

## Ogre renderer compatibility patch

The Docker build fetches Ubuntu's Ogre Next 2.2.5 source package, verifies the source hashes in `ogre_next.json`, applies the distribution patches and the local NV_copy_image patch, and builds only the matching GL3Plus renderer for installation. Upstream core binaries remain installed. The upstream [MIT notice](licenses/ogre-next-COPYING.txt) is retained in this repository. Ogre's package copyright is retained in the image at `/opt/agile_slam_metadata/renderer-copyright`; plugin and patch hashes are recorded beside it. See [Ogre Next](https://github.com/OGRECave/ogre-next) and the [Ubuntu source archive](https://archive.ubuntu.com/ubuntu/pool/universe/o/ogre-next/). This does not complete the provenance of the inherited application base or pin every apt dependency.
