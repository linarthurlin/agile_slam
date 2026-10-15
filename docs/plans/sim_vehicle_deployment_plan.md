# 模擬／實車共用部署架構與待辦

日期：2026-10-15（America/Los_Angeles）。狀態：研究及目標架構，尚未實作新 Compose profiles；現有 simulator 與使用者修改的 simulation_first_plan.md 保留。

## 1. 結論與現有落差

可以讓同一套 repository、ROS 介面、上層程式與 Compose project 部署於開發電腦及車載電腦；切換 sim／vehicle／replay backend。Docker 的可攜性不能取代 driver、host kernel／GPU、實車校正及車輛動力參數確認。共用架構的目標是減少程式分叉，不是所有參數或 image binaries 完全相同。

目前 sim 容器同時啟動 Gazebo、bridge、robot_state_publisher、wheel odometry、Twist adapter 與 Nav2；停掉 sim 會一起失去上層系統。baseline launch 在 Gazebo 退出時會 shutdown。GUI 透過 scripts/gui.sh 另啟動並共用 sim 的 network namespace，CycloneDDS 綁 loopback；拆成獨立容器後不能直接沿用此網路假設。

## 2. 參考案例

- Autoware Open AD Kit：容器化元件、共用 base Compose 與不同 simulation overlays，包含 vehicle-system 與 simulator 類元件。此為共用部署設計的參考，不宣稱其已提供對應本車 PACMod 的可直接使用部署。
  https://autowarefoundation.github.io/openadkit/deployments/
  https://autowarefoundation.github.io/openadkit/components/
- Clearpath：clearpath_simulator 與 real robot stack 共用 robot.yaml、config parser 及 descriptions，替換硬體執行端；其價值是設定及介面共用，不是照搬其全部容器配置。
  https://github.com/clearpathrobotics/clearpath_simulator
- ros2_control：hardware abstraction 可替換實體、Gazebo 或 mock backend。PACMod 整合仍可維持 ROS command/report contract，無須強迫真 PACMod 一定經由與 Gazebo 相同的 joint controller。
  https://control.ros.org/jazzy/doc/ros2_control/hardware_interface/doc/hardware_components_userdoc.html
- Compose profiles 可選擇服務；overlays 可改時間、裝置、網路及參數。profiles 本身不是互斥機制，切換 profile 的 up 也不能當成舊 backend 已停止的保證。
  https://docs.docker.com/compose/how-tos/profiles/
  https://docs.docker.com/compose/how-tos/multiple-compose-files/merge/
  https://docs.docker.com/compose/how-tos/networking/

## 3. 目標服務邊界

| 服務 | simulation | vehicle | replay |
|---|---|---|---|
| description／TF config | 共用程式，使用參考 geometry | 共用程式，使用實車 calibration | 使用 bag 對應版本；避免重複 TF |
| localization | 共用演算法；先 wheel baseline 後 LIO | 共用演算法與實車參數 | 同程式離線驗證 |
| autonomy | Nav2、任務與 vehicle controller | 同程式；實車 tuning | 預設不向真 actuator 輸出 |
| simulator | Gazebo、spawn、sim joints、sensor bridge | 停用 | 停用 |
| pacmod-mock | 接收 PACMod commands 並回報模擬 feedback | 停用 | 預設停用；可獨立測試 |
| hardware | 停用 | Velodyne／IMU／camera／RealSense／PACMod driver | 停用 |
| recorder／diagnostics | 可選 | 可選 | 可選 |
| visualization | Gazebo GUI／RViz 可選 | RViz 可選，無 Gazebo | RViz 可選 |

初期可將 description、localization 與 autonomy 中相容的 ROS process 分組於少量容器；不採每個 node 一個容器。依 GPU、SDK、裝置權限或獨立重啟需求才進一步拆分。LIO 可於獨立 image/container 解決相依套件衝突；sensor driver 不必一開始每顆各一容器。

共同控制鏈：Nav2 → vehicle controller → PACMod command contract → backend → feedback reports。
sim backend：PACMod mock → 模擬 adapter → ros2_control joints。
vehicle backend：對應實車版本 PACMod driver → SocketCAN／適用 CAN transport → PACMod ECU。
回授由實際 backend 量測產生，不能以 command echo 取代。sim 與 vehicle 的上層 vehicle controller 共用程式，允許不同 tuning 與控制限制。

## 4. 設定與部署模型

建議重構後使用一個 Compose project，拆少量檔案：compose.yaml（共用服務）、compose.sim.yaml、compose.vehicle.yaml、compose.replay.yaml；GUI／recording 可作 profiles。主模式由 deploy wrapper 選擇恰好一種，並先檢查合併後 configuration。

目標操作介面為 deploy sim、deploy vehicle、deploy replay，尚未建立此命令。wrapper 不只是開 profile：須確認舊 backend、殘留 GUI 與命令 producer 已停止，清除或重建受 clock reset 影響的 ROS nodes；實車 actuation 預設 disabled，不因容器 restart 自動恢復 enable。提供只讀 hardware bringup 模式先驗證資料。

共用 config 管理 sensors、vehicle geometry、topic contract、frame、message schema、資料單位、timestamp、QoS 及 calibration ID。simulation、vehicle、replay 各自保存 runtime override；serial／IP／CAN channel 等機器資料放 ignored local config。每次 run manifest 記錄 code commit、image digest、geometry、calibration、driver revision、模式與 bag checksum。

## 5. 不能只靠切容器解決的差異

- 時間：simulation 與 replay 使用唯一有效 /clock 並一致 use_sim_time=true；vehicle 的 ROS nodes 使用已同步的系統時間，硬體 acquisition stamps 須轉到相容時鐘域，use_sim_time=false。保留 scan-start/end 及逐點 firing 定義；暫停／reset 與真實失聯的 watchdog 分開驗證。
- DDS：現有 loopback 適用共享 namespace；獨立 bridge containers 須配置可達網路介面／discovery，實車可能需要 Linux host network 或明確 peers／NIC 選擇。各種模式均測大點雲、影像及跨容器 delivery。host network 是選項，不是假設所有 driver 都必須用它。
- TF：description、driver、bag、wheel odom 與 LIO 不得同時發布同一條 edge；map→odom 及 odom→base 各有唯一 authority。切 LIO 時保留 wheel topic，關閉其競爭 TF。固定起點 identity alignment 不可帶到實車充當全域定位。
- 裝置：Velodyne 是 Ethernet/UDP；RealSense 常需 USB／udev；V4L2 cameras 可能需 /dev/video*；SocketCAN 是 Linux network interface，不是通用 /dev/can0 device。只向 hardware backend 配置所需裝置與權限。主機端準備 NIC、CAN bitrate、時鐘同步與 GPU driver。
- 平台：車載以原生 Linux 作候選，依既有 driver 相容性決定 ROS／Ubuntu；WSL2 留作桌面開發。若車載是 ARM64／Jetson，須重新建對應 architecture image，核對 CUDA／JetPack，不能直接執行目前 amd64 image。
- 模型：保留 e2 baseline；e6 reference 只能依來源建立可選 profile，未知年份、輪距、重心及轉向 mapping 不冒稱實測。感測器型號未知時完整接入目標仍有待實車確認的 gate。
- 效能：容器不會消除 GPU driver／kernel／USB 等主機差異，也不保證控制 deadline；在車載 compute 上做負載及 command/report latency 測試。
- Actuation：模式互斥、command authority、enable／override／fault、stale report、timeout 與獨立人工接管是此車控制需求；Compose process-running／healthcheck 不等於 ROS data ready 或允許驅動。

## 6. 待辦順序與完成條件

| 順序 | 工作 | 完成條件 |
|---|---|---|
| D0 | 固定 sensor／vehicle／PACMod 資料契約與單一 config | topics、frames、單位、timestamps、QoS、未知硬體皆可追溯 |
| D1 | 拆分 simulator 與共用 ROS bringup；Compose profiles／overlays、GUI 整合 | 停 Gazebo 不會把共用節點一起 shutdown；網路不依附 sim namespace；新架構重跑既有 3/8/16 m regression |
| D2 必做 | PACMod mock＋共用 vehicle controller | Nav2 必須經 PACMod commands；joint feedback reports、enable/override/fault、gear、互鎖及 timeout 全部通過 |
| D3 | 動態資料集、重播與故障回歸 | 固定路線三次、左右轉／路口、動態 bag、static TF late join、clock reset、command/report loss；回放不碰實體控制 |
| D4 | Velodyne schema 與 rolling-scan、LIO 接入 | 真正 firing-time 量測、deskew 對照、時間 offset 故障、軌跡誤差；無 truth 洩漏至演算法 |
| D5 | 完整 sensor profiles 與校正框架 | truth／estimated 分離；外參、內參與時間 offset 的 held-out 驗證；未知型號標示 placeholder |
| D6 | 實車只讀 hardware bringup | 真實 driver、hardware timestamps、TF、IP／serial／CAN／firmware／DBC 確認；重啟可重現，actuation disabled |
| D7 | 低速封閉場地與硬體驗收 | enable／override／fault／停止處置、速度／轉向 tuning、長時間負載與人工接管驗證 |
| D8 | 建置、CI 與平台維護 | 從乾淨 Linux 可建置；image digest／架構固定；headless runtime regression；規劃維護版本遷移 |

GPU rendering、城市材質與地形／碰撞一致性列為平行修正；它們不可掩蓋控制、定位與 sensor fidelity 的驗收缺口。

## 7. 移植驗收矩陣

SIL：全部模擬，驗證共用軟體與介面。
車載 compute-in-loop：同一套模擬資料在實際車載電腦運行，量測效能／部署差異。
硬體 bench／HIL：只有確實接入感測器、CAN 或 PACMod 硬體才稱硬體測試；ROS mock 不冒稱 HIL。
實車：實際安裝校正、失聯與低速運動驗收。

若將來分散到多台車載主機，Compose 不會自動跨主機編排；各主機需自己的部署入口與共同設定／DDS 網路設計。
