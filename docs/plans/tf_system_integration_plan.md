# GEM e6 TF、感測器命名與系統整合計畫

修訂日期：2026-11-01（America/Los_Angeles）
狀態：採用一套以 GEM e6 為骨架的 canonical operational TF graph，模擬與實車共用 `base_link` 語意、active sensor frame IDs 與其 parentage；Gazebo 可在同一棵樹上附加車身、視覺或明確標記的 legacy sensor frames。本輪已將 E2 衍生 URDF 的模擬 base、主要 sensor frames 與 runtime consumers 遷移到 canonical graph；E2 body/dynamics 仍是模擬 proxy，sensor mount 數值只列為 simulation nominal。靜態與 runtime validation 尚待完成；E6 實車的 wheelbase 年份、sensor inventory、實際 mount、driver 和 clock 仍待核實。此模擬 URDF 不是實車 vehicle description，vehicle mode 不得載入它或其 nominal transforms。

## 1. 範圍、已知條件與待確認事項

本計畫以 GEM e6 global mapping 為主，同時保留之後加入 local obstacle avoidance 的介面。目標硬體包含：三顆共用剛性支架的 Livox Horizon、一顆 Velodyne VLP-16、六顆共用水平支架的 AVT Mako G-319、RealSense（使用內建 gyro/accelerometer）和 RTK GNSS。Velodyne 及 camera 現場序號／安裝仍須 inventory 驗證；此輪先依使用者明確點名將 VLP-16 納入 target profile。RealSense 的 ROS node、topic 和 TF 名稱統一簡化為 `realsense`，不把型號塞進名稱。主 estimator 仍以 RealSense IMU 為唯一初始 IMU；Livox Horizon 的內建 IMU 暫不納入 operational TF/topic contract。

模擬與實車各自只啟動一棵 operational TF graph，並共用相同的 `base_link` 與 sensor contract。Gazebo 和 vehicle bringup 可選擇不同的 transform 數值來源：模擬使用可追溯且明確標示為 nominal 的 E2-derived seed；實車只接受經量測、附校正證據並通過 readiness gate 的 E6 values。模擬可在 canonical graph 內附加車身／渲染／明確標記為 legacy 的模擬 sensor links；不另立 E2 root、不複製 operational sensor frames，也不允許同時啟動兩個 graph。任何 simulation nominal value 都不得用於實車 bringup 或宣稱已完成感測器校正。

圖面只當安裝位置的初步線索，不用它決定方向或 TF 幾何。依本輪要求查核實際產品文件：Livox Horizon point cloud 與 IMU 有不同座標原點；Mako G-319 可用 PTP/ToE 的能力受 firmware 版本影響；RealSense wrapper 可按 `camera_name` 產生 frame prefix；VLP-16 手冊定義的量測原點與 ROS driver frame convention 不同。實作前仍要逐台讀取型號、serial/firmware、安裝方向和 driver 輸出，不能只從示意圖猜位置。

三顆 Livox Horizon 的 logical IDs 改為 `livox_fl/fc/fr`，TF links 改為 `livox_fl_link/livox_fc_link/livox_fr_link`。三顆相對 `livox_mount_link` 的 x、z 共用同一值，y 各自不同；各機的 orientation 仍獨立量測。六顆 AVT 共用同一個剛性水平支架且 mount Z 相同，改用 `avt_cam_fl/fr/cl/cr/rl/rr`（Front/Center/Rear × Left/Right）；支架座標定名 `top_sensor_rig_link`。Velodyne VLP-16 與車載 RTK GNSS 的 `velodyne_link`、`gnss_main_link`／可選 `gnss_slave_link` 也掛在此 rig 下，但各自的 x/y/z 與方向都相對 rig 獨立量測，不能套用 AVT 相機的共同高度約束。Livox mount 與 top sensor rig 是兩個可量測 datum；下方目標樹先將它們各自連到 `base_link`，表示目前尚未量定兩支架間的機械關係。P0 若確認兩者是同一剛性總成，Xacro 應按實物把其中一個 datum 設為另一個的固定子-frame，只校正一次總成到車體的外參，避免重複建模同一支架。Mako G-319 官方規格為 2064×1544、全球快門、最高 37 fps、GigE/PoE；PTP/ToE 支援與 firmware 版號需逐台核實。型號/Mono-Color variant 仍從每台標籤和 serial 盤點確認。[Mako G-319 產品規格](https://www.alliedvision.com/en/products/area-scan-cameras/mako/mako/view/1051)、[Mako technical documentation](https://www.alliedvision.com/en/support/camera-documentation/area-scan-cameras-documentation/mako-documentation)

`sensor_kit_link` 改名為 `livox_mount_link`，專指三顆 Horizon 共用支架的量測基準。AVT、VLP-16 和車載 GNSS 所在的上層感測器支架 datum 命名為 `top_sensor_rig_link`；Velodyne 與 GNSS 是它的子 frame，各自的安裝偏移獨立校正。下方目標樹暫將 `livox_mount_link` 和 `top_sensor_rig_link` 各自固定連到 `base_link`，避免在未量定前假設兩支架的父子關係；若 P0 確認兩者為同一剛性總成，依實物將其中一個 datum 改為另一個的固定子-frame，僅發布一次總成到車體的外參。`lidar_top_link` 是前版通用佔位名稱，從目標樹移除；Velodyne VLP-16 的 TF frame 定為 `velodyne_link`。

## 2. 推薦 TF tree

車身軸遵循 REP-103：x 向車頭、y 向車輛左側、z 向上。兩種模式共用 `base_link`，定在後軸中心的地面投影；E6 實車的 datum 仍須量測確認。模擬遷移時把原 E2 chassis origin 改成 `base_chassis_link` 子 frame，保留舊 mesh 與 joint 相對幾何，再把 odometry、Nav2、sensor mounts 改接至 canonical base。camera 左右皆以「坐在駕駛座、朝車頭看」的車身方向定義，不依照片的頁面左右判斷。

```text
earth                                             選用：需要 GNSS 地理座標／跨地圖對齊時
└── map                                           全域地圖；SLAM、loop closure、全域定位
    └── odom                                      局部連續座標；允許長期漂移
        └── base_link                             後軸中心地面投影；x 前、y 左、z 上
            ├── base_chassis_link                模擬 E2 車殼／物理幾何 datum；vehicle description 要使用實測幾何
            ├── livox_mount_link                  三顆 Horizon 共用支架 datum
            │   ├── livox_fl_link                 x,z 共用；y 獨立量測
            │   ├── livox_fc_link                 x,z 共用；y 獨立量測
            │   └── livox_fr_link                 x,z 共用；y 獨立量測
            ├── top_sensor_rig_link               AVT、VLP-16、GNSS 的支架 datum
            │   ├── avt_cam_fl_link
            │   │   └── avt_cam_fl_optical_frame
            │   ├── avt_cam_fr_link
            │   │   └── avt_cam_fr_optical_frame
            │   ├── avt_cam_cl_link
            │   │   └── avt_cam_cl_optical_frame
            │   ├── avt_cam_cr_link
            │   │   └── avt_cam_cr_optical_frame
            │   ├── avt_cam_rl_link
            │   │   └── avt_cam_rl_optical_frame
            │   ├── avt_cam_rr_link
            │   │   └── avt_cam_rr_optical_frame
            │   ├── velodyne_link                  VLP-16 ROS point-cloud frame
            │   ├── gnss_main_link                 RTK main antenna phase center
            │   └── gnss_slave_link                optional second vehicle antenna phase center
            └── realsense_link                     RealSense left-IR origin / wrapper root
                └── RealSense stream and IMU frames (discovered from selected wrapper)
```

這個 graph 不含 Livox 內建 IMU frame；只有在 driver spike 確認 topic、座標原點與方向後，才另行擴充。

`base_chassis_link` 是 simulator 的附加幾何 frame，不是 Nav2 base 或 sensor calibration datum；本輪由舊 E2 車殼 origin 推導為 `base_link→base_chassis_link=[0.87, 0, 0.44]`。實車 description 若要使用它，必須用 E6 車體 CAD/量測數值另行定義，不可複用此 simulation transform。

`livox_mount_link` 和 `top_sensor_rig_link` 是兩個描述支架 datum 的 frame。Livox 三顆的 x、z 由共同支架參數提供，僅 y 按 fl/fc/fr 各自設定；每台的 roll/pitch/yaw 依真實安裝方向量測。六顆 AVT 的安裝/光學中心高度依使用者確認為同一高度；Xacro 以 `top_sensor_rig_link` 表達共同 mount Z datum，六個 camera link 相對 rig 的 `z=0`，各自只量測 x/y 與方向。若支架與相機外殼間有固定 Z offset，依相機孔位/CAD 一次納入，不可改成六個互不一致的 mount Z。`velodyne_link`、`gnss_main_link` 和可選的 `gnss_slave_link` 雖同樣是 `top_sensor_rig_link` 的子 frame，其 x/y/z 和 roll/pitch/yaw 必須按各自實體位置獨立量測。camera body frame 遵循 REP-103，optical frame 以零平移、標準軸轉換接在 camera body frame 下。

每顆 AVT 的 `*_link` 是相機安裝方向的 ROS body frame；`*_optical_frame` 遵循 camera optical 軸（x 右、y 下、z 朝鏡頭），Image 和 CameraInfo 的 `header.frame_id` 使用 optical frame。命名意義：FL/FR=前左/前右、CL/CR=中左/中右、RL/RR=後左/後右；全部以車身前進方向定義，並以 serial 綁定正式名稱。

RealSense wrapper 的 `camera_name` 設為 `realsense`，root/frame IDs 便使用簡潔的 `realsense_*` prefix；其 root link 原點定義在左 IR (`infra1`) 位置，並由 wrapper 發布內部 sensor transforms。建議 `robot_state_publisher` 只發布 `base_link → realsense_link`，wrapper 擁有 root 以下的 stream transforms；啟動後用實際 TF graph/message headers 凍結 exact child names。[RealSense ROS frame 與 TF 說明](https://github.com/realsenseai/realsense-ros)

### 從現有模擬樹遷移

模擬 URDF 的根 `base_link` 現在代表後軸地面投影；舊 E2 車身 origin 保存在 `base_chassis_link`，世界 spawn 做相應平移以保留舊車身與場景的相對位置。輪速 Odometry child、動態 `odom→base_link`、Nav2、obstacle projection、RViz、vehicle-control command frame 與 Gazebo ground-truth evaluation frame 已對齊 `base_link`。舊獨立 E2 TF frame 已移除。攝影機、RealSense IMU 與 VLP-16 模擬 frame 依 [`simulation_nominal_transforms.yaml`](../../config/e6/simulation_nominal_transforms.yaml) 使用 nominal 值；legacy NavSat 僅供舊模擬保留，明確排除於 E6 GNSS contract。這些 source 改動尚未經 ROS/Xacro build 或 Gazebo runtime 驗證。

## 3. Topic、frame 與設備命名合約

Topic 用 namespace 分設備，frame ID 不加開頭斜線。`PointCloud2.header.frame_id` 必須等於表中 frame。位置名稱描述車上位置；serial、IP、driver profile 和 calibration ID 放入 inventory/config，不塞進 frame 名稱。

### 三顆 Livox

| 設備／ROS namespace | canonical topic | message `frame_id` | 備註 |
|---|---|---|---|
| `livox_fl` | `/sensors/lidars/livox_fl/points` | `livox_fl_link` | `livox_mount_link` 子框架；x/z 共用，y 獨立 |
| `livox_fc` | `/sensors/lidars/livox_fc/points` | `livox_fc_link` | mapping 單 LiDAR baseline 候選 |
| `livox_fr` | `/sensors/lidars/livox_fr/points` | `livox_fr_link` | `livox_mount_link` 子框架；x/z 共用，y 獨立 |

### Velodyne VLP-16

| 設備／ROS namespace | canonical topic | message `frame_id` | 備註 |
|---|---|---|---|
| `velodyne_vlp16` | `/sensors/lidars/velodyne_vlp16/points` | `velodyne_link` | `velodyne_pointcloud` 由 raw packets 解碼；設備安裝尚待現場確認 |
| `velodyne_vlp16` | `/sensors/lidars/velodyne_vlp16/packets` | packet header frame 依 driver | raw packets 保留以供診斷與重播 |

ROS 2 Velodyne driver 對 VLP-16 設 `model:=VLP16`，packet driver 的 `frame_id` 設成 `velodyne_link`；RPM 要和雷達 web interface 實際設定一致。`velodyne_pointcloud` 使用 `VLP16db.yaml`，預設空的 `target_frame` 會沿用 packet frame；除非刻意轉換 cloud，先保留空值以避免額外 TF 轉換。官方預設 topics 是 `velodyne_packets`/`velodyne_points`，launch remap 為 canonical names。只有 VLP-16 已接上 GPS PPS/NMEA input 時才設 `gps_time:=true`，否則 driver 用 local time。[Velodyne ROS 2 driver](https://github.com/ros-drivers/velodyne/tree/ros2)、[VLP-16 pointcloud parameters](https://github.com/ros-drivers/velodyne/blob/ros2/velodyne_pointcloud/config/VLP16-velodyne_transform_node-params.yaml)

VLP-16 手冊的 sensor measurement origin 位於 sensor base 上方 37.7 mm，不能把支架板面直接當 LiDAR 原點。手冊 azimuth convention 與 ROS driver 的 REP-103 點雲軸向不同；ROS driver maintainer 說明其點雲採標準 ROS 軸向，因此先確認所鎖定版本的輸出，再由 TF 表達 driver frame 到車體的實際 mount pose，不要再重複旋轉已轉成 ROS axes 的 cloud。[VLP-16 User Manual](https://data.ouster.io/downloads/velodyne/user-manual/vlp-16-user-manual-revf.pdf)、[ROS Velodyne axis convention](https://github.com/ros-drivers/velodyne/issues/71)

初期保持三條獨立點雲 stream，不先把 clouds 無條件 concat。記錄各裝置的型號、broadcast code/serial、firmware、driver、point-time schema、publish rate、clock 狀態和 QoS。若確認是 Horizon，Livox ROS 2 driver 官方舊版 repo 列有 Horizon 支援和 Humble build instructions；`livox_ros_driver2` 現行 README 的範例集中於 HAP/MID360，不能直接假設它支援 Horizon。Driver 版本需在 Humble 環境做編譯和真機連線 spike。[Livox ROS 2 Horizon driver](https://github.com/Livox-SDK/livox_ros2_driver)、[Livox ROS Driver 2 topic/schema](https://github.com/Livox-SDK/livox_ros_driver2)

Livox 每顆需唯一 `msg_frame_id` 和 topic，按本契約分別設 `livox_fl/fc/fr`，frame IDs 分別為 `livox_fl_link/livox_fc_link/livox_fr_link`。driver 的多機制若會把多個 LiDAR 合到相同 topic，就需選 per-device publishing option、各自 driver/config 或 namespace/remap，並以實際 `ros2 topic echo` 的 `header.frame_id` 驗證。保留含逐點時間的原始格式供 LIO/deskew 使用；另提供標準 PointCloud2 給 Nav2/通用消費者時，不可丟掉原始同步資料或誤解 point time 單位。Livox driver2 PointXYZRTLT 格式有逐點 timestamp 欄位；實際 Horizon driver/輸出格式須按所鎖定版本確認。[Livox driver2 message fields](https://github.com/Livox-SDK/livox_ros_driver2/blob/master/README.md)

Horizon 有 built-in IMU，且手冊定義其 IMU 與 point-cloud frame 是不同座標原點；IMU origin 在點雲座標下的平移為 `(-0.05512, -0.02226, +0.02970) m`。目前主估計器先只使用 RealSense IMU，因此不把 Livox IMUs 加到 operational TF/estimator；若之後要用，依 Horizon 手冊/driver 對應點雲 frame 建立 IMU child frame，orientation 亦按手冊軸定義和實測驗證，不假設兩個 frame 重合。[Horizon manual, coordinates and IMU](https://www.livoxtech.com/3296f540ecf5458a8829e01cf429798e/assets/horizon/Livox%20Horizon%20user%20manual%20v1.0.pdf)

### 六顆 AVT cameras

六顆 AVT 共用 `top_sensor_rig_link`，將它設在可重複量測的支架 datum。Xacro 對六顆相機只定義一個共同安裝高度 `avt_camera_mount_z`；每個 camera link 相對 rig 的 z 固定為 0，x/y 依 FL/FR/CL/CR/RL/RR 的實際安裝位置分別量測，方向則逐顆量測。VLP-16 和 GNSS 也掛在 rig 下，但各有獨立的 3D 外參，不受相機共同 z 約束。這表示六個相機安裝基準高度一致，不代表六台鏡頭視線方向、x/y 或 optical center 必然相同。

| camera ID | optical `frame_id` | image topic | CameraInfo topic |
|---|---|---|---|
| `avt_cam_fl` | `avt_cam_fl_optical_frame` | `/sensors/cameras/avt_cam_fl/image_raw` | `/sensors/cameras/avt_cam_fl/camera_info` |
| `avt_cam_fr` | `avt_cam_fr_optical_frame` | `/sensors/cameras/avt_cam_fr/image_raw` | `/sensors/cameras/avt_cam_fr/camera_info` |
| `avt_cam_cl` | `avt_cam_cl_optical_frame` | `/sensors/cameras/avt_cam_cl/image_raw` | `/sensors/cameras/avt_cam_cl/camera_info` |
| `avt_cam_cr` | `avt_cam_cr_optical_frame` | `/sensors/cameras/avt_cam_cr/image_raw` | `/sensors/cameras/avt_cam_cr/camera_info` |
| `avt_cam_rl` | `avt_cam_rl_optical_frame` | `/sensors/cameras/avt_cam_rl/image_raw` | `/sensors/cameras/avt_cam_rl/camera_info` |
| `avt_cam_rr` | `avt_cam_rr_optical_frame` | `/sensors/cameras/avt_cam_rr/image_raw` | `/sensors/cameras/avt_cam_rr/camera_info` |

AVT driver instance 以唯一 serial 選相機，driver namespace 用穩定的 logical ID，再 remap 到表中的 canonical topics。每顆保存自己的 GenICam settings 和 `camera_info_url`；內參按 serial、pixel format、ROI、resolution 和 focus/mode 校正。Image 和配對的 CameraInfo 使用同一個 optical frame。若有相機是 stereo module，才額外依實際左右目建立各自 optical frames 和 baseline；不從六個獨立機殼推定 stereo pair。

Allied Vision Vimba X ROS 2 driver 支援 `camera_id`（含 serial/IP）、`camera_frame_id`、`camera_info_url`、camera timestamp/ROS time 選擇；README 明列的測試組合是 ROS 2 Jazzy、Ubuntu 24.04 和 Alvium，不是本專案 Humble。Vimba X SDK 相容文件談到 GenICam/Mako 功能，但沒有證明 G-319 可由此 ROS 2 driver 在 Humble 直接串流。故 Mako G-319 + Vimba X ROS 2 + Humble 必須先實測，不視為已保證組合；driver 預設 PID namespace 需 remap 才能取得固定 topic 名稱。[Vimba X ROS 2 driver](https://github.com/alliedvision/vimbax_ros2_driver)、[Vimba X SDK compatibility](https://docs.alliedvision.com/vimba_x/compatibility.html)

若六顆實際都是 G-319，在最高解析度/37 fps 下 Mono8 原始 image payload 約 5.66 Gbit/s aggregate（未含 Ethernet/ROS overhead），每台 1GbE link 單是影像 payload 已約 943 Mbit/s；RGB8 每台則超過 1GbE。理想網路是每台 GigE camera 有獨立 full-duplex camera port、PTP-aware managed switch、足夠快的 uplink（全速 Mono8 aggregate 至少以 10GbE 規劃並實測），車載電腦有對應 NIC/PCIe bandwidth；若 NIC、storage 或 DDS 預算不足就降低 FPS/ROI 或選 Mono/Bayer format，並量測丟幀率和 latency。這是 conditional capacity estimate，不能當成已知實際相機設定。

### RealSense 相機與內建 IMU

以 `camera_name:=realsense`、`base_frame_id:=link` 令 wrapper root 為 `realsense_link`；建議 namespace `/sensors`，以邏輯名稱建立固定 topics。實際設備型號保存在 hardware inventory，不放在 ROS topic 或 frame ID。

| stream | canonical topic(s) | frame／備註 |
|---|---|---|
| color | `/sensors/realsense/color/image_raw`, `/sensors/realsense/color/camera_info` | wrapper 實際 optical frame，確認為 `realsense_color_optical_frame` 後凍結 |
| depth | `/sensors/realsense/depth/image_rect_raw`, `/sensors/realsense/depth/camera_info` | wrapper 實際 optical frame；保留 depth scale/encoding |
| left/right IR（需要時） | `/sensors/realsense/infra1/image_rect_raw`, `/sensors/realsense/infra2/image_rect_raw` | wrapper 對應 optical frames |
| raw gyro | `/sensors/realsense/gyro/sample` | `sensor_msgs/Imu` 只填角速度相關欄位 |
| raw accel | `/sensors/realsense/accel/sample` | `sensor_msgs/Imu` 只填線加速度相關欄位 |
| combined IMU | `/sensors/realsense/imu` | `enable_gyro:=true`, `enable_accel:=true`, `unite_imu_method:=2`；線性插值 accel 到 gyro stamp |

RealSense wrapper 把 gyro 和 accel 當成兩個 `sensor_msgs/Imu` stream；合併 topic 不代表有姿態融合，orientation 仍可能未知（covariance 的 unknown 標記須保留）。第一個 estimator 用 combined IMU 時，另外錄 raw gyro/accel 供診斷。Wrapper 的 `camera_name` 會影響所發佈的 frame IDs；其 body axes 為 x 前、y 左、z 上，optical axes 為 x 右、y 下、z 前；root origin 在左 IR (`infra1`) 位置，wrapper 提供 streams 到 camera root 的內部變換。建議 wrapper 唯一擁有 root 以下的廠商內部 TF，`robot_state_publisher` 只擁有 `base_link → realsense_link`。啟動後由實際 graph/headers 凍結名稱。若 driver 自帶內部 TF，禁用 URDF 中同一組 internal transforms；只選一個 authority。[RealSense ROS frames/TF](https://github.com/realsenseai/realsense-ros)

### RTK GNSS

| 介面 | 建議名稱 | TF 要求 |
|---|---|---|
| 車載主天線位置 | `/sensors/gnss/rtk/fix` (`sensor_msgs/NavSatFix`) | `header.frame_id=gnss_main_link`，若 driver 消息語意支援 |
| 雙天線航向／baseline | `/sensors/gnss/rtk/heading`（依 driver 明確的 message type） | 方向參考點和 `main→slave` baseline 在 contract 中定義 |
| fix/衛星/RTK 狀態 | `/sensors/gnss/rtk/status` 或 diagnostics | quality state 不假裝成 NavSatStatus enum |

TF 描述的是天線 phase center，不是 receiver 電路板。若雙天線 heading receiver 的主副天線都裝在車上，分別量測 phase center，建立 `gnss_main_link` 和 `gnss_slave_link`；如果車上只有一副天線，只留 `gnss_main_link`。串列／USB receiver adapter、收訊板和天線線纜不產生 TF。若所謂母子是 base/rover 兩台實體接收器，固定 base station 不掛在車體下；只在有地理座標需求時在 `earth/map` 註記其站點。接收器型號、板卡拓撲與實際 antenna 數仍屬 P0 待確認。

## 4. TF 發布權與全域／局部資料流

| TF edge | 唯一 owner | 規則 |
|---|---|---|
| `base_link → livox_mount_link → Livox frames` | `robot_state_publisher` | Xacro 讀一份 versioned calibration；三顆各自一條固定邊 |
| `base_link → top_sensor_rig_link → six AVT links → optical frames` | `robot_state_publisher` | AVT 共用 mount Z；各 camera x/y/RPY 與 optical-axis rotation 明確定義 |
| `top_sensor_rig_link → velodyne_link` | `robot_state_publisher` | VLP-16 外參獨立量測，指向 ROS point-cloud frame並包含 sensor origin 高度定義 |
| `base_link → realsense_link` | `robot_state_publisher` | RealSense 左 IR/wrapper root 的 mount 外參；logical name 不含型號 |
| `realsense_link` → streams/IMU frames | RealSense wrapper **或** `robot_state_publisher` | 只擇一；預設沿用 wrapper 的 factory/internal transforms |
| `top_sensor_rig_link → GNSS phase-center frames` | `robot_state_publisher` | 主/副天線各自量測；adapter/receiver board 不造 frame |
| `odom → base_link` | 一個 local state estimator | 輪速、RealSense IMU 和選定 LIO 輸入；連續、無跳變 |
| `map → odom` | 一個 SLAM/localization component | loop closure/global correction 放在此 edge；不得同時開兩個 publisher |
| `earth → map` | 地理參照元件，選用 | 固定 datum/projection；平面本地建圖不需要 |

URDF/Xacro 描述車輛有哪些 links/joints 及固定幾何；`robot_state_publisher` 把固定 joints 轉為 `/tf_static`，可動 joints 依 joint states 發布 `/tf`。它不應描述會隨里程計、SLAM 或重定位改變的 `odom → base_link`、`map → odom`；這兩條由 runtime estimator/localization 發布。這樣 URDF 是機械與感測器安裝幾何的定義，TF 是系統執行時供各節點查詢的座標關係。[robot_state_publisher](https://github.com/ros/robot_state_publisher)

Global mapping 與 Nav2 使用共同的 `map → odom → base_link → sensor` tree。Local costmap 建議 `global_frame: odom`、rolling window，以近期 LiDAR PointCloud2 做 marking/clearing；global costmap 用 `global_frame: map`，以載入或 SLAM 輸出的 2D occupancy map 做長距離規劃。SLAM/LIO 若輸出 3D map，另設明確的 3D→2D projection/layer；TF 本身不會將點雲轉成導航地圖。不要把動態障礙物直接寫入持久 global map。

Local estimator 持續發布平順的 `odom → base_link`。SLAM/localization 唯一負責 global correction `map → odom`：mapping 模式由 SLAM 擁有；載入既有地圖時由定位元件擁有；兩者不能同時發布。若演算法只輸出 `map → base_link`，adapter 必須以同一時間戳的 local odometry 計算：

```text
T_map_odom(t) = T_map_base(t) × inverse(T_odom_base(t))
```

loop closure 或重新定位可以改變 `map → odom`，但不得讓 local `odom → base_link` 跳變。Nav2 的 global planner 使用 `map` 和全域 2D map；local obstacle controller 使用連續 `odom` costmap 和有時效的感測器 observations。若切換 mapping/localization backend，明確停掉舊的 `map → odom` publisher 再切換新 owner。

建圖 baseline 建議先比較已確認連線的 `velodyne_vlp16` 和 `livox_fc` 單一 LiDAR 路徑：VLP-16 有完整旋轉掃描與成熟 ROS 2 解碼鏈，適合作為參考 baseline；Horizon 若 driver 保留逐點時間且 Humble spike 通過，則以 FC 做 Livox/LIO baseline。採用哪一顆須在 P0 看實車存在、driver、point-time schema、視場和 bag 結果決定，不因「target profile」假設 VLP 一定已裝車。輪速和 RealSense IMU 作 local motion aiding；校正通過後依序增加其餘 Livox。local obstacle costmap 可另外接低延遲且已校正的 VLP-16、三顆 Livox clouds。不要在 concat 時丟棄來源 ID、每點時間或各感測器時間語意。

## 5. TF 與感測器校正工作流

1. **定義車體基準。** 實測後軸中心與路面投影，記錄 `base_link` 到車身/車架的高度、車寬、軸距、輪距、Nav2 footprint。測量時標出車頭方向和右手座標軸。
2. **定義兩種支架 datum。** 分別在 `livox_mount_link` 和 `top_sensor_rig_link` 選可重複量測的固定孔/定位面，測量它們相對 `base_link` 的 pose。Livox 三顆相對支架的 x、z 共用值，y 逐顆量測且 orientation 分別量測；AVT 六個相機的 mount z 必須同值，x/y 和視線方向按 FL/FR/CL/CR/RL/RR 分別量測；VLP-16 與 GNSS phase center 的完整外參各自相對 top rig 量測。
3. **逐顆定 camera。** 依 serial 對照 `avt_cam_fl/fr/cl/cr/rl/rr`，校驗位置、視線方向、內參、畸變、曝光模式和 optical frame；每個 resolution/ROI/calibration 都綁定 serial 和版本。Image/CameraInfo 的 `header.frame_id` 必須是對應 `*_optical_frame`，且 TF 應可在量測 timestamp 查到。
4. **VLP-16 mount。** 測量 mounting surface 到資料原點的變換；手冊給出資料原點在 sensor base 上方 37.7 mm。確認 `VLP16db.yaml`/設備校正及 official driver 的 REP-103 軸轉換後，從 `top_sensor_rig_link` 到 `velodyne_link` 定外參，不要把 manufacturer-to-ROS axis change 又套一次。
5. **RealSense mount 和內部校正。** 確認 wrapper root frame 的實際原點（ROS wrapper 預設 camera link 在左 IR 原點），量測它到 `base_link`；保留原廠 stream extrinsics，使用 wrapper TF，檢查 depth scale/平面誤差和 IMU 軸向。若重裝、撞擊或更換支架，重做外參驗證。
6. **LiDAR-LiDAR 與 LiDAR-camera。** 先用 CAD/尺規提供 mount 初值，再用多方向平面和共同可見標靶驗證；沿車輛可能的三軸運動取得足夠激發。車輛只有平面直行資料時，不宣稱 6-DoF 可觀測。LiDAR-camera 每顆相機都獨立估算或以驗證過的共同支架約束，不從一顆外推六顆。
7. **GNSS lever arm。** 從 `top_sensor_rig_link` 分別量測至主／副天線 phase center，透過 rig-to-base 外參得到車體 lever arm。若雙天線，用 `gnss_main_link`/`gnss_slave_link` 的位置和 baseline 朝向校驗 heading convention、ENU/NED、角度正負與 receiver 輸出 frame。
8. **外參與時間 offset 分開管理。** 靜態 TF 只描述空間位姿；sensor clock offset、曝光中點、LiDAR scan 起點/逐點時間寫入 clock/timestamp config，不能用移動 TF 假修時間差。
9. **單一 frame contract，依 mode 選一個數值來源。** `config/e6/sensor_inventory.csv` 綁定 sensor ID 與硬體 serial/driver/topic；`config/e6/sensors_calibration.yaml` 保存實車外參與校正證據；`config/e6/simulation_nominal_transforms.yaml` 保存 E2-derived simulation seeds。兩份幾何資料使用相同 canonical frame IDs/parent topology，但 runtime 只選目前 mode 的一份來源；vehicle mode 永不讀 simulation seed。衍生 Xacro/launch/driver config 不得另存互相漂移的外參。實車記錄 raw bag、工具/commit、initial guess、估計結果與 held-out 殘差，不用模擬 truth 補真車缺值。

沒有一組適用所有車輛/演算法的固定公差。先依 global map resolution、local collision margin、速度和量測距離推導可接受位置/角度/時間誤差；相機用 held-out reprojection/edge alignment，LiDAR 用多平面/重疊地物殘差，時間用共同 flash/trigger event 或移動邊緣估 offset/jitter，GNSS 用測量基準/天線 baseline。報告重複量測與退化方向，避免只憑 RViz 看起來重合就驗收。

## 6. 時間同步與 timestamp 合約

**同步時鐘、同步拍攝、同步發布是三件事。** PTP 讓設備時鐘對同一時間源；hardware trigger/action command 控制影像實際曝光時刻；ROS header 應表示量測時間而非資料抵達 ROS 的時間。解決 PTP 不代表六台 camera 同一瞬間曝光，也不代表 LiDAR point cloud 已被 motion compensated。

### 建議硬體方案

- 若三顆 Livox 確認為 Horizon 且鎖定的 firmware/driver 支援，讓 Mako G-319 與 Horizon 使用同一 IEEE 1588 PTP grandmaster 是優先評估方案。Horizon manual 確認支援 PTPv2、PPS、GPS (PPS+UTC)；Mako G-319 也支援 PTP 和 Trigger over Ethernet，但官方手冊指出該能力對 G-319 需 firmware `01.54.21000` 或更新且功能啟用，須逐台盤點。配置相同 PTP domain、單一 grandmaster、PTP-aware network，監測各設備 sync lock/offset/path delay 及 host clock。[Horizon manual](https://www.livoxtech.com/3296f540ecf5458a8829e01cf429798e/assets/horizon/Livox%20Horizon%20user%20manual%20v1.0.pdf)、[Mako G-319 datasheet](https://www.alliedvision.com/assets/support/Camera-Documentation/Allied-Vision/Cameras/Mako/Data-Sheets/Mako_G-319_DataSheet_en.pdf)、[Mako documentation and firmware notes](https://www.alliedvision.com/en/support/camera-documentation/area-scan-cameras-documentation/mako-documentation)
- 以 host NIC PHC 參與 PTP，同時將 Linux system clock 對齊到該 PHC（常見 `ptp4l` + `phc2sys`）；ROS 2 `header.stamp`、TF、bag 及 estimator 使用同一 ROS/system-time epoch。確認 driver 對硬體 timestamp 的 epoch/unit 轉換正確，不能單看 PTP service 顯示 locked 就當 ROS topic stamp 同步完成。
- 若 RTK GNSS receiver 或專用 clock unit 有可靠 PPS/UTC output，理想上以該來源 discipline PTP Grandmaster，讓設備 clock 有一致 UTC epoch；若沒有可用 PPS，仍可採單一 PTP GM 做車內相對同步，但 GNSS datum/absolute time 的關係須另外驗證。
- AVT 使用 camera hardware timestamp，確認其時間域及 driver 到 ROS epoch 的轉換；驗證 Image header 與 `camera_info` 的 stamp/frame。若六個 global shutter camera 必須同一曝光時刻，使用共用硬體 trigger 或已啟用之 ToE action command，先核對 firmware/features、電氣介面和 Vimba driver 行為，再用共同 LED/flash 量 trigger-to-exposure skew。PTP 對時本身不代表曝光同時。
- VLP-16 要達到 GNSS 時間需向 interface box 提供 PPS 加 NMEA UTC（手冊列 GPRMC/GPGGA），確認 PPS 電平/極性/時序及實體接線；driver 只有在 GPS 真正接至雷達時才設 `gps_time:=true`。無 GPS input 時 driver 使用 local time，需另做 host-clock offset bridge，不能把其 stamp 當 UTC。[VLP-16 manual](https://data.ouster.io/downloads/velodyne/user-manual/vlp-16-user-manual-revf.pdf)、[ROS 2 driver GPS parameter](https://github.com/ros-drivers/velodyne/blob/ros2/velodyne_driver/README.md)
- RealSense 以 device timestamps/global-time behavior 為主，使用 `enable_sync:=true` 對 color/depth/IR 取最近的 frameset；gyro/accel 用 wrapper `unite_imu_method:=2` 以 gyro timestamp 插值。這只整理 RealSense 自身的 streams，不是 AVT/Livox/VLP-16 間的硬體同步。把 RealSense device/global timestamp 和 Linux/ROS clock 的 offset 實測後再融合。[RealSense timestamp domain](https://github.com/realsenseai/librealsense/blob/master/include/librealsense2/h/rs_frame.h)、[RealSense frame sync](https://github.com/realsenseai/librealsense/blob/master/doc/frame_lifetime.md)
- Livox Horizon 若無法使用 PTP，依已鎖定的 firmware/driver 接同一 GNSS UTC + PPS 時間源；具體 PPS cable、UTC message 和 priority 依 Horizon manual/SDK 驗證。先選一種已監測的共用時鐘來源，不要讓設備默默選不同源。[Livox ROS 2 Horizon driver](https://github.com/Livox-SDK/livox_ros2_driver)
- 外部 PPS/trigger 應使用規格相符的 fan-out、隔離或 level conversion；先對照 VLP-16/Horizon/G-319 electrical manuals，不能直接將 receiver output 並接多台設備。D400 external sync 僅在日後確有 camera/IMU external-sync 要求時才評估，需先檢查電氣 input/output 方向；不作為第一階段跨品牌觸發假設。[D400 datasheet](https://dev.realsenseai.com/download/42003/)

### 每個 ROS message 的時間規則

- `header.stamp` 是 capture/exposure/measurement time；保留 sensor 原始 timestamp、timestamp domain/source、packet receive time（diagnostic）和轉換後 ROS time 的對照。
- Livox PointCloud2 記錄一個 message stamp 的定義（first point、scan reference 或 driver convention）及 per-point time 欄位、單位、相對/絕對時間語意。三顆各自 deskew 後才合併。
- VLP-16 ROS 2 pointcloud converter 的 XYZIRT profile 有 float32 `time` 欄位；目前 driver code 以 `scan_start_time` 為基準，將 packet stamp 差與逐點 firing offset 組合成點時間。鎖定版本後仍需量測/檢查欄位單位與 stamp convention，記錄 RPM、GPS/local time source 和 driver revision；不要只同步 ROS publish times 就宣稱具備 scan deskew。[Velodyne XYZIRT implementation](https://github.com/ros-drivers/velodyne/blob/ros2/velodyne_pointcloud/src/lib/rawdata.cpp)、[XYZIRT fields](https://github.com/ros-drivers/velodyne/blob/ros2/velodyne_pointcloud/src/lib/pointcloudXYZIRT.cpp)
- AVT 曝光採中點或廠商 timestamp 的哪種定義要有明確結論，保留 exposure duration metadata；如用 PTP scheduled trigger，也記錄 trigger command/event。
- RealSense accel/gyro 原始 topic stamp 保留；combined IMU orientation 不具備融合姿態時保持 unknown covariance，不假裝已輸出 orientation。
- TF 查詢使用 observation timestamp；不能因 extrapolation warning 就在 latest TF 下硬轉舊資料。
- Sim 和 replay 使用唯一 `/clock` source；real mode 不使用 `/clock`/`use_sim_time`。bag 包含 `/tf`, `/tf_static`, sensor streams、odometry、clock status/diagnostics、driver/firmware config manifest。

### 同步驗證與降級

1. 錄製冷啟動、熱機、持續運作和 reconnect 後的 PTP lock/offset、host PHC/system offset、sensor header stamp、到達時間、掉 frame/packet、LiDAR point-time連續性。
2. 同一 PTP network broadcast/action event 或測量 flash/LED 同步事件，估計各影像曝光 skew；移動測試牆面/邊緣以 cross-check camera-to-LiDAR 時間偏移。
3. 由運動預算訂 acceptance：位置誤差約 `v·Δt`，旋轉造成的點位誤差約 `range·ω·Δt`。門檻依車速、LiDAR range、map voxel/resolution 和 obstacle margin 寫入 config，並留出抖動、曝光時間與感測器 latency budget。
4. Clock unlock、stamp 倒退/跳變、sensor 資料過期或 observation-time TF 缺失時，diagnostics 觸發降級：global mapping 停止累積無法 deskew 的資料；local avoidance 將過期 source 判為 stale，依安全策略限制速度或停車，不沿用最後點雲當新資料。

## 7. 分階段 implementation plan

| 階段 | 工作 | 可 review 的產出／下一階段 gate |
|---|---|---|
| P0 — 實車盤點與相容性 spike | 逐台拍 model/serial/firmware；確認 Horizon 型號、三顆 network topology、VLP-16 是否實車存在及 RPM/GPS input、AVT 型號/Mono/Color/鏡頭/firmware、RealSense 型號/serial、GNSS 板/天線數；確認六 camera 的 FL/FR/CL/CR/RL/RR 位置。用 Humble 驗證 Livox、Velodyne 和 Vimba X ROS 2 + G-319 | `sensor_inventory.csv` 綁 serial→logical name→IP/port→topic→frame；driver matrix、clock source 和 bandwidth 預算；未知值明標 pending |
| P1 — 單一 E6 canonical TF 遷移 | 把現有 GEM description rebase 到 E6 `base_link` 後軸地面 datum；E2 chassis 改作 `base_chassis_link`，以同一 frame graph 接上 Livox、AVT、VLP-16、RealSense 和 GNSS contract。模擬載入 nominal seed；vehicle 只載入 validated calibration registry。 | 同一份 robot description/frame ID contract 可供 sim 與 vehicle；每個 mode 僅一個 RSP／TF owner；Odometry `child_frame_id`、動態 TF、Nav2 base frame 一致；vehicle gate 拒絕 simulation nominal 值；舊模型相對幾何不被意外改變 |
| P2 — drivers、topic 與時間 | VLP-16、單顆至三顆 Livox；單顆至六顆 AVT；RealSense streams/IMU；GNSS position/heading/status；QoS、namespace、serial locking；設定 PTP/PPS/trigger/clock conversion | 每 topic 型別/rate/frame/stamp 語意和 latency 可觀測；多裝置無 name collision；driver compatibility 和時間 skew 有報告 |
| P3 — 幾何標定 | 量測車體/kit/mounts；相機 intrinsics；Livox-Livox / LiDAR-camera；RealSense mount、depth/IMU axes；GNSS lever arm/baseline | 一份 calibration YAML 驅動所有靜態 TF；每條路徑可查；held-out 殘差和 uncertainty 符合預先制定門檻 |
| P4 — local state + global mapping | 輪速＋RealSense IMU 建 local `odom→base_link`；通過實車存在與資料品質 gate 後，以 VLP-16 或 Livox FC 建單 LiDAR baseline；再加入其餘 LiDAR、逐點 deskew 和多 LiDAR 對照 | map/odom authority 唯一；loop closure 只影響 map→odom；bag/replay 結果一致；不讀 ground truth |
| P5 — local avoidance / Nav2 | local costmap `odom` rolling window，配置 VLP-16 與 Livox FL/FC/FR PointCloud2 sources、height/range/marking/clearing；global costmap `map`；若 3D map，明確投影 occupancy map | 靜態/動態障礙能 mark/clear；observation time TF 有效；車體 footprint、轉向掃掠和 clearance 已測 |
| P6 — 整車系統驗證 | 同步 fault、camera packet loss、Livox dropouts、RealSense USB reconnect、GPS fix loss、TF age、clock reset、bag replay、長時間/高負載與 Nav2 stop policy | 啟動圖、topic/TF/clock owner 清單可重現；故障會依策略降級，診斷和 bag 足以定位失敗 |

### 理想的系統整合狀態

- 一份可版本控制的 e6 URDF/Xacro + calibration registry 代表真實幾何；每個 ID 綁硬體 serial、mount revision、driver、內外參、timestamp policy 和狀態。
- `robot_state_publisher`/vendor wrapper 各自只負責明確的 TF edges；每個 frame 唯一父節點，`map→odom` 與 `odom→base_link` 單一 authority；整車 TF 在 sensor capture time 可查。
- 全部資料有固定且易懂的 ROS topic contract，serial 只用於選設備，不變動邏輯名稱；Image/CameraInfo/frame、LiDAR cloud/frame、IMU frame/time 語意一致。
- AVT/Livox 共用 PTP Grandmaster；VLP-16 若實車接入，以同一 GNSS-disciplined source 的 PPS+NMEA 對時；若多視角同時觀測必須同曝則再用 trigger/action command；RealSense 以可驗證的 device/global timestamp bridge 到同一 ROS clock。
- mapping/estimation 從少量已驗證 input 增加 sensor；local costmap 使用低延遲近期觀測，global map 保持全域一致且不被短命障礙污染；每次改動都有 rosbag、manifest、TF graph 和精度/延遲報告可回放。

## 8. 驗收清單

- 車體靜態樹只有一條 operational path：`map → odom → base_link → sensor frames`（若使用 georeferencing 再加 `earth → map`）。無迴圈、重複 child、未知 frame、競爭 publisher。
- 每顆 Livox 與 VLP-16 在自己的 topic 發佈，frame ID 各自正確；三個 Livox 和 VLP-16 固定外參可在共同標靶/牆面下對齊。
- 六顆 AVT 的 logical ID/serial/位置表、Image/CameraInfo calibration URL、optical frame ID、解析度/ROI/format/曝光設定一對一。
- RealSense root 與 wrapper children 完整，topic/frame logical names 不含型號，沒有 `robot_state_publisher` 和 wrapper 重複發佈同一 internal edge；raw IMU 與 combined IMU 的軸向、單位、stamp、covariance 已核驗。
- GNSS frame 位於天線 phase center；如有主副天線，TF baseline 和實際 heading reference 相符；adapter/receiver board 不在車身測量 tree 內。
- 同步時鐘、曝光 trigger、ROS header stamp 語意分別有驗證；clock lock 和 offset 退化可診斷；每一筆 mapping/obstacle observation 能在自己的 timestamp 轉到 `odom`/`map`。
- Nav2 local/global frame 分工、3D-to-2D map 輸出、點雲高度、vehicle footprint、障礙物清除/過期策略在靜態和動態場景通過。
- 每次實驗保留 URDF/Xacro、calibration registry、driver/firmware/switch/PTP config、rosbag、TF graph、clock status、run manifest 和 held-out 殘差。

## 9. 研究依據

- [REP-103：ROS 座標軸與 SI 單位](https://www.ros.org/reps/rep-0103.html)；[REP-105：map/odom/base_link 語意](https://www.ros.org/reps/rep-0105.html)
- [Nav2 transforms setup](https://docs.nav2.org/rolling/configuration_and_development/first_time_robot_setup_guide/transformation/setup_transforms.html)：`map→odom→base_link→sensor` 必要路徑與靜態 frame 建議。
- [Nav2 mapping/localization](https://docs.nav2.org/rolling/configuration_and_development/first_time_robot_setup_guide/sensors/mapping_localization/)；[Nav2 costmap configuration](https://docs.nav2.org/rolling/configuration_and_development/configuration_guide/core_servers/costmap_2d/)。
- [RealSense ROS 2 wrapper](https://github.com/realsenseai/realsense-ros)：namespace、frame names、publish_tf、enable_sync、gyro/accel、unite_imu_method。
- [Librealsense timestamp domains](https://github.com/realsenseai/librealsense/blob/master/include/librealsense2/h/rs_frame.h)；[frame sync/lifetime](https://github.com/realsenseai/librealsense/blob/master/doc/frame_lifetime.md)；[D400 series datasheet](https://dev.realsenseai.com/download/42003/)。
- [Livox ROS 2 driver for Horizon](https://github.com/Livox-SDK/livox_ros2_driver)；[Livox driver2 message fields and per-device topics](https://github.com/Livox-SDK/livox_ros_driver2/blob/master/README.md)；[Livox time synchronization manual](https://github.com/Livox-SDK/Livox-SDK/wiki/livox-device-time-synchronization-manual)。
- [Allied Vision Mako G-319](https://www.alliedvision.com/en/products/area-scan-cameras/mako/mako/view/1051)；[Mako documentation and firmware](https://www.alliedvision.com/en/support/camera-documentation/area-scan-cameras-documentation/mako-documentation)；[Vimba X ROS 2 driver](https://github.com/alliedvision/vimbax_ros2_driver)；[Vimba X SDK camera compatibility](https://docs.alliedvision.com/vimba_x/compatibility.html)。
- [Velodyne VLP-16 User Manual](https://data.ouster.io/downloads/velodyne/user-manual/vlp-16-user-manual-revf.pdf)：data origin、native coordinates、PPS+NMEA UTC sync；[ROS 2 Velodyne driver](https://github.com/ros-drivers/velodyne/tree/ros2)：VLP16 model、packet/point cloud、frame ID、RPM 與 GPS-time parameters。
- [Velodyne ROS 2 raw-data decoder](https://github.com/ros-drivers/velodyne/blob/ros2/velodyne_pointcloud/src/lib/rawdata.cpp) 與 [XYZIRT point schema](https://github.com/ros-drivers/velodyne/blob/ros2/velodyne_pointcloud/src/lib/pointcloudXYZIRT.cpp)：per-point `time` 的產生方式與欄位型別。
- [Autoware vehicle/sensor description approach](https://tier4.github.io/autoware-documentation/latest/how-to-guides/integrating-autoware/creating-vehicle-and-sensor-description/creating-vehicle-and-sensor-description/)：以車輛 Xacro、sensor mount 和 calibration 分層管理。
