# Roadmap

The executable baseline includes a single-container Humble/Fortress simulator, WSLg clients, sensor/control checks, and an optional known-start static Nav2 profile. It is not a measured e6 digital twin or a validated full SLAM system.

The immediate simulator-first sequence is documented in the [implementation plan](plans/simulation_first_plan.md): repeat simple motion and sensor geometry tests, validate goal cancellation/unreachable cases, record/replay fixed routes, then add localization/SLAM and larger worlds.

Existing workstreams:

1. [Sustained transport and record/replay](https://github.com/linarthurlin/agile_slam/issues/1).
2. [FAST-LIO input contracts and rolling-scan validation](https://github.com/linarthurlin/agile_slam/issues/2).
3. [GEM e6 geometry and full sensor/PACMod profiles](https://github.com/linarthurlin/agile_slam/issues/3).

See [navigation operation](navigation.md), [validation](validation/navigation.md), and [scene candidates](scenes.md). Known-start identity alignment is a temporary navigation test assumption; AMCL/SLAM must replace it before evaluating global localization.

The development workflow is local build/integration validation, followed by a reviewable commit with updated evidence. GitHub Actions checks source/configuration, kinematics/watchdog regressions, and generated scene/map consistency. It does not build the private local base image or exercise GPU/CAN hardware.

Detailed implementation plans use Traditional Chinese under `docs/plans/`. Other code, configuration, documentation, issue descriptions, and commit messages use English.

The proposed replacement platform targets a shared amd64 Jazzy/Harmonic runtime for Windows/WSL2 simulation and native Linux vehicle deployment. See the [architecture decision](architecture/0001-shared-runtime.md) and [target architecture plan](plans/target_architecture_plan.md). Migration is gated by PACMod/LIO compatibility and WSLg rendering validation.
