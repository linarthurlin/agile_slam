# 下一階段模擬測試計畫

日期：2026-10-31  
平台：Windows 11 + WSL2 Ubuntu 22.04 + Docker Desktop；ROS 2 Humble / Gazebo Fortress  
範圍：simulation only，不接觸實體 CAN、USB 或感測器介面

## 目的與驗收原則

以 Small City 與目前 split Compose runtime 為基線，依序驗收 Nav2、PACMod2 ROS mock、感測器資料品質、動態障礙物與動態錄製重播。每個案例保留 manifest、JSON 結果、logs、image/config/world/model fingerprints；失敗資料不覆蓋。

Gazebo ground truth 僅供 evaluator 使用，不可作為 localization 或 Nav2 的輸入。模擬通過不代表 e6 車體參數、實際感測器校正、PACMod ECU/CAN、實車制動距離或 real-time 安全已驗證。

每次測試一次只跑一個 scenario runner。結束時確認車輛靜止、mock disabled、狀態 fault 清楚；不為了讓測試變綠而放寬 freshness、rest 或導航誤差門檻。模擬時間與 wall time 分別記錄；RTF < 1 時不可宣稱模擬為 real-time。

## 已確認基線

- 10/31 split runtime 可見 GPU 曲線路線 3/3 通過；詳見 [split runtime acceptance](../validation/simulation-runtime-2026-10-31.md)。此結果尚未驗收 split topology 的交叉路口或 moving-fault suite。
- 車輛是 e2 衍生替代模型，localization 為 wheel odometry/known-start fixture；不是 e6 digital twin 或 LIO 定位。
- PACMod2 mock 只模擬 ROS command/report，不模擬 CAN frame、ECU、DBC 或實體 watchdog。
- URDF 的主要 sensor update rate 是 RGB 30 Hz、IMU 50 Hz、LiDAR 10 Hz；這些是 simulator 設定，不是尚未確認型號的實車硬體規格。
- check_sensors.py 已有 15 秒的 schema、frame、部分資料有效性、stamp/wall rate smoke；RGB 低於 24 Hz 僅是 warning，還沒有長時間掉包/gap 驗收。
- 計畫曾提及 check_nav2_actions.py 已測 NavigateToPose cancellation 與不可通行目標；本次檢查工作樹時未找到該檔案，因此這些 action case 尚未驗收，也未納入 scenario runner。Gate 3 開始前需先確認或建立測試器。
- bag_smoke.sh 有短錄製與隔離重播 smoke；動態路線、simulation-time bag timestamps、QoS 與禁止 actuator 輸出尚未形成 acceptance gate。
- 現有 footprint-overlap 是依靜態 map 幾何取樣，不能代替 Gazebo contact event。

先前紀錄中的 GUI exit 139 是使用者手動關 GUI 所致，不列作 Gazebo crash 缺陷。之後的 GUI case 要區分手動關窗與測試期間意外退出。

## Gate 1：左右交叉路口（下一個立即執行項目）

各自 cold-start、依序執行；使用 GPU rendering 並保持 Gazebo/RViz GUI 可見：

~~~powershell
python scripts/run_scenarios.py intersection-left --gui --rendering gpu
python scripts/run_scenarios.py intersection-right --gui --rendering gpu
~~~

**通過條件：** Nav2 SUCCEEDED；wheel odometry 與 evaluator truth 的目標位置誤差皆 <= 0.4 m；yaw 誤差 <= 0.35 rad；有有效 path/commands；無靜態 footprint overlap；clock、TF、point cloud、odometry、readiness 與 mock report 新鮮；到站後速度 < 0.02 m/s 並通過至少 1 秒 fresh-rest window；GUI 仍存活，runner 清理後 mock disabled。

若 GUI/GPU 失敗，保留原報告，再以同 route 的 headless GPU run 分流，對照 /world/small_city/stats、ROS timestamp/receipt gaps、renderer 與程序 log。headless 通過不能當作 GUI 通過。已知起點左右轉彎通過後，再獨立跑 intersection-left --start-x 0 長進場案例。

## Gate 2：PACMod2 mock moving faults

先降低 GUI 負載，依序測 controller-stop、backend-pause、readiness-pause：

~~~powershell
python scripts/run_scenarios.py faults --rendering gpu
~~~

每案先證明車輛正在移動，再注入 fault；驗證 command path 被 inhibit、feedback 回復後不可自動 enable、rest hold 成立且清理時 mock disabled。readiness-pause 另需證明新 ready heartbeat 後仍須明確 disable/enable 才恢復。

Backend pause 會凍結物理與 sensor，暫停期間無法量得停車距離；wall stopping time 不是 ECU watchdog 規格或實車制動量測。Gate 2 通過後，再新增 stale/re-published、delay/drop vehicle reports 與 clock freeze/rewind，各自保留 fault cause。

## Gate 3：Nav2 action／任務行為

先確認或建立 Nav2 action checker，再納入 scenario suite，補以下系統測試：

| 案例 | 驗收 |
| --- | --- |
| NavigateToPose cancel | 移動中取消，action 為 CANCELED；cmd 歸零且 fresh feedback 顯示停止。不是實車制動驗證。 |
| occupied/unreachable goal | 無非零移動命令；保存結果狀態及原因。 |
| Active goal replacement | 第二個有效目標取代第一個；舊目標終止、無兩個目標同時控制底盤，車輛只到達第二個目標。 |
| NavigateThroughPoses | 以可達 waypoints 驗證順序、最終位姿與 fresh rest。 |
| 空 waypoint／錯誤 frame | 不得以成功結束或產生非零 actuator command；保留拒絕/abort 診斷。 |

Nav2 上游 system tester 以 system-level 測試涵蓋 NavigateThroughPoses、空請求與 preemption，可參照其覆蓋方式：[Nav2 system tester](https://github.com/ros-navigation/navigation2/blob/main/nav2_system_tests/src/system/nav_through_poses_tester_node.py)。

## Gate 4：感測器資料、頻率與時序

延伸 check_sensors.py，收集至少 120 秒 simulation time，並設定獨立 wall-time timeout。每個 topic 報告 count、sim-stamp rate、wall receive rate、stamp interval p50/p95/max、最大 gap、stamp regression、payload validity、frame/schema；PointCloud2 另報欄位、point count、finite xyz，Image/CameraInfo 報尺寸/encoding/frame，IMU 報軸與重力讀值。

**首版建議門檻：**

- stamps 嚴格單調。
- 120 秒 sim-time window 的 message count 至少為 configured update rate 預期數量的 95%；未達時先查 Gazebo 更新、bridge、QoS、測試器負載，不下修門檻。
- RTF、wall receive rate、最大 gap 都列入報告，但在取得基準前不設定沒有依據的 real-time RTF 合格線。
- 用「sim-time receive age」描述依 /clock 估算的資料到達年齡，不把 ROS 收件時間誤稱為 sensor exposure/firing latency。

Gazebo Fortress 提供 sensor update_rate 與 world stats 的 sim_time、real_time、real_time_factor，應同時檢查模擬時間與主機收件時間：[Fortress Sensors](https://gazebosim.org/docs/fortress/sensors/)、[Fortress world stats](https://gazebosim.org/docs/fortress/sdf_worlds/)。

第一輪限定現有 RGB、CameraInfo、IMU、Velodyne cloud、obstacle scan。再逐項新增 depth/RealSense、前方三顆 LiDAR、GNSS/UM982 的資料層模擬；GNSS 僅模擬 ROS data、covariance、noise、latency/dropout，不模擬 serial、RTCM/NTRIP、USB 或 receiver protocol。

## Gate 5：動態障礙物與 contact event

新增固定起點、速度、啟動時間、路徑與模型 fingerprint 的 moving-obstacle fixture：

1. 障礙進入規劃路線：scan/costmap 可見；Nav2 減速、停止或重規劃；車體不接觸障礙。
2. 障礙離開：確認資料與 readiness 新鮮，再規劃並抵達有效目標。
3. 獨立低速 contact positive-control 證明接觸事件來源有效；避障 case 再驗證 contact event 為零。

需增加 Gazebo contact sensor/system 或等價碰撞事件讀取；碰撞偵測器正控制與導航避撞是兩項不同驗收。

## Gate 6：動態 rosbag record/replay

把 bag_smoke.sh 擴充為一次可移動路線的動態錄製與隔離重播：

- 記錄 /clock、/tf、/tf_static、必要 sensor topics、wheel odometry、/cmd_vel、PACMod2 reports 與 readiness/control diagnostics。Ground truth 只給獨立 evaluator，不進 localization/Nav2。
- 提供 QoS overrides、bag metadata、commit/image/config/world fingerprints 與案例結果。
- 使用 rosbag2 simulation-time recording 時，等第一筆 /clock 後再驗證 bag；重播確保只有一個 clock owner，sim-time nodes 設定 use_sim_time。
- 使用隔離 ROS domain；replay 時不得啟動 Gazebo、sim-bridge、PACMod mock 或 actuator consumer，並證明不會產生 mock command。
- 驗證 topic/schema/count/stamps、late-joining subscriber 的 /tf_static、重播結果可離線重現。

rosbag2 的 `--use-sim-time` 依 `/clock` 作錄製時間戳，也支援 per-topic QoS override；收到第一筆 clock 前不會寫入訊息，啟動順序因此要納入測試：[rosbag2 simulation time](https://github.com/ros2/rosbag2/blob/rolling/README.md#simulation-time)、[rosbag2 QoS override](https://github.com/ros2/rosbag2/blob/rolling/README.md#overriding-qos-profiles)。

## Gate 7：重複性及雙 GUI soak

單次 Gate 1–6 通過後才跑三次 suite：

~~~powershell
python scripts/run_scenarios.py all --repeat 3 --rendering gpu
~~~

先 headless 做重複測試；再獨立進行 20 分鐘 Gazebo/RViz GUI soak，使用低速重複路線，記錄 RTF、sensor stamp/receipt gaps、DDS/IP counters、CPU/RAM、service restart、GUI liveness、readiness faults。每輪結束 mock disabled、車輛靜止。三次全通過才算 repeatability gate；單次視窗可見只算 targeted integration pass。

## Gate 8：LIO／deskew 前置條件

完成 sensor timing 與動態 bag 後，才進入 synthetic LIO：

- 先確認實車 Velodyne 型號、return mode、point-time 語意及目標 LIO 欄位要求；型號未知時不宣稱資料與實車完全同型。
- ROS PointCloud2 contract 明列 x/y/z/intensity/ring 與逐點 acquisition offset 的欄位型別、單位、scan-start/end 參考語意。
- 以已知速度與轉向軌跡比較 deskew 前後 cloud/map 殘差，ground truth 只供獨立 evaluator 使用。
- 證明 estimator 未訂閱 ground-truth pose。

Synthetic deskew 通過只證明受控資料鏈與演算法；真正 Velodyne/IMU timestamps、外參與 noise 仍需實車資料驗證。

## 建議順序與第一批執行命令

| 順序 | 工作 |
| --- | --- |
| 1 | split-runtime 左右交叉路口 |
| 2 | split-runtime PACMod2 moving faults |
| 3 | Nav2 cancel/preemption/NavigateThroughPoses suite |
| 4 | 120 秒 sensor timing/throughput |
| 5 | moving obstacle/contact instrumentation |
| 6 | dynamic bag/isolated replay |
| 7 | repeated suite/20-minute GUI soak |
| 8 | point-time contract/synthetic LIO deskew |

~~~powershell
python scripts/run_scenarios.py intersection-left --gui --rendering gpu
python scripts/run_scenarios.py intersection-right --gui --rendering gpu
python scripts/run_scenarios.py faults --rendering gpu
~~~

此文件建立期間不啟動、停止或重設 runtime。每個命令完成後先審閱 manifest/報告、確認車輛靜止與 mock disabled，再執行下一案。任一測試失敗，保留證據並先分流 headless/Gazebo stats/ROS freshness，不跳過失敗直接跑全套。

