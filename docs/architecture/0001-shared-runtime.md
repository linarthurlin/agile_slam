# ADR 0001: Shared amd64 runtime with replaceable backends

Status: Proposed; feasibility gates required before migration.
Date: 2026-10-15.

## Context

The developer uses Windows/WSL2, while the GEM e6 uses a conventional x86_64 Linux PC. The existing Humble/Fortress container couples Gazebo, navigation, odometry, and GUI network lifetime. Hardware models and PACMod board/firmware/DBC remain unknown.

## Decision

Target Ubuntu 24.04, ROS 2 Jazzy, and Gazebo Harmonic. Retain the old baseline for regression. Build clean, pinned amd64 images from traceable public bases and sources. Validate PACMod, the selected LIO port, and WSLg sensor rendering before adopting this target.

Use Docker Desktop on the development host and Docker Engine on the native Linux vehicle. Share application images and ROS contracts; provide host-specific networking, graphics, time, hardware permissions, calibration, and tuning through deployment overlays.

Separate common core, localization, and vehicle-control services from simulation/hardware/replay backends. Group compatible ROS processes; split further only for SDK dependencies, hardware access, or independent lifecycle requirements. Make PACMod command/report control mandatory in the simulation profile before hardware actuation tests.

Use a private bridge network on the desktop and initially native Linux host networking for vehicle data-plane services. Do not depend on a simulator container network namespace or assume Docker Desktop host networking exposes SocketCAN.

Prefer the WSL Linux filesystem for the new development checkout and working datasets. Keep generated assets and bags outside source control. Use immutable release image digests and versioned configuration/calibration manifests. No new deployment command or image is implemented by this ADR.

## Consequences

The same amd64 application artifacts can run on both hosts, but this does not eliminate kernel/GPU/USB/CAN differences. Jazzy migration requires explicit source compatibility tests for legacy PACMod and LIO. Harmonic does not guarantee a fix for WSLg rendering. Simulation/replay and vehicle mode must be mutually exclusive; restart must not automatically re-enable actuation.

## References

- https://gazebosim.org/docs/latest/ros_installation/
- https://github.com/ros-infrastructure/rep/blob/master/rep-2000.rst
- https://autowarefoundation.github.io/openadkit/deployments/
- https://github.com/clearpathrobotics/clearpath_simulator
- https://docs.docker.com/engine/network/drivers/host/
- https://learn.microsoft.com/en-us/windows/wsl/filesystems

Detailed implementation sequence: [target architecture plan](../plans/target_architecture_plan.md).
