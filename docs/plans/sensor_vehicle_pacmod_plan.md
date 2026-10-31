# 感測器、車輛與 PACMod 整合澄清及實作計畫

修訂日期：2026-10-31（America/Los_Angeles）。使用者目前沒有 Velodyne 型號、e6 年份及 PACMod firmware／DBC 資料。既有正常運行的模型與 GUI 不因本次研究直接切換；候選規格須標示來源與未知項目。

## 1. Velodyne 相容性分成三層

1. ROS 介面：固定 driver revision、topic、frame、QoS、PointCloud2 fields／datatype／offset／point_step／row_step、organized／unorganized 與無回波規則。官方 ROS2 PointcloudXYZIRT 使用 x/y/z/intensity float32、ring uint16、time float32；需核對實車所用 driver，而非假設所有版本相同。
2. 量測語意：光束角度、laser ID 到 ring 對應、firing 順序、RPM、return mode、距離、強度與逐點時間。Velodyne 原始硬體送 packets；PointCloud2 是 driver 解碼產物。Gazebo 直接產生符合已選 driver ROS schema 的 sensor data，不模擬 Velodyne UDP packet／driver transport；packet 與 driver 測試只能在實體 sensor 或硬體 bench 驗證。
3. 動態物理：每點在自己的 firing time，從當時的 sensor pose 對當時場景求交。不能替同一時刻生成的整圈快照補一欄時間，便宣稱能驗證 deskew。

目前 gpu_lidar：16 個等間距垂直 samples、1875 個水平 samples、10 Hz、無逐點 time。不能據此認定實車是 VLP16；VLP16 僅作可明確標示的開發候選。

實作順序：定義 driver 相容契約 → snapshot adapter（標示無 deskew 驗證能力）→ firing schedule 與逐批 ray casting 的 rolling-scan plugin → 靜態／轉彎／動態物體實驗 → FAST-LIO。每點時間單位、scan stamp 定義、reset 行為及 IMU 覆蓋範圍均入設定。

驗收：欄位與 serialization；已知平面在不同速度／yaw rate 的殘差；同一資料 deskew 開／關對照；加入時間偏移後殘差變差；獨立真值不得成為 LIO 的執行輸入。僅使用姿態對快照點雲做反向變換可作單元測試，不可替代真正 rolling ray casting，也無法重現遮蔽與動態物體。

來源：
- https://github.com/ros-drivers/velodyne/blob/ros2/velodyne_pointcloud/src/lib/pointcloudXYZIRT.cpp
- https://github.com/ros-drivers/velodyne/blob/ros2/velodyne_pointcloud/src/lib/rawdata.cpp
- https://github.com/ros-drivers/velodyne/blob/ros2/velodyne_pointcloud/params/VLP16db.yaml

## 2. e6 模型與候選規格

找到 Nova-UTD/navigator 的 data/hail_bopp.urdf 與 hailbopp.stl，可作 e6 研究平台描述／外觀候選；repository LICENSE 為 MIT。檢視 dev commit 24c111ce8a53a240bb3be81b52f9eabead173200：URDF 含絕對 mesh 路徑、0.25 kg 主體與 inertia TODO，未包含完整輪組／轉向控制及 Gazebo 車輛系統，不能直接替換目前可動模型。不匯入資產，先沿用 e2 visual mesh。

公開官方規格存在差異：2024 owner manual 列軸距 3.39 m、外形約 4.24×1.41×1.86 m、乾重 769 kg、Turning Circle/Radius 6.71 m；目前官方產品頁列軸距 3.404 m、Turning Radius 5.59 m、鋰電版本乾重 672 kg。這些不能混成同一輛實車設定；轉彎規格也不能直接當後軸中心路徑半徑。

將來源候選保存為 config/vehicle/e6_references.json，預設不啟用。可獨立建立明確命名的 e6 reference profile，但須同步改 wheel joint origins、wheel odometry、control geometry、footprint、planner curvature 與 rear-axle frame；不得只改 Nav2 的 wheelbase。車寬不是輪距，乾重不是主體 link 質量，輪胎標稱尺寸不是實測滾動半徑；缺少的輪距、重心、慣性、轉向映射與實車 sensor mounts 保留未知。

來源：
- https://github.com/Nova-UTD/navigator/blob/dev/data/hail_bopp.urdf
- https://github.com/Nova-UTD/navigator/blob/dev/LICENSE
- https://www.gemcar.com/wp-content/uploads/2024/03/MY24-GEM_web.pdf （PDF 第 86 頁）
- https://www.gemcar.com/gem-e6/

## 3. 多感測器與校正框架

建立單一 inventory，以 sensor ID 綁定型號狀態、topic、frame、幾何、頻率、clock、noise 與 calibration ID。Velodyne、主要 IMU、前方三 LiDAR、多 camera、RealSense 都有可選 profile；未知 2D／3D scanner 類型及 RealSense 子功能不假裝已確認。

分離兩套值：truth mounting／intrinsics 決定 Gazebo 的量測；estimated calibration 決定發布給演算法的 TF 與 CameraInfo。固定 TF 每條 edge 只有一個 authority；truth 只進 evaluator。正常 profile 使用正確參數；fault profile 注入外參、內參、時間 offset/drift/jitter/dropout，量測 timestamp 與 delivery time 分開。

第一批校正實驗：已知多平面／標靶場；單顆相機內參 → LiDAR-camera 外參 → 有重疊 FOV 的 LiDAR-LiDAR → 有充分運動激發的 IMU 時空校正。只能平面行駛時，須報告不可觀測自由度，不宣稱完整 6-DoF 已校正。

每次保存 raw bag、truth、初始誤差、工具版本、估計結果與 held-out 驗證。指標包含重投影殘差、平面距離、旋轉／平移／時間 offset 誤差及重複性。工具候選為 camera_calibration、Kalibr、direct_visual_lidar_calibration；依所選版本處理 ROS1/ROS2 離線資料轉換。

來源：
- https://github.com/ethz-asl/kalibr/wiki
- https://github.com/koide3/direct_visual_lidar_calibration

## 4. 模擬資料邊界與 UM982／RTK 整合

### 硬體拓撲解讀

UM982 原廠手冊中的 ANT1（主天線）與 ANT2（從天線）是同一顆 UM982 接收模組的兩個天線輸入；該模組可計算位置與雙天線航向。MJRTK-982 的 Base/Rover 快速指南則描述兩個實體模組及 Base TXD → Rover RXD 的 RTCM 串列連結，這是另一種配置。現有公開資料沒有證明「母／子 receiver 經單一自訂 adapter 合成一條 USB serial stream」是標準接法；軟體不得先假設只會有一個 tty。Vehicle bring-up 依實際 Linux 裝置枚舉映射一個或多個 tty 至 0025-gnss。

車上若使用一顆雙天線 UM982，兩天線提供位置／航向 baseline；RTK corrections 仍由 NTRIP caster 或獨立 Base station 提供。修正來源目前未知，列為 vehicle integration gate。若使用實體 Base/Rover pair，須另定義 Base 的固定位置、RTCM 傳輸路徑與天線配置；它不等同於雙天線 heading。

### Simulation 只模擬 ROS 感測器資料

- Gazebo／ROS adapter 直接發布 sensor_msgs/msg/NavSatFix 及一個明確定義的 heading/status ROS contract；不建立 fake serial port、UM982 byte protocol、USB device、NTRIP/RTCM link 或 receiver emulator。
- GNSS data profile 可注入位置雜訊／covariance、延遲、跳點、漂移、遮蔽／dropout；另以 diagnostics/status scenario 表示 FIXED、FLOAT、SINGLE、NO_FIX 等品質狀態。不要把 RTK FLOAT/FIXED 硬塞進 NavSatStatus.status 的不相符 enum。
- 雙天線 heading 由模擬車身真值 yaw 加上指定誤差生成，輸出介面與硬體 driver 正規化後一致；truth topic 只供 evaluator，不能餵給 localization。
- 這能驗證 ROS 資料契約、定位融合、品質降級與故障回復，不能驗證 UM982 serial parser、NTRIP、RTCM 傳輸、載波相位解算或實機固定解。需要檢查 parser 時可用真實接收器錄下的 bytes 做離線單元測試；serial／RTK 硬體驗收仍在 vehicle bench 完成。

### ROS 與 localization 接法

硬體與 simulation 正規化為共同的 GNSS position、heading、quality 與 diagnostics contract。NavSatFix 提供全域位置；獨立 heading adapter 依已核對的 UM982 heading reference、角度正負、單位及 ENU/NED 慣例轉成 localization 可用的方向觀測。不得將 GNSS heading 假裝成完整 IMU（尤其不能假造 angular velocity／acceleration）。

LIO／wheel odometry 維持連續的 odom → base_link；以 robot_localization/navsat_transform_node 將 GNSS position 投影至世界座標，再由全域 estimator 產生 map → odom。GNSS 可修正全域漂移及提供航向參考，不直接取代 LIO，也不在未確認演算法支援前當成 FAST-LIO 的 GNSS factor。base_link 至 GNSS 天線的 lever arm、天線 baseline、datum、heading convention、covariance 與時間戳都納入 calibration/config manifest。

來源：
- UM982 原廠手冊：https://m.unicorecomm.com/assets/UM982_User_Manual_R1.7/index.html
- MJRTK-982 Base/Rover 快速指南：https://manuals.plus/m/3098ac7c60295eaf5f50f0dc509fe298edf6a8e7f208c3fd840880c5c742a7f40
- robot_localization navsat_transform：https://github.com/cra-ros-pkg/robot_localization/blob/rolling-devel/doc/navsat_transform_node.rst

## 5. PACMod 為必做控制路徑

使用者要求 simulation 與 vehicle 軟體統一採用 pacmod2_msgs／PACMod2 driver contract，PACMod 為必要控制路徑。Simulation 只 mock ROS command/report，不模擬 CAN；車上要使用 PACMod2 driver 與真實 CAN。實車板卡／firmware／DBC 仍需核對後才能啟用，不可由 ROS mock 推論硬體相容。

控制鏈：Nav2 cmd_vel → vehicle controller（速度閉迴路、方向盤角命令）→ PACMod commands → PACMod mock／模擬車輛 adapter → ros2_control joints。以實際 joint feedback／模擬車速產生 reports，回到 controller。mock profile 必須停用現有直接 Twist-to-Ackermann 路徑，避免繞過 PACMod 或兩個 command writers 競爭。

已在現有容器核對的訊息：
- pacmod2_msgs/SystemCmdFloat：header、command。
- pacmod2_msgs/PositionWithSpeed：header、angular_position、angular_velocity_limit。
- pacmod2_msgs/SystemCmdInt：含 SHIFT_PARK=0、REVERSE=1、NEUTRAL=2、FORWARD=3。
- pacmod2_msgs/VehicleSpeedRpt：vehicle_speed、vehicle_speed_valid。
- pacmod2_msgs/GlobalRpt：enabled、override_active 與多個 timeout/error 欄位。

原始工作區已有 cmd_vel_to_pacmod2.py 與設定，可參考但不照搬：其中 wheelbase=3.4、steer_ratio=16、油門／煞車 PID、最低油門與 gear 等不是實車確認值。方向盤角與路輪角必須明確區分；例如 /pacmod/steering_cmd 的角度不能直接當 wheel joint 角。

階段 A：ROS 介面及狀態機 mock（disabled/enabled/override/fault、gear、command/report timeout、油門煞車互鎖、轉向角／速率限制、速度 feedback）。mock 的油門煞車到速度模型參數明確標為工程假設，不冒充真實 firmware／力學；先不加入延遲 plant。
階段 B：Nav2 經 PACMod mock 行車，驗證 PID、限幅、到站保持、取消、失聯、report 無效／過期、override/fault、reset，並證明沒有旁路命令。
階段 C：取得實車板卡／firmware／DBC 後，在 vehicle hardware bench 接真正 PACMod2 driver 與實際 CAN/ECU，驗證 frames 和回報。simulation 不啟動 CAN/vcan，不測 CAN encoding 或 ECU 行為；ROS mock 通過不等於硬體已驗證。

驗收要求：disabled 不驅動；fault/override 依定義退出自動控制且不自行重新 enable；上層命令過期後不得藉 timer 重新發布而掩蓋；無效車速 report 不可繼續正常閉迴路；不允許非預期油門與煞車同時輸出；速度與控制狀態 report 必須反映回授，不能僅回送 command。

來源：https://github.com/astuff/pacmod2 （官方硬體世代與 CAN 介面參考；其預設 branch ROS API 不能直接取代本機 ROS2 訊息契約。）

## 6. 接續順序

1. 鎖定 inventory、資料契約與現有模型 geometry；保留可用基線。
2. PACMod ROS mock、速度閉迴路與狀態／故障測試，完成 Nav2 經 PACMod 的低速控制鏈。
3. Velodyne driver 相容 schema，再做真實 firing-time rolling scan 與 deskew 對照。
4. 多感測器 profile、truth/estimated calibration 分離、校正及故障實驗。
5. 取得實車資訊後，啟用對應 e6 geometry、sensor models 與真 PACMod driver。

本文件是研究與可執行開發範圍，不代表上述 PACMod、rolling scan 或校正系統已完成。
