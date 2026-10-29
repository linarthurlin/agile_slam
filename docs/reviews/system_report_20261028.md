# Agile SLAM 系統檢查與程式碼審查報告

日期：2026-10-28
檢視版本：main，commit 1803b75（Fix readiness safety and add tested WSL GPU sensor backend）
範圍：程式與設定靜態檢視、既有測試、Compose 設定、驗證紀錄與官方相容性／支援期限資料。這不是安全性稽核，也不是實車驗收。

## 結論摘要

目前專案已從早期單一模擬容器，整理為一個 Compose 專案、六個明確命名的服務，以及共用的 ROS 2 vehicle-control／PACMod mock 控制鏈。Readiness lease、命令新鮮度、啟動故障鎖存與明確重新 enable 都有程式實作和單元測試支援。

平台適合作為**模擬軟體整合與初步導航測試環境**。它仍不是已量測的 GEM e6 digital twin、完整 sensor calibration lab、LIO/SLAM 驗證平台或可部署實車的系統。當前部署 CLI 只允許 sim 模式；真實 PACMod、CAN 與硬體 sensor backend 尚未實作。

本次沒有發現足以推翻目前模擬架構的程式缺陷；找到數項在擴展到長時間運行與實車之前應補強的 freshness、輸入驗證與建置可重現性工作，詳列於「程式碼審查發現」。

## 系統檢查結果

### 本次實際執行

| 檢查 | 結果 |
|---|---|
| Git | main 與 origin/main 同步於 1803b75 |
| 工作目錄變更 | 僅 docs/plans/simulation_first_plan.md 有既存未提交修改；本次未修改該檔 |
| Python 單元測試 | 52/52 通過 |
| Source/config 檢查 | 通過 |
| Small-city scene/map 產物一致性 | 通過 |
| 車輛幾何與 runtime interface contract | 通過 |
| Compose 軟體與 GPU overlay 設定解析 | 通過 |
| Docker／ROS 執行中檢查 | 未執行：環境依使用者要求維持暫停 |

Windows Docker CLI 回報 client 29.5.2，但無法連到 Docker Desktop Linux Engine named pipe；Docker Desktop、Docker backend 與 vmmemWSL process 查無運行項目。這符合先前「暫停 WSL 與 Docker」要求，不視為系統故障。本次因此不能重新確認 container 狀態、ROS graph、GPU rendering 或現場感測器輸出；相關運行結論引用既有驗證文件並標示其範圍。

### 主要架構

- 主機：Windows 11 + WSL2 Ubuntu 22.04 + Docker Desktop。
- 容器：amd64 Ubuntu 22.04、ROS 2 Humble、Gazebo Fortress、CycloneDDS。
- 唯一 Compose 專案：agile-slam；唯一應用程式 image tag：agile_slam:humble。
- 共用本機基底：agile_control_ros2:baseline-20261014；它不是本 repo 可獨立取得的公開基底。
- ROS domain 44、Gazebo partition agile-slam、Compose 私有 bridge network。
- 預設軟體渲染；可選 WSL NVIDIA overlay 只為 sensor backend 開 GPU 路徑，Gazebo／RViz GUI 保持軟體渲染。
- 六個容器：core、localization、vehicle-control、backend-sim，以及可選的 gazebo-gui、rviz。六者共用 image，但各自有獨立 container 與生命週期。

### ASCII System Diagram

~~~text
+-------------------------- Windows 11 host ---------------------------+
|                                                                      |
|  +------------------------- WSL2 Ubuntu 22.04 --------------------+  |
|  |  Docker Desktop Linux engine                                    |  |
|  |  Compose project: agile-slam | ROS domain: 44                   |  |
|  |  Gazebo partition: agile-slam | private bridge network          |  |
|  |                                                                  |  |
|  |  +----------------------+       +-----------------------------+  |
|  |  | core                 |       | localization                |  |
|  |  | map, Nav2, readiness |       | wheel odometry, known-start |  |
|  |  +----------+-----------+       +--------------+--------------+  |
|  |             | /cmd_vel                         ^ /joint_states    |
|  |             v                                  | /odometry/wheel  |
|  |  +----------------------+                      |                 |
|  |  | vehicle-control      |                      |                 |
|  |  | speed loop, PACMod   |                      |                 |
|  |  +----------+-----------+                      |                 |
|  |             | PACMod ROS commands              |                 |
|  |             v                                  |                 |
|  |  +----------------------+     sensor topics    |                 |
|  |  | backend-sim          |-----------------------+                 |
|  |  | Gazebo, bridges,     |                                         |
|  |  | PACMod mock, joints |                                         |
|  |  +----------+-----------+                                         |
|  |             |                                                     |
|  |             +---- optional gazebo-gui container                   |
|  |             +---- optional rviz container                         |
|  +------------------------------------------------------------------+ |
+----------------------------------------------------------------------+
~~~

### 車輛、控制與定位

- 模型是 e2 衍生替代車，不是依實車量測的 e6 模型。
- 共用車輛設定標示 hardware_validated=false；現值包括軸距 1.75 m、輪距 1.20 m、輪半徑 0.295 m、最大模擬速度 0.6 m/s。這些是模擬參數，不應拿來當 e6 校正值。
- Nav2 的 /cmd_vel 經 vehicle-control 轉為 PACMod accel、brake、steering、shift messages，進入 mock 後再轉為 /simulation/actuation 和 Gazebo joints；模擬 wheel feedback 回到控制器。
- Ready heartbeat 使用 advancing sequence、session id 和 0.5 秒 steady-time lease；lease 過期會 inhibit 並鎖存，需要資料恢復後明確重新 enable。mock 啟動時預設不允許致動。
- 定位為 wheel odometry + known-start map alignment。沒有接入 FAST-LIO、AMCL 或其他已驗收的全域定位；ground truth 僅作為測試評估輸入。

### Sensor 與世界模型

目前已驗證的主要 simulator ROS streams 為前方 RGB/Image + CameraInfo、IMU、LiDAR PointCloud2、virtual obstacle scan、joint feedback。small_city 已轉入 Fortress 場景和地圖流程。

- 模擬 LiDAR 發布 30,000 點，欄位 x/y/z/intensity/ring，約每 0.1 秒一筆模擬時間資料。
- IMU 約 50 Hz、前方 RGB 和 CameraInfo 約 30 Hz，均為設定／模擬時間頻率，不代表相同的 wall-time 吞吐率。
- LiDAR 是 snapshot scan，沒有逐點 firing time；目前無法據此驗證真實 Velodyne rolling scan 或 LIO deskew。
- depth／輔助相機在目前 navigation workload 關閉或未橋接；GPS、三顆前 LiDAR、多相機與 RealSense 尚未構成完整驗收 profile。
- 場景轉換為支援 WSL GPU rendering 修改 terrain visual mesh；碰撞幾何／道路地圖維持既有來源，但 terrain texture blending 沒有完整重現。

## 程式碼審查發現

| 優先度 | 發現 | 影響與建議 |
|---|---|---|
| P1（實車 gate） | 真實硬體 backend 尚未實作，deploy CLI 對 vehicle、vehicle-readonly、replay 模式採 fail-closed | 現階段不得用此 runtime 控制實車。完成車上 OS、感測器與 PACMod 硬體盤點後，才開發 hardware profile 和 read-only 輸入路徑。 |
| P1（支援期限） | ROS 2 Humble、Gazebo Fortress、Ubuntu 22.04 standard support 都接近 2027-05 | 維持目前穩定模擬基線，但需在支援期限前完成後續平台選型與遷移驗收。Ubuntu ESM 不會自動延長 ROS/Gazebo 發行版支援。官方期限見 [ROS Humble release announcement](https://discourse.ros.org/t/ros-2-humble-hawksbill-released/25729)、[Gazebo release table](https://gazebosim.org/docs/latest/releases/) 和 [Ubuntu release cycle](https://ubuntu.com/about/release-cycle)。 |
| P2（freshness） | readiness 對 map→base_rear_axle 使用 latest TF 可轉換性檢查，但沒有檢查動態 TF 的時間戳新鮮度 | 在 TF 發布停止但其他資料仍新鮮的故障情境下，readiness 可能仍看到一筆可用的舊 transform。加入動態 TF receipt/stamp age gate 與 stale-TF 故障測試。 |
| P2（輸入健壯性） | PACMod mock 的 joint callback 在有限值驗證前就對轉向 joint position 呼叫 tan | 非有限 steering 值可能造成數學函式例外。先驗證每個 joint name、position、velocity、stamp 都有效，再計算運動學；增加 malformed JointState regression。這是靜態檢視提出的風險，未在 ROS callback 中重現。 |
| P2（可重現建置） | Dockerfile 依賴本機可變 tag 基底，部分 apt 套件未固定版本 | 僅保存 image ID 不足以在新主機重建。固定 base digest、來源 revisions 和套件版本／snapshot；讓乾淨環境建置成為 CI gate。 |
| P2（驗證覆蓋） | 單元測試不涵蓋完整 ROS graph、container 間 DDS、長時間 GPU／GUI 與真實 driver | 恢復 runtime 後跑 cold-start、fault injection、重複導航和 soak；每種測試獨立保存 image/source/config 資訊和失敗證據。 |

### PACMod 研究與相容性風險

PACMod mock 已實作並走在模擬控制鏈內，但不能代表實車 driver 已接上。PACMod2 上游 driver 文件限定 board revision 2，明確指出不支援 PACMod3，且其支援車型列有 Polaris GEM e2/e4/e6 MY 2016+；這仍不能確認使用者手邊控制板的硬體世代、firmware、DBC 或 vehicle configuration。實作前必須讀取板卡與 vehicle type，不可僅因 ROS message package 名稱含 pacmod2 就推定硬體相容。[PACMod2 upstream README](https://github.com/astuff/pacmod2)

## 效能與驗證解讀

2026-10-16 的 WSL GPU 移動 sensor window 約 30 秒，估計 RTF 約 0.169；該段 LiDAR 的模擬時間頻率為 10 Hz，但 wall-time 接收約 1.69 Hz；RGB 模擬時間頻率約 30 Hz，wall-time 接收約 4.15 Hz。這代表模擬時鐘下的 topic stamps 正常遞增，不代表 simulator 即時運行或 wall-time 具有同等吞吐能力。

近期有針對性的 GPU camera/LiDAR 幾何檢查、右轉與 moving-fault 案例，以及軟體渲染導航和 PACMod mock contract 通過記錄。但完整重複雙 GUI 路線 suite、20 分鐘移動 soak、長距離重複與 sustained bag/transport acceptance 尚未完成。舊失敗紀錄保留於 validation report；整體驗證不能標記為 all-green。詳見 [GPU/runtime validation](../validation/gpu_runtime.md) 和 [dynamic scenario validation](../validation/dynamic_scenarios.md)。

## 建議決策

1. 保留目前 Humble/Fortress 作為可回歸的 simulator baseline，不要同時把 ROS、Gazebo、sensor 模型和控制鏈全部升級。
2. 先完成 docs、TF freshness、錯誤 sensor payload 測試，以及可重現 image build；恢復 Docker 後再跑 targeted route 和 fault regression。
3. 取得實車硬體清單後，確認 PACMod2 或 PACMod3，並決定 driver/message contract 與 CAN 接法。
4. 在 2027-05 前另開相容性分支評估 ROS 2 Jazzy + Ubuntu 24.04 + Gazebo Harmonic。Gazebo 官方配對表建議 Humble/Fortress、Jazzy/Harmonic；這是遷移候選，不代表本次已驗證或應立即切換。[Gazebo ROS pairing](https://gazebosim.org/docs/jetty/ros_installation/)

## 對應文件

- [Open-task roadmap](../roadmap.md)
- [Runtime architecture and operations](../runtime.md)
- [Architecture implementation baseline](../architecture/implementation-baseline.md)
- [GPU/runtime validation evidence](../validation/gpu_runtime.md)
- [Traditional Chinese simulator-first plan](../plans/simulation_first_plan.md)
