# Software-renderer stall investigation

Date: 2026-10-16. Platform: Docker Desktop / WSL2 Ubuntu 22.04, ROS 2 Humble, Gazebo Fortress, Mesa 23.2.1. Application image remains `agile_slam:humble` (`c82685c8a18c`).

## Status

Headless regression passes with the 128-bit workaround. Simultaneous GUI navigation is **not accepted**: a correctly configured GUI trial still reproduced a 2.031-second simulation-progress gap and a LiDAR freshness fault. The underlying rendering problem remains open.

## Findings

The MTU correction remains active. The newly reproduced failures had zero IP fragmentation/reassembly counter deltas. Independent Gazebo Transport statistics and Linux thread samples show simulation-progress stalls while a single llvmpipe worker consumes CPU. The read-only sampler continued at roughly 0.25-second intervals during the stalls, so the missing statistics cannot be explained solely by a stalled host reader.

An intrusive native debugger capture corroborated the blocked chain:

- Main server: `SimulationRunner::UpdateSystems` waits in `Barrier::Wait`.
- Sensors update: `Sensors::PostUpdate` waits.
- Render thread: `CompositorPassQuad::execute` / `GL3PlusRenderSystem::_render` waits in Mesa.
- Three llvmpipe workers wait at a pthread barrier while another executes generated shader code.

The generated shader has no resolved source symbol. This evidence does not identify a specific shader, establish an upstream bug, or prove that every historical stall has the same cause. Attaching a debugger pauses the target and can itself trip watchdogs; that run is diagnostic-only, excluded from acceptance.

## Controlled comparisons

| Configuration | Run | Result |
| --- | --- | --- |
| Original automatic vector width, 24 observed workers | `20261016T084719822936Z` | Right turn failed; 1.50 s statistics gap, LiDAR age 2.09 s |
| Four renderer workers | `20261016T085145328690Z` | First right turn passed, second failed; 4.61 s gap and only 0.006 s simulated progress |
| Original workers, front-camera Gaussian noise removed | `20261016T091530024923Z` | Right turn failed; 2.27 s gap |
| 128-bit vector width, original sensors restored | `20261016T091943785956Z` | Two cold-start right turns passed; maximum gaps 0.297 / 0.343 s |
| 128-bit, complete headless suite | `20261016T092714633912Z` | Three continuous curve goals, left/right intersections and both moving fault cases passed |
| 128-bit, both GUIs, incorrect WSL fixture | `20261016T094321514038Z` | Failed deadline; actual start 0 instead of requested 30; maximum gap 0.235 s; excluded from fixture acceptance |
| 128-bit, both GUIs, corrected fixture | `20261016T095211551050Z` | Failed LiDAR freshness; maximum source-progress gap 2.031 s |
| Ogre 1 sensor/GUI comparison, 128-bit | `20261016T100141579440Z` | Failed almost immediately after navigation started; maximum gap 3.312 s; reverted |

The four-worker and camera-noise changes were reverted. No sensor resolution, scan geometry, update rate, goal tolerance, freshness timeout or PACMod watchdog threshold was relaxed. Sensor units and configured rates remain simulation-time quantities.

The Ogre 2 backend retains `LP_NATIVE_VECTOR_WIDTH=128` as the tested headless candidate, an option described in the [Mesa LLVMpipe guide](https://docs.mesa3d.org/drivers/llvmpipe.html). Treat this as a tested local workaround, not proof that the underlying driver defect is fixed. A new Mesa/LLVM version, GPU, host or scene requires regression testing.

## Deployment fix and sensor checks

The new GUI scenario path initially lost `AGILE_SPAWN_X/Y/YAW` when Windows delegated startup to WSL. `deploy.py` now passes all three as literal `env` arguments, including explicit zero defaults. Two unit regressions cover nonzero/negative values and paths with spaces. Container environment and initial wheel odometry confirmed the corrected (30, 0, 0) fixture. The scenario evaluator additionally checks first-goal wheel-odometry origin against the configured rear-axle start within 0.05 m. This check is not reapplied to later goals in the same continuous route.

Both moving and GUI 30-second sensor sanity windows passed without warnings. Estimated real-time factors were 0.275 and 0.211 respectively. These short successful windows do not override the failed GUI route or establish hardware timing. Original 800x600 camera images and 16x1875 snapshot LiDAR remain configured.

Read-only Linux X11 captures confirmed both windows and the vehicle/point cloud display. Some small_city materials remain magenta, and RViz logged a map shader link warning. Visual/photometric fidelity remains unaccepted; screenshot inspection was partial because the windows overlapped.

## Diagnostics

`sample_gazebo_process.py` discovers the server dynamically and collects read-only thread CPU/wait/scheduler data and CPU/memory pressure. `GazeboMonitor` stores the capture next to each navigation result and records effective renderer environment for future runs. The optional analyzer correlates long statistics gaps with busy threads. No debugger or extra Linux capability is required by the committed runtime.

Raw local diagnostic-only files: `artifacts/native_capture/`; failed trials remain under `artifacts/scenarios/`. Reviewed evidence is in `render_stalls_results.json`. Raw logs are intentionally excluded from Git.

## Remaining limits

Repeated short turns do not establish long-duration stability, long-approach acceptance, all scene coverage or real-time behavior. Known-start wheel odometry, the e2 surrogate, snapshot LiDAR and the ROS PACMod mock retain the limits described in the canonical runtime report. LIO, rolling-scan deskew, real CAN/PACMod and vehicle deployment remain separate work.


## Next investigation

Prioritize mapping the busy generated shader to its Ogre compositor pass, then compare a pinned Mesa/LLVM update or a verified GPU backend. Native Linux rendering is a separate comparison, not proof of WSL2 correctness. After a candidate passes both GUIs, repeat long approaches and a sustained moving soak before promoting full desktop stability. Keep the original watchdogs and all negative evidence.
