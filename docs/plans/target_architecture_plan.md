# Agile_SLAM 目標架構與重新建置計畫

日期：2026-10-15（America/Los_Angeles）。前提：開發電腦為 Windows＋WSL2；GEM e6 搭載一般 x86_64 Linux PC，不是 Jetson。實車 Linux 發行版、GPU 及 sensor／PACMod 型號仍未知。此文件定義建議目標，尚未安裝新 WSL distro、搬移 checkout、替換 Compose 或改動實車。

## 1. 架構決策

採用同一 repository、同一 amd64 應用程式 images、共用 ROS 介面與分層設定；由單一部署入口選擇 sim／vehicle-readonly／vehicle／replay。以 Ubuntu 24.04＋ROS 2 Jazzy＋Gazebo Harmonic 為目標，先做 PACMod／LIO／WSLg 建置與運作 feasibility gate，再完整遷移。舊 Humble／Fortress 保留為可重現回歸基線，無需為重建新架構而刪除。

不把舊 agile_control_ros2 image 當長期 build foundation；從公開可追溯基底與 pinned source/dependency 建立新 image。兩台都是 amd64，可重用同一應用 image digest，但 kernel、GPU host driver、USB／CAN 與顯示掛載仍依主機不同。

## 2. 版本選擇

| 組合 | 本專案用途與取捨 |
|---|---|
| Humble／Fortress／22.04 | 已通過短程測試，作 legacy baseline；不繼續擴大所有新功能對其耦合 |
| Jazzy／Harmonic／24.04 | 推薦目標；官方配對、amd64 Tier 1、Jazzy 至 2029-05；Velodyne 有 Jazzy release，RealSense README 列出支援 |
| Lyrical／Jetty | 官方相容的新配對；現有 PACMod／LIO port 與完整 SDK matrix 未驗證，暫不作主線。這是專案相容性取捨，不宣稱新版無法使用 |

沒有在 Jazzy rosdistro distribution.yaml 找到 PACMod 項目，不可據此推斷第三方沒有套件；須核對 vendor repository／本機 ROS2 source，先固定 message definitions 與對應 driver revision。ROS distro 跨版本通訊不是預設相容方案；driver 如必須保留舊環境，使用有測試的明確 adapter／bridge 當過渡，不把 Humble 與 Jazzy 任意混在一個 ROS domain 當作可行證據。

## 3. 主機環境

### 開發端

Windows 11 提供編輯器與桌面；獨立 WSL2 Ubuntu 24.04 提供 Linux shell／Git；Docker Desktop 的 WSL2 backend 執行 Linux containers。此專案只選一個 Docker daemon，不同時混用 WSL 原生 dockerd 與 Desktop 的 image／context。

新開發 checkout、build cache、assets 與工作中 bags 放在 WSL Linux filesystem 或 Docker named volumes；Windows D: 保留既有 checkout、備份及匯出，不在遷移前移除原路徑。Windows 編輯器透過 WSL integration 存取；Dev Container 與 runtime 共用基底／依賴。這可減少跨檔案系統 I/O、權限、case／換行差異；實際性能仍須量測。

核心 ROS 與 Gazebo server 預設在 containers，不要求 Windows 原生 ROS。RViz／Gazebo GUI 是獨立可選 tools services，透過 WSLg 顯示。圖形相關 socket、Mesa／WSL driver mounts 僅在 desktop overlay，不能進車載共用 base。

### 實車端

候選標準主機為原生 Ubuntu 24.04 amd64＋Docker Engine／Compose plugin。既有 Linux 若不同版本，先盤點 kernel、driver／SDK；容器 user space 可用 24.04，但不據此假設所有 USB／GPU／CAN 能運作，也不先重灌主機。

主機負責 NIC／IP、SocketCAN bitrate、udev／USB、GPU driver、系統時間同步、SSD／log rotation、開機與關機處置；Docker 負責版本固定的 ROS／SDK user space。systemd 可管理部署啟停，但所有 actuation 重啟後仍 disabled，須重新通過 readiness 與明確 enable。

## 4. 服務邊界與 image 策略

| 服務群 | 共用內容 | 模式差異 |
|---|---|---|
| core | description／TF、必要感測器前處理、map、Nav2、任務及 readiness coordinator | 讀取不同 geometry／calibration／clock／localization profile |
| localization | 可替換 LIO、全域定位／map alignment | wheel-only debug、LIO、已知 map localization 或 replay；每條 TF 唯一 authority |
| vehicle-control | 目標速度／路輪角轉換、速度閉迴路、command arbitration、PACMod adapter、command/report freshness | 相同程式與 interface；可有不同實測 tuning，板卡版本由 adapter 選擇 |
| backend-sim | Gazebo server、spawn、sim joints、sensor bridges、PACMod mock | 僅 sim 啟動，獨立於 core 生命週期 |
| backend-hardware | 真實 sensor drivers、PACMod driver／CAN transport | 僅 vehicle-readonly 或 vehicle；只讀模式禁止 actuator output |
| tools | RViz、Gazebo GUI、recorder、diagnostics／evaluation | 可選；不承擔車輛控制的必要功能 |

這是功能分組，不要求六群一開始全部各一 image。推薦一份 pinned runtime base，再用 multi-stage targets 產生 core、sim、drivers、tools；localization 依 eigen/PCL/CUDA 相依需求有獨立 target。相同依賴可共用 image 執行多個 services。依 SDK、裝置權限或獨立重啟需求拆 sensor driver，避免每個 ROS node 一個容器。

第一個可用版本先有三個共用 runtime service（core、localization、vehicle-control）＋一個 backend；GUI／recorder 可選。不是把整個 Autoware 搬入本專案；只借用介面分層及 base/overlay deployment 方法。

## 5. 控制與資料契約

固定高層 /cmd_vel 型別（Twist 或 TwistStamped 依所選 Nav2 release 明確配置，不交由 defaults 漂移），由 vehicle-control 轉成明確定義的目標速度與路輪角。可用 AckermannDriveStamped 作內部標準化 setpoint；速度閉迴路再產生 PACMod 油門／煞車與方向盤角命令。

sim：Nav2 → 共用 vehicle-control → PACMod messages → mock → 模擬 actuator adapter → Gazebo joints → PACMod feedback reports。
vehicle：Nav2 → 同一 vehicle-control → 對應板卡 messages → PACMod driver → CAN／ECU → feedback reports。

未知板卡前以已核對的 pacmod2_msgs 作 provisional contract；實車若為 PACMod3，替換對應 adapter／mock／driver message contract，保持上層 setpoint 與 controller 邏輯。不得以 pacmod2_msgs 宣稱可直接控制 PACMod3。

PACMod mock 包含 enable／gear／override／fault、互鎖、限幅、報告有效性與 timeout；不加入使用者已移除的 delayed plant 作必備功能。控制 backend 只有一個，不能留有 Nav2→joint 的旁路。停止 Gazebo 時 vehicle-control 應進不可用／停止狀態，core 不必跟著 process shutdown；關閉 simulator 不代表可在原 session 無條件切到真車。

Sensor contract 包含 PointCloud2 layout、ring／firing time、scan stamp、frame、CameraInfo、IMU axis／units／covariance、QoS、有效範圍與版本。truth 只進 evaluator；nominal/estimated calibration 決定演算法使用的 TF／內參。unknown sensor 型號持續明確標示，不能以 generic depth camera 冒稱完整 RealSense 模擬。

## 6. 網路與時間

開發端選獨立 private Compose bridge network，各 ROS／Gazebo client services 加入同一 network，不再共用 simulator 的 network namespace。CycloneDDS 綁可達 container interface，驗證 discovery／multicast，必要時以固定服務命名／peers 管理；實作前測不同 container IP／重啟行為，不用 loopback XML 套全部容器。

實車初期推薦對 ROS hardware/data-plane services 使用原生 Linux host networking，便於 UDP LiDAR、SocketCAN 及同主機 DDS；可對不需 host access 的工具另外限制。固定 ROS_DOMAIN_ID 與正確 NIC／peers。這是本案部署簡化的建議，不代表所有 ROS 系統都必須 host networking。

Docker Desktop host networking 與原生 Linux 不完全相同，其支援偏 TCP／UDP layer 4，不能據此在 Windows 上證明真 SocketCAN；桌面模擬不依賴 host networking。WSL mirrored networking 不作單機容器互通的必要前提。

sim／replay：唯一 /clock source，所有相關 nodes use_sim_time=true；vehicle：use_sim_time=false，校對硬體 acquisition time 與系統 clock，PTP／PPS 是否可用仍依型號。系統時間由主機服務管理。相同 domain 不混用 sim 與 live sources；跨模式切換重啟 clock-sensitive estimators/controllers。

## 7. WSL 圖形與效能處理

WSLg OpenGL 使用 Mesa/D3D12 路徑；CUDA container GPU access 不等於 Ogre rendering 已相容。現有 Fortress/Ogre2 已實際失敗過，升到 Harmonic／新 Mesa 是重新驗證機會，不宣稱必定修復。

先驗證新 GUI／sensor-rendering profile：glxinfo／renderer、camera／depth／LiDAR 輸出、Gazebo＋RViz 同開穩定性與 RTF；同時保留可重現 software headless CI。若桌面 WSL 無法達到需求，可從 Windows 開發端操作 native Linux 的 simulation compute，仍執行同一 sim image/config；這是性能補充路徑，WSL 本機基本模擬仍須通過，不把問題藏起來。

性能 gate 分級：功能模式容許低 RTF但必須報告；目標性能模式若要求即時則量測 RTF、wall-time sensor throughput、queue/drop、CPU／GPU與延遲。不能靠改 nominal rate 或把 sim-time Hz 當 wall-time Hz 掩蓋負載。

## 8. 專案組織與操作

目標目錄（研究提案，未建立啟動命令）：

```text
agile_slam/
  compose.yaml
  deploy/                 # desktop-sim, linux-vehicle, replay overlays
  containers/             # pinned base and multi-stage runtime targets
  config/                 # common contracts, vehicle, sensors, DDS, profiles
  calibration/            # versioned estimated results and manifests
  ros2_ws/src/            # description, bringup, sensing, localization, vehicle, simulation
  scenarios/              # route definitions, faults, evaluation thresholds
  scripts/                # doctor, deploy, validate, record/replay
  docs/                   # English operations; Traditional Chinese plans
  assets/                 # ignored pinned/cache assets
  artifacts/              # ignored runs, bags, reports
```

單一 CLI 目標：doctor、build、up sim、up vehicle-readonly、up vehicle、up replay、test scenario、record、status、down。這些是介面設計，不是已可執行的命令。wrapper 驗證合併後 Compose config、互斥 backend、clock、calibration/profile、readiness 與 command authority；profiles 本身不執行互斥。GUI、錄製與故障注入由選項控制。

持續使用公開 GitHub 版控與可追溯 release tags；新 images 可由 CI 建立並依 digest 部署。發布 image 前核對 SDK/asset redistribution，不能把舊私人 base image 直接推公開 registry。實車 IP／serial／credentials／bags 放 local config 與外部資料儲存；Git 保存設定模板及 manifest schema。

## 9. 重建順序與退出條件

| 階段 | 內容 | 驗收與決策 |
|---|---|---|
| A0 | inventory／driver source、Jazzy build matrix、WSLg GPU＋sensor feasibility | PACMod messages/driver source 可追溯、LIO選定版本可建置、GUI及sensor正常；任何不相容先解決或選有測試的過渡 adapter |
| A1 | clean public base＋core／sim／tools targets；small_city Harmonic 轉換 | 乾淨環境可重建；同時檢查世界 physics／materials／collision；既有3/8/16m測試回歸 |
| A2 | 獨立 core/localization/vehicle-control/backend，Compose overlays＋readiness | 關 Gazebo 不殺 core；graph無重複TF／commands；GUI不依附sim namespace；跨容器cloud/image通過 |
| A3 必做 | PACMod mock／adapter／速度閉迴路與故障回歸 | enable、gear、override、fault、stale command/report、互鎖、取消、停止及重啟不自動enable |
| A4 | 固定 scenario runner、動態bags與CI | 直行／左右轉／路口各三次，軌跡／heading／collision與停止指標；replay無實體輸出 |
| A5 | 真實 firing-time rolling Velodyne、LIO、calibration profiles | deskew開關／時間offset對照；held-out校正與估計器真值隔離 |
| A6 | 車載 Linux readonly bringup與compute-in-loop | 真實sensor/PACMod/DBC確認，USB/NIC/CAN/time/CPU/GPU/SSD負載，使用與sim相同core image digest |
| A7 | 封閉場地低速動態驗證 | 實車tuning、人工接管、失聯／停止與重啟；每次run可追溯 |

A0–A4 優先建立可靠平台；A5 的 LIO 與完整校正不能只靠新 ROS 版本宣稱完成。現有可動 baseline 可作比較，待新架構達成驗收再切主線，避免失去可用測試環境。

## 10. 研究來源

- ROS/Gazebo 官方配對：https://gazebosim.org/docs/latest/ros_installation/
- ROS REP-2000：https://github.com/ros-infrastructure/rep/blob/master/rep-2000.rst
- Jazzy release catalog（Velodyne／PACMod查核）：https://github.com/ros/rosdistro/blob/master/jazzy/distribution.yaml
- RealSense supported setup：https://github.com/realsenseai/realsense-ros
- WSL filesystem：https://learn.microsoft.com/en-us/windows/wsl/filesystems
- Docker Desktop WSL backend：https://docs.docker.com/desktop/features/wsl/
- Host network differences：https://docs.docker.com/engine/network/drivers/host/
- WSLg graphics：https://github.com/microsoft/wslg
- Open AD Kit base/overlay deployments：https://autowarefoundation.github.io/openadkit/deployments/
- Clearpath shared configuration：https://github.com/clearpathrobotics/clearpath_simulator

本計畫是針對已知需求的推薦，不將未知硬體支援、圖形修復或即時性能當成已驗證事實。
