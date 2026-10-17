# 渲染與控制鏈修復實作計畫

日期：2026-10-16。依據：docs/reviews/system_code_review_20261016.md。維持 Ubuntu 22.04／Humble／Fortress、單一 agile-slam project、共用應用層及可替換 backend。

## 研究結論

目前包含兩條獨立問題：CPU llvmpipe 渲染停滯，以及 WSL D3D12 GPU 的 Ogre texture-copy 相容性。原生 WSL 與既有 image 的臨時容器均已確認 RTX 4060 可用；OpenGL 4.2 缺少 ARB_copy_image，提供 NV_copy_image。Ogre 2.2.5 的 NV fallback 未啟用，而 2.3.3 有對應實作。這提供明確的 backport 研究方向，但仍須重現相同 GPU 例外並驗證 texture 格式；不能宣稱修法已通過。

## 依序實作與驗收

1. 修正 readiness 的 startup future 清除 fault latch、control 缺少 readiness lease，以及 PACMod CommandBundle 的 skew／重複時間戳問題。加入 pending-startup clock rewind、readiness node death、跨 topic 延遲與重複 stamp 測試；不依賴更換顯示引擎。
2. 新增實際 renderer capability preflight。記錄 adapter、Mesa／LLVM／Ogre 版本、OpenGL 與 ARB／NV copy 支援；不要只檢查 CUDA 或 nvidia-smi。
3. 以最小 primitive world 依序測相機、GPU LiDAR、兩者同時，重現 texture-copy 呼叫，記錄 src／dst format、target、layer／mip 與 stack。維持原 sensor specs。
4. 評估將 NV-copy fallback 回植到匹配的 Ogre 2.2.5 renderer plugin，保留核心 ABI。驗證 image／range readback、depth／cubemap／MSAA 及 shader；不要直接混用 2.3 binary 或假造 OpenGL version／extension。Mesa 更新也必須先證明提供所需能力。
5. 同一 compose project 建立桌面 GPU 設定，只對 simulator／Gazebo GUI／RViz 掛載必要 GPU 裝置與 libraries。逐步驗證 server-only、加 RViz、加 Gazebo GUI、雙 GUI。WSL GPU 未通過時，對照同 image 的原生 Linux NVIDIA backend；需要重新驗證跨主機 DDS／clock／TF／吞吐。
6. 驗收工具分開 sim-time route budget 與 wall-time hang budget，保留 steady-time 安全 watchdog。啟用前以 test-only truth 核對 Gazebo 起點與 wheel rear-axle 起點／yaw；到站要求 fresh truth 與連續 fresh rest，不以累積 frame 數代替持續停車。
7. 所有候選先做 cold-start 路線、故障注入及 20 分鐘持續動態雙 GUI soak，通過後固定 image／renderer／package／source 版本，再接續 LIO／rolling-scan／校正。保留全部失敗證據。

此計畫尚未實作 runtime 修復。本輪只完成 review、read-only capability probes 與獨立缺陷重現；既有運行設定與使用者的 simulation_first_plan.md 修改維持。
