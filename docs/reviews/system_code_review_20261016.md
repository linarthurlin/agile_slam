# System and code review: rendering stalls and control readiness

Review date: 2026-10-16 (America/Los_Angeles). Reviewed commit: `053194a`. Scope: Compose, build provenance, simulator/sensor timing, readiness, PACMod mock/control, navigation acceptance and prior validation evidence. This is a correctness/architecture review, not a security audit. No runtime code or deployment configuration was changed.

## Executive assessment

The shared Humble/Fortress service architecture can be retained. The current desktop rendering backend is the main demonstrated bottleneck. Separate application defects can weaken fault handling or produce misleading failures; they are not established causes of the captured renderer stall.

The most actionable new lead is a GPU compatibility gap: the existing image can access NVIDIA D3D12 OpenGL 4.2 with `GL_NV_copy_image`, but not `GL_ARB_copy_image`. Ogre 2.2.5 leaves its NV-copy fallback disabled. Ogre 2.3.3 implements that fallback. A narrowly scoped, version-matched backport is a stronger candidate than more CPU-renderer parameter tuning or an unqualified ROS/Gazebo upgrade. It remains an unvalidated proposal.

## Evidence and root-cause boundaries

1. Historical statistics and native stacks corroborate a render-worker / Sensors / SimulationRunner waiting chain. A rendering delay can delay world progress because the Sensors system synchronizes scene updates with rendering. The [Fortress branch source](https://github.com/gazebosim/gz-sim/blob/ign-gazebo6/src/systems/sensors/Sensors.cc) documents this coupling. The exact generated shader remains unresolved.
2. `compose.yaml:14` forces software rendering for all services. The server additionally uses Xvfb; GUI containers separately render the same scene. A GPU was therefore not being used by the canonical runtime. Separate containers do not eliminate shared CPU and memory contention, but contention alone has not been proven to explain each stall.
3. Prior corrected GUI trial `20261016T095211551050Z` had a 2.031-second statistics gap with only 0.024 seconds of source-time progress, then a cloud freshness fault. IP fragmentation counters remained zero. That observation does not support blaming PACMod or DDS alone.
4. New read-only probes: Windows reports NVIDIA RTX 4060 Laptop GPU and Intel UHD. Native WSL defaults to Intel D3D12 OpenGL 4.1; explicitly selecting NVIDIA yields accelerated OpenGL 4.2. A disposable offline container using the existing image, `/dev/dxg`, WSL libraries and the WSLg X socket also reports NVIDIA OpenGL 4.2. It advertises NV-copy and omits ARB-copy. No persistent probe container or image was created.
5. In [Ogre 2.2.5 copyTo](https://github.com/OGRECave/ogre-next/blob/v2.2.5/RenderSystems/GL3Plus/src/OgreGL3PlusTextureGpu.cpp), the relevant ordinary texture-copy branch requires OpenGL 4.3 or ARB-copy and otherwise throws ERR_NOT_IMPLEMENTED; its NV branch is commented out. The installed plugin contains ARB-copy/glCopyImageSubData strings, with no matching NV-copy strings. This strongly matches the previously documented GPU texture-copy failure, but a new minimal failing GPU sensor case is still required to prove the exact call path.
6. [Ogre 2.3.3](https://github.com/OGRECave/ogre-next/blob/v2.3.3/RenderSystems/GL3Plus/src/OgreGL3PlusTextureGpu.cpp) implements an NV-copy alternative. This is relevant source evidence, not proof that replacing the current binary is ABI-safe or sufficient for every sensor texture format. [Mesa's D3D12 documentation](https://docs.mesa3d.org/drivers/d3d12.html) explains the OpenGL translation layer and explicit adapter selection; CUDA availability is not a renderer capability test.

The software stall and GPU startup exception are distinct failure mechanisms. Fixing GPU compatibility could avoid the problematic CPU path, but does not itself diagnose or repair llvmpipe. Previously tested worker-count, camera-noise removal and Ogre 1 changes failed and should not be promoted as fixes. Old [Fortress llvmpipe issues](https://github.com/gazebosim/gz-sim/issues/1116) are contextual evidence, not a matching bug identification.

## Code findings

### R1 - P1: lifecycle completion can clear a latched readiness fault

Location: `ros2_ws/src/agile_navigation/scripts/readiness.py:61-62`.

If a clock rewind trips readiness while the STARTUP service future is pending, its later successful completion sets `failed=False` and `active=True`. With fresh data/TF, inhibit becomes false without explicit fault recovery. An isolated execution of the actual update method with that state reproduced `{failed: false, active: true, inhibit: false}`.

Fix: make the fault latch monotonic until an explicit reset; invalidate startup completion using a generation/token, catch future exceptions, and do not accept an earlier startup response after a trip. Test clock rewind during pending startup and late success/failure responses.

### R2 - P1: loss of the readiness publisher does not invalidate its last permission

Location: `ros2_ws/src/agile_vehicle/scripts/vehicle_control.py:49-55`.

The controller remembers the last inhibit Boolean without a receipt timestamp. If readiness dies after publishing false while Nav2 and PACMod reports remain live, the steady timer continues using false. The core launch does not make readiness-process exit a mandatory stack shutdown. This is established by code inspection; process-death integration testing was not run.

Fix: add a steady-time readiness lease/heartbeat, fail closed on expiry, and explicitly define re-enable behavior. Publish node/lease health and test killing only readiness while command and report publishers remain active. Transient-local durability is not a heartbeat.

### R3 - P2: command bundling can starve or mix cycles

Location: `ros2_ws/src/agile_vehicle/scripts/control_logic.py:97-109`; producers in `vehicle_control.py:56-60`.

The buffer stores only one sample per field and accepts equality of ROS timestamps as cycle identity. Reproduction A: accelerator for cycle n+1 arrives before brake/steering for n; 60 otherwise complete cycles produce zero commits. Reproduction B: after committing accelerator=.2/brake=0, a brake=.4 update with the same timestamp immediately commits accelerator=.2/brake=.4 using old fields. Paused ROS time permits repeated stamps despite the wall-time publisher timer. The mock can consequently trip timeout or a spurious accelerator/brake interlock.

Fix: define cycle identity and duplicate handling explicitly, use bounded per-cycle assembly with ordering/age limits, and retain independent steady-time watchdogs. Avoid inventing frame IDs or bypassing the mandatory PACMod message chain. Cover fixed per-topic skew, repeated stamps, out-of-order delivery and clock rewinds. No evidence establishes this as the cause of the measured render-worker stalls.

### R4 - P2: acceptance timing and freshness can misclassify results

Location: `check_navigation.py:88,97-105` in the navigation scripts directory.

The route deadline is fixed wall time while speed is simulated-time based. At RTF=.21, 360 wall seconds provide only about 75.6 simulated seconds. The three-wall-second rest window additionally requires >10 feedback messages; at 30 simulated Hz that is about 18.9 samples at RTF=.21 and only nine at RTF=.1. Rest samples need not be consecutive and truth has no receipt/stamp freshness check at final acceptance. Historical GUI failure with eight rest samples is not evidence that this was its primary cause: that run had a genuine rendering/readiness failure.

Fix: separate simulated route-progress budget from a bounded wall-time hang/resource budget. Evaluate a consecutive fresh rest interval, reject duplicate/nonadvancing feedback, and require fresh truth. Keep actuator/sensor watchdogs on steady wall time; do not increase them to hide stalls.

### R5 - P2: fixture verification occurs after navigation and does not verify actual spawn

Location: `scripts/run_scenarios.py:79-86`.

The first-goal initial wheel-odometry check is evaluated only after the navigation subprocess succeeds. It cannot stop a wrong fixture before motion and is skipped on subprocess failure. Wheel odometry is initialized from the same requested values, so matching it alone does not independently prove the Gazebo model spawned correctly.

Fix: before enabling, verify requested configuration against actual model pose (test-only truth), rear-axle odometry and yaw; retain that preflight report on failures. Truth must remain outside operational localization/control. Keep the existing Windows-to-WSL forwarding regression.

### R6 - P2: image rebuilds are not yet reproducible

Location: `containers/Dockerfile:1,6-13`.

The base is a local mutable tag, apt dependencies are unversioned, and inherited PACMod/LIO packages are not reconstructed from pinned sources. Recorded image IDs describe a completed build but do not reproduce it.

Fix: record and validate the base digest, source revisions and graphics/ROS package versions. Build a narrowly scoped renderer candidate from explicit source/version inputs; retain the current image as a recoverable baseline during comparison and keep only the selected application image after acceptance, consistent with the project requirement.

Additional hardening before real hardware: validate finite joint/odometry payloads and advancing stamps; verify TF age rather than latest-transform existence alone; add readiness-process death, stale-but-republished data and malformed sensor tests. The simulator adapter uses a ROS-time timer/timeout, so do not infer an independent wall-time actuator stop from that layer. The outer mock/controller have steady-time checks. Disabled mock velocity is idealized and is not measured braking physics. Installed PACMod2 command messages were inspected: they do not contain an enable field; no missing-enable-field defect is asserted.

## Recommended implementation sequence

1. Fix R1/R2 and command assembly R3 with focused regression tests. These are deterministic application defects and do not require changing ROS or Gazebo.
2. Add a renderer capability preflight reporting actual adapter, software/hardware status, GL version and ARB/NV copy support. Keep all comparisons inside one `agile-slam` deployment project.
3. Reproduce the GPU copy failure with a primitive world and one original camera, then one original GPU LiDAR, then both. Capture source/destination texture format, target, layer/mip and call stack. Do not change sensor sampling or fake OpenGL capabilities.
4. Investigate a version-matched NV-copy backport to Ogre 2.2.5, building its renderer plugin against matching headers/core. Validate pixel/range readback, cubemap/depth/multisample paths and shader compilation. Do not drop a 2.3 binary into the 2.2 runtime. A Mesa update is a candidate only after measured extension/copy support, not an assumed cure.
5. First validate the full sensor server on GPU with headless clients. Then compare server + RViz, server + Gazebo GUI, and all three. Configure GPU libraries/devices only on render services. EGL headless mode is another capability-gated option; it does not manufacture missing extensions.
6. If no compatible WSL GPU path is demonstrated, compare the same Humble/Fortress image on native Linux NVIDIA OpenGL. A native Linux or remote Linux simulator backend can preserve the application contracts; network throughput/clock/TF must then be revalidated. Neither Hyper-V nor another VM should be assumed to provide native OpenGL.
7. Fix R4/R5, repeat cold-start routes and fault injection, then run a 20-minute moving dual-GUI soak. Require no freshness latch, valid sensor contracts, successful actions, independently confirmed start/end poses and fresh consecutive stopping observations. Freeze the accepted renderer/image/source versions.

## Verification and limits

Thirty existing unit tests passed. Three new diagnostic cases reproduced the startup-latch race, command-skew starvation and repeated-stamp mixed frame without ROS/hardware. GPU checks were read-only OpenGL capability probes, not Gazebo sensor acceptance. Live simulator containers were already stopped during review and were not restarted; shutdown exit codes are not treated as crash evidence. The user's separate `simulation_first_plan.md` edit was preserved. No runtime fix is claimed by this report.
