# ADR 0002: Prefer Humble/Jammy while separating architecture from upgrades

Status: Preferred design; deployment refactoring remains unimplemented.
Date: 2026-10-15.
Supersedes the platform selection in ADR 0001.

## Context

The user prefers ROS 2 Humble and Ubuntu 22.04 and believes the vehicle PC already runs Ubuntu 22. The exact vehicle OS version is unverified. The current desktop uses WSL Ubuntu 22.04 and a working Humble/Fortress baseline. Changing ROS, OS, Gazebo, and the actuation chain together would increase migration and diagnostic work.

## Decision

Prefer Ubuntu 22.04 amd64, ROS 2 Humble, and its recommended Gazebo Fortress pairing. Reuse the existing simulation baseline while separating core, localization, vehicle-control, and simulation/hardware/replay backends. Use Docker Desktop on Windows/WSL2 and Docker Engine on the native Linux vehicle, with host-specific networking and device overlays.

Keep mandatory PACMod mock/control integration and the shared ROS contracts. Do not require an immediate vehicle OS upgrade or a new WSL distribution. Verify /etc/os-release, architecture, kernel, SDKs, and actual driver provenance during vehicle preflight. Preserve the supplied image as bootstrap/reference while reconstructing a traceable clean Humble base.

Humble/Harmonic is an isolated experiment only: non-default ros_gz packages can conflict with the Fortress packages and require plugin/API regression. Jazzy/Harmonic remains a later maintenance candidate, not a prerequisite for the current architecture.

## Lifecycle and gates

As verified on 2026-10-15, Humble and Fortress upstream support and Ubuntu 22.04 standard security maintenance end in May 2027. Ubuntu Pro/ESM does not automatically extend ROS/Gazebo or third-party SDK maintenance. Complete a migration/maintenance assessment by February 2027 and decide the post-May-2027 path before that deadline. This is a planning milestone, not an installed scheduled task.

First prioritize inventory/source contracts, backend separation, PACMod command/report tests, and existing motion regression. Rendering, rolling-scan, LIO, calibration, and hardware validation retain their own acceptance gates. A container process being alive is not readiness or actuation authorization.

## References

- https://github.com/ros-infrastructure/rep/blob/master/rep-2000.rst
- https://gazebosim.org/docs/latest/ros_installation/
- https://gazebosim.org/docs/latest/releases/
- https://ubuntu.com/about/release-cycle

Implementation details: [updated target plan](../plans/target_architecture_plan.md).
