# WSL GPU and control remediation

Date: 2026-10-16 (America/Los_Angeles). UTC artifact IDs may begin 20261017.

## Implemented

- Readiness startup completion cannot clear an already latched fault.
- Vehicle-control requires a live advancing readiness heartbeat; expiry inhibits and requires explicit re-enable after recovery.
- PACMod command assembly buffers bounded asynchronous cycles; duplicate committed stamps cannot renew freshness. Frozen simulation time cannot manufacture new command cycles.
- Route acceptance checks actual spawn before actuation, separate simulation/wall budgets, advancing fresh truth and consecutive fresh rest.
- A matching Ogre Next 2.2.5 GL3Plus plugin includes an NV_copy_image fallback, source checksums, build-feature compatibility checks and installed plugin hash verification.
- The optional WSL NVIDIA sensor-server overlay uses the existing project/image. GUI clients retain software rendering after Qt/D3D12 context creation failed in the Gazebo client. City terrain visuals use a source-height-image mesh because Terra's compute shader fails on this GL 4.2 path. Road/map/collision hashes remain unchanged; heightmap texture blending is not reproduced.

## Executed evidence

52 unit tests, source checks and generated-scene consistency checks passed. The image builds all five project ROS packages.

Primitive GPU run `20261017T011036Z` passed camera-only, LiDAR-only and combined operation. Camera output is rgb8 800x600; the explicit diffuse wall has about 40.9% warm-color pixels. The cloud has 30,000 samples, with 16,077 finite points in the baseline scene and approximately 1.78 mm median absolute error against the wall front face. This is a synthetic geometry check, not hardware accuracy or calibration evidence.

Earlier primitive runs `20261017T005955Z`, `20261017T010302Z` and `20261017T010638Z` failed the color criterion. Inspection identified an unspecified diffuse wall material and then a threshold exceeding the measured rendered channel separation. The wall now explicitly specifies diffuse color; the retained criterion checks visible warm color with a nonblank image. These failed trials are retained locally.

Initial city GPU trial `20261017T011111419097Z` failed before navigation: TerraShadowGenerator compute compilation aborted the server. Its failure and raw log `artifacts/gpu_city_failure.log` are retained. The terrain mesh conversion addresses this distinct failure; primitive success alone did not establish city readiness.

The first city route/fault suite `20261017T011548049724Z` passed all five navigation goals plus controller-stop and backend-pause, but failed the readiness recovery expectation: resumed readiness correctly latched stale-data loss, so disable/enable alone could not restore control. The corrected test restarts core with an observer in localization, then verifies fresh readiness and explicit re-enable. This run is failed overall, not accepted as a complete suite.

Its early routes also requested two GUIs while the Gazebo Qt/D3D12 client had exited. Later switching clients to software restored the actual Gazebo window. Consequently this run is mixed GUI evidence; it is not a dual-GUI pass. The new runner requires live containers and actual X11 client windows before actuation and after every scenario.

The RViz indexed-map sampler warning is a known upstream first-message issue, which can occur without incorrect map rendering ([RViz issue 463](https://github.com/ros2/rviz/issues/463)). A warning alone is not evidence that the map is broken or correct. Visual and topic checks remain separate.

## Final configuration regression

Fault run `20261017T013242389894Z` passed all three moving cases with GPU sensor server and software GUI clients. Actual Gazebo/RViz client windows were verified before enable and after each fault. Readiness loss inhibited motion, core restart restored ready heartbeats, no automatic resume occurred, and explicit disable/enable restored motion. The mock was disabled during cleanup. Wall stopping observations are simulation/orchestration measurements, not physical ECU deadlines or braking distances.

The original five navigation goals passed positional, yaw, overlap and consecutive-rest checks. The early-route GUI limitation above remains; a separate final-configuration turn regression is reported below.

Observed city simulation real-time factors are below one (roughly 0.2–0.6 during these captures). Removing multi-second stalls does not establish real-time performance.

## Limits

Twenty-minute continuous moving dual-GUI soak, long-approach repetitions, depth/cubemap/MSAA variants, sustained best-effort transport and dynamic bag/replay remain separate gates. No full desktop stability claim is made from short routes. The plugin build is source-traceable; the inherited application base and unpinned apt dependencies are not yet fully reproducible. The e2 surrogate, wheel-only known-start localization, snapshot LiDAR and PACMod ROS mock remain provisional. No real CAN/ECU, LIO deskew or measured e6 performance is established.

Final-configuration right-turn run `20261017T013543754766Z` passed with actual Gazebo/RViz client windows verified before enable and after arrival. The concurrent 30-second reliable sensor sanity window passed without backward timestamps or RGB acquisition-rate warnings. These establish targeted operation, not the entire repeated dual-GUI suite or continuous soak.

Software fallback also passed actual start-pose preflight, a 3 m navigation goal and the ROS PACMod mock contract regression. The contract test deliberately leaves a readiness fault latched; all services are cold-started afterward before restoring the GPU GUI session.

Machine-readable positive/negative evidence, image IDs, source and asset fingerprints are retained in [gpu_runtime_results.json](gpu_runtime_results.json). Large raw artifacts remain local and ignored.
