# Roadmap

The first executable milestone is committed: a single-container Humble/Fortress simulator baseline with sensor presence and low-speed command-expiry checks. This is not a complete e6 digital twin or validated SLAM system.

Next gates, in order:

1. [Sustained transport and record/replay](https://github.com/linarthurlin/agile_slam/issues/1).
2. [FAST-LIO input contracts and rolling-scan validation](https://github.com/linarthurlin/agile_slam/issues/2).
3. [GEM e6 geometry and full sensor/PACMod profiles](https://github.com/linarthurlin/agile_slam/issues/3).

The default development workflow is local build and integration validation, followed by a reviewable commit with updated evidence. GitHub Actions runs source/configuration checks and regression tests; it does not build the private local base image or exercise GPU/CAN hardware.

Detailed implementation plans are maintained in Traditional Chinese under `docs/plans/`. All other project code, configuration, documentation, issue descriptions, and commit messages use English.
