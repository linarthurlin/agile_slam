# 模擬／實車共用部署架構與待辦

日期：2026-10-31（America/Los_Angeles）。狀態：目標架構與實作順序；本次明確決策：simulation 只模擬 ROS sensor data，不模擬 CAN／Serial transport；PACMod 保留 pacmod2_msgs command/report 介面 mock。現有 simulator 與使用者修改的 simulation_first_plan.md 保留。

## 1. 結論與現有落差

同一個 repository 維持共用 ROS data contracts、autonomy、localization 與 vehicle-control；以 Compose base 加 sim／vehicle／replay overlays 選擇資料來源和硬體 backend。Docker 的可攜性不能取代 driver、host kernel／GPU、實車校正及車輛動力參數確認。

Simulation 的感測器邊界是資料層：Gazebo sensor plugins／ROS adapters 直接發布 ROS messages，注入可控雜訊、延遲、dropout、品質狀態與故障；不建立 fake tty、serial protocol、USB bridge、NTRIP/RTCM transport、SocketCAN 或 CAN frame emulator。PACMod 是例外但只到 ROS 介面層：simulation 使用 pacmod2_msgs command/report mock 控制 Gazebo joints，不產生或驗證 CAN frames。真實 Serial／CAN 與 driver 測試只在 vehicle／硬體 bench 進行。

現有 sim 容器同時啟動 Gazebo、bridge、robot_state_publisher、wheel odometry、Twist adapter 與 Nav2；停掉 sim 會一起失去上層系統。baseline launch 在 Gazebo 退出時會 shutdown。GUI 目前有獨立啟動路徑；目標設計讓 GUI 作為 Gazebo container 內可選啟動的 process，ROS service 生命週期仍由 deployment wrapper 管理。

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
| autonomy | Nav2、任務／路徑演算法 | 同程式；實車 tuning | 同程式離線驗證 |
| vehicle-control | 速度／轉向控制與 pacmod2_msgs commands；不接 CAN | 同一服務，命令交給 pacmod2-driver | 預設只記錄，不輸出 actuator command |
| Gazebo | Gazebo server、spawn、sim joints 與 Gazebo GUI（GUI 選擇性啟動） | 停用 | 停用 |
| sim-bridge | Gazebo↔ROS sensor data bridge、資料品質／故障 adapter、pacmod2_msgs mock；不模擬 Serial／CAN | 停用 | 停用 |
| hardware-sensors | 停用 | 真實 Velodyne／IMU／camera／RealSense／GNSS drivers；依 transport、權限與 SDK 分組 | 停用 |
| pacmod2-driver | 停用 | PACMod2 ROS driver＋真實 CAN transport；vehicle mode 專用 | 停用 |
| recorder／diagnostics | 可選 | 可選 | 可選 |
| visualization | RViz 可選；Gazebo GUI 由 Gazebo container 選擇性啟動 | RViz 可選，無 Gazebo | RViz 可選 |

共用 runtime roles 為 autonomy（Nav2、任務／路徑演算法）、localization、vehicle-control（速度／轉向轉換與 PACMod ROS command contract）；Dev Container 僅供編輯、colcon build/test，不自動啟動模擬或硬體。vehicle-control 與 autonomy 維持分開 service，便於單獨重啟及驗證 command safety。依 SDK、裝置權限或獨立重啟需求拆分 vehicle sensor services，不採每顆 sensor 一容器。

目標 sim 容器：0025-gazebo 負責 world、vehicle、sim joints 與可選 GUI；0025-sim-bridge 合併 Gazebo↔ROS sensor data bridge、資料品質 adapter 和 pacmod2_msgs mock。共用 autonomy、localization、vehicle-control 只消費／輸出 ROS topics。PACMod mock 回報由 Gazebo joint／vehicle state 產生，並將 PACMod command contract 映射到模擬 actuators；不實作 CAN/vcan。

目標 vehicle 容器：不啟動 Gazebo 或 sim-bridge；0025-gnss 獨占 UM982 的實體 serial endpoint，其他感測器依 Ethernet／serial／USB／SDK 與裝置權限分組；0025-pacmod2-driver 才能接觸 PACMod CAN。vehicle-control 不直接開 CAN。Compose base 共用程式與 ROS contracts，sim、vehicle、replay overlays 各自選 backend；同一時間只允許一種 actuator backend。

共同控制鏈：Nav2／autonomy → vehicle-control → pacmod2_msgs command → backend → feedback reports。
sim backend：pacmod2_msgs mock → Gazebo actuator adapter → simulated joints → reports。
vehicle backend：PACMod2 driver → 實體 CAN → PACMod ECU → reports。
兩端不共用 transport，只共用 ROS command/report contract。回授由 backend state 產生，不能以 command echo 取代；sim ROS timeout mock 不等於 CAN bus／ECU 故障驗證。

## 4. 設定與部署模型

建議重構後使用一個 Compose project，拆少量檔案：compose.yaml（共用服務）、compose.sim.yaml、compose.vehicle.yaml、compose.replay.yaml；GUI／recording 可作 profiles。主模式由 deploy wrapper 選擇恰好一種，並先檢查合併後 configuration。

目標操作介面為 deploy sim、deploy vehicle、deploy replay，尚未建立此命令。wrapper 不只是開 profile：須確認舊 backend、殘留 GUI 與命令 producer 已停止，清除或重建受 clock reset 影響的 ROS nodes；實車 actuation 預設 disabled，不因容器 restart 自動恢復 enable。提供只讀 hardware bringup 模式先驗證資料。

共用 config 管理 sensors、vehicle geometry、topic contract、frame、message schema、資料單位、timestamp、QoS 及 calibration ID。simulation profile 只設定 ROS data source／noise／fault scenarios，不含串列埠、baud rate、RTCM transport、CAN interface 或 USB passthrough。vehicle profile 才保存 serial／IP／CAN channel 等 ignored host-specific 設定；每次 run manifest 記錄 code commit、image digest、geometry、calibration、driver revision、模式與 bag checksum。

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
| D0 | 固定 sensor／vehicle／PACMod ROS 資料契約與 source mode | topics、frames、單位、timestamps、QoS 與 ROS-level PACMod contract 固定；sim 與 vehicle transport 邊界清楚 |
| D1 | 拆分 simulator 與共用 ROS bringup；Compose profiles／overlays、GUI 整合 | 停 Gazebo 不會把共用節點一起 shutdown；網路不依附 sim namespace；新架構重跑既有 3/8/16 m regression |
| D2 必做 | pacmod2_msgs ROS mock＋共用 vehicle controller | Nav2 必須經 PACMod ROS commands；Gazebo joint feedback reports、enable/override/fault、gear、互鎖及 ROS command/report freshness 通過；不使用 CAN/vcan |
| D3 | 動態資料集、重播與故障回歸 | 固定路線三次、左右轉／路口、動態 bag、static TF late join、clock reset、command/report loss；回放不碰實體控制 |
| D4 | Velodyne schema 與 rolling-scan、LIO 接入 | 真正 firing-time 量測、deskew 對照、時間 offset 故障、軌跡誤差；無 truth 洩漏至演算法 |
| D5 | 完整 sensor profiles 與校正框架 | GNSS fix／heading／quality ROS data scenarios 可重播；truth／estimated 分離；外參、內參與時間 offset 的 held-out 驗證；未知型號標示 placeholder |
| D6 | 實車只讀 hardware bringup | 實際 sensor drivers、UM982 serial endpoint／RTK correction path、PACMod2 driver／CAN、timestamps、TF、firmware／DBC 確認；重啟可重現，actuation disabled |
| D7 | 低速封閉場地與硬體驗收 | enable／override／fault／停止處置、速度／轉向 tuning、長時間負載與人工接管驗證 |
| D8 | 建置、CI 與平台維護 | 從乾淨 Linux 可建置；image digest／架構固定；headless runtime regression；規劃維護版本遷移 |

GPU rendering、城市材質與地形／碰撞一致性列為平行修正；它們不可掩蓋控制、定位與 sensor fidelity 的驗收缺口。

## 7. 移植驗收矩陣

SIL：全部模擬，驗證共用軟體與介面。
車載 compute-in-loop：同一套模擬資料在實際車載電腦運行，量測效能／部署差異。
硬體 bench／HIL：只有接入真實 sensor／serial receiver／PACMod CAN ECU 才算 hardware-in-loop；PACMod ROS mock 與 Gazebo sensor data test 是 SIL，不驗證 serial protocol、CAN frame 或 receiver RTK solver。
實車：實際安裝校正、失聯與低速運動驗收。

若將來分散到多台車載主機，Compose 不會自動跨主機編排；各主機需自己的部署入口與共同設定／DDS 網路設計。

## 8. 本輪實作進度（2026-10-31）

已在本機加入第一階段的架構切分：

- compose.yaml 保留共用 ROS runtime 服務；compose.sim.yaml 定義 Gazebo 與 sim bridge；Dev Container 使用獨立 dev build target 與 agile-slam-dev Compose project。
- 新增 sim_bridge.launch.py，將 sensor bridges、spawn/controllers 與 PACMod2 ROS mock 從 Gazebo server process 分開。
- Gazebo 與所有 ROS runtime containers 使用明確 0025-* 名稱；Gazebo GUI 改由同一服務選擇 headless 或 GUI process，RViz 保持可選。
- 部署、場景監測、GUI 檢查與 GPU sensor 工具改指向新服務名稱；up 會冷啟動整個 sim project，避免只重啟 /clock owner。
- README 與操作文件已改成英文並描述目前的目標拓樸；本繁中計畫保留實作狀態與未完成 gate。

目前尚未做乾淨 Docker build、Dev Container 啟動或新拓樸 runtime test；WSL／Docker 仍依照先前要求保持暫停。既有 route、sensor 與 PACMod validation 是舊拓樸證據，不能直接算作此重構通過。

接續工作：恢復環境後先建 runtime/dev targets，再驗證 Compose 合併結果、跨容器 DDS／Gazebo Transport、/clock、TF、sensor streams 和 PACMod2 mock control path；完成後重跑原有路線與 moving-fault regression。vehicle overlay、UM982 real serial service、真 PACMod2 CAN service、資料層 GNSS scenario 與校正框架仍未實作，不能以目前 sim profile 代替。
