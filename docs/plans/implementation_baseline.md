# 系統重新審查與本輪實作基準

日期：2026-10-15（America/Los_Angeles）。本文件為下一輪實作的統一基準；平台採 ADR 0002，Jazzy／24.04 提案不再是本輪目標。此前各研究文件保留作來源及後續功能說明。這次完成審查／規格，不冒稱已拆好服務或完成 PACMod。

## 1. 查核結果：事實、決策及未知條件

已直接讀取現有 Compose、Dockerfile、兩個主 launch、bridge、DDS、wheel odometry、Nav2 設定、CI、測試證據及容器 package metadata。

| 項目 | 結果 |
|---|---|
| 容器 OS／CPU／ROS | Ubuntu 22.04.5、x86_64、Humble，實際查核 |
| Gazebo library | libignition-gazebo6 6.18.0，Fortress |
| Nav2 | ros-humble-nav2-bringup 1.1.20 |
| ros_gz | 0.244.26 |
| ign_ros2_control | 0.7.21 |
| PACMod driver | ros-humble-pacmod2 2003.1.1-0jammy，/opt/ros/humble；已安裝但現有 graph 沒有啟動 driver |
| PACMod messages | pacmod2_msgs 1.0.0，/workspace/ros_ws/install；不是將所有套件假定都來自同一 apt release |
| FAST-LIO | 在繼承 workspace install prefix 存在；本輪未確認精確 source revision，未啟動 |
| 現有運作 | sim、Gazebo GUI、RViz 容器運行；Nav2／wheel odometry／直接 Twist adapter 在 graph 中 |
| 已有證據 | 短距離靜態導航、取消／不可達、sensor sanity、靜止bag replay及雙GUI行車；尚非完整測試矩陣 |
| 實車 | x86 Linux PC 為使用者已確認；Ubuntu 22 只是推測，型號／板卡／DBC／安裝外參未確認 |

不能把安裝完成當作真硬體相容已確認，也不能把本輪 metadata 查核稱為重跑整套導航測試。機器可讀摘錄見 docs/validation/architecture_audit.json；完整命令輸出留本機 artifacts。

## 2. 固定環境與部署決策

- 開發：Windows＋WSL2 Ubuntu 22.04＋Docker Desktop＋WSLg。保留現有 distro／可用環境；新 checkout／cache／bags 於後續遷移時可放 WSL Linux filesystem，不在審查時搬動工作目錄。
- Runtime：amd64 Ubuntu 22.04／Humble／Fortress／CycloneDDS。當前 software rendering 已驗收；GPU 僅實驗，保留相關故障紀錄。
- 實車：先核對既有 Linux，不要求 OS 升級；Docker Engine／Compose 加入 hardware-specific overlay。
- 共用：同一 repository、ROS contracts、controller／localization code及 release image；network／clock／devices／calibration／tuning 可依模式不同。
- Desktop private bridge；vehicle 可先採 Linux host network。移除 sim-owned network namespace 依賴，DDS 不再全域綁 lo。
- Humble／Fortress 支援與 Jammy 標準安全維護至 2027-05；維護遷移另列里程碑，不在本輪同時更換 ROS／Gazebo／OS。

## 3. 本輪明確服務邊界

| 服務 | 第一版內容 | 不納入第一版的宣稱 |
|---|---|---|
| core | robot_state_publisher、obstacle projection、map/Nav2、readiness coordination | 不宣稱包含已完成 SLAM |
| localization | 搬出目前 wheel-debug odometry，保留 sim-only identity map alignment | 不將 joint_states 里程計當實車已可用定位 |
| vehicle-control | cmd_vel setpoint adapter、共用速度閉迴路、PACMod adapter、freshness／enable 狀態管理 | 不把原工作區 PID／轉向比當實測值 |
| backend-sim | Gazebo、spawn、sim controllers、sensor bridge、PACMod mock、private actuator adapter | 不包含真 CAN／DBC 驗證 |
| backend-hardware | 後續實車 sensors／PACMod driver | 未取得資料前不提供會碰硬體的假完成模式 |
| tools | Gazebo GUI、RViz、recorder、evaluator | 關 GUI 不影響核心服務 |

第一輪沿用 e2 geometry（軸距1.75 m、輪距1.2 m、輪徑0.295 m）與 small_city；車輛各模組以同一份 geometry 設定生成參數，不能只將其中一個 module 改成 e6 3.4 m。現有 e6 reference 保持 inactive。

Humble /cmd_vel 固定 geometry_msgs/Twist；規劃 /vehicle/setpoint 使用 AckermannDriveStamped，角度定義為路輪角。vehicle-control 內部速度閉迴路與 PACMod adapter 輸出實際 PACMod messages，方向盤角／路輪角轉換明確配置。這個 setpoint 不能被 Gazebo adapter 直接拿來旁路 PACMod。

PACMod provisional messages 採已核對的 pacmod2_msgs；接真 driver 前須核對 ROS2 launch、endpoint、schema、報告與硬體世代。未知型號不影響 mock 開發，會阻擋真車 actuator acceptance。

## 4. 啟動與失敗路徑：避免循環依賴

1. 檢查模式／設定，啟動 description 與 core 基礎節點；Nav2 尚不 activation。
2. backend 等待 robot_description，啟動 Gazebo、spawn、controllers；發布 sensors、clock與實際feedback。
3. localization 等待必要 joint/sensor資料並提供有效TF/pose；vehicle-control 等待fresh reports，保持 disabled。
4. readiness coordinator 確認clock、sensor、TF、reports後 activation Nav2；enable 是獨立明確動作，容器重啟不得自動恢復。
5. backend中止：core process可留存供診斷，但Nav2必須取消／停用、vehicle-control進入不可驅動狀態。不能用「核心還活著」掩蓋失去回授。

不用 core depends_on backend healthy、backend又depends_on core healthy 的循環配置。Compose只處理容器層；ROS readiness與資料freshness由應用層管理。

## 5. 即將實作的批次、檔案與驗收

| 批次 | 預計新增／重構 | 驗收 |
|---|---|---|
| M0 契約與來源 | config/vehicle 共用geometry、config/interfaces、package/source manifest、狀態與timeout定義 | geometry一致；schema／單位／clock／TF owners 明確；可列出driver與message來源、未知revision不隱藏 |
| M1 部署拆分 | avl_bringup分離description／simulation啟動、agile_navigation分離core/localization、DDS desktop設定、deploy/compose.next.yaml、GUI納入services、統一CLI | 獨立project/domain/IGN_PARTITION跑新架構，舊baseline可保留；跨容器資料、GUI重啟、cold start及3/8/16m既有測試通過 |
| M2 PACMod必做 | 新agile_vehicle套件（setpoint、速度controller、PACMod adapter）、mock及private sim actuation adapter、故障注入介面 | 停用直接Twist-to-joint旁路；commands→mock→joints→reports閉迴路；enable/gear/override/fault、timeout、invalid reports、限幅、互鎖、cancel/rest全部通過 |
| M3 可信驗證 | scenarios、統一run manifest／report、動態bag／replay、headless integration CI | 固定起點三次，左右轉／路口、軌跡及yaw誤差、碰撞事件與輪廓取樣；TF late join／clock reset／5–20分鐘資料測試 |
| M4 感測器/LIO | Velodyne契約adapter、真實firing-time rolling scan、LIO profile、calibration truth/estimated分離 | schema與量測時序一致；deskew對照；truth不進估計器；校正held-out證據 |
| M5 實車 | vehicle-readonly、真正drivers／CAN、host doctor與devices setup、calibration profile | 核對OS／hardware／firmware／DBC；passive輸入驗證，再低速封閉場地actuation acceptance |

M1可暫時保留明確標示legacy-direct的回歸路徑以隔離重構問題；M2正式PACMod profile不得使用此路徑。不要一開始把所有未知driver移植、OS升級、rolling scan與全車sensor同時塞進第一批。

新CLI及服務尚未實作；文件中的名稱是規格，不是已可執行的指令。測試用新domain與Gazebo partition由wrapper配置；不可只隔離ROS_DOMAIN_ID而忘記Gazebo Transport。

## 6. PACMod測試與只讀模式的明確規則

必測：disabled不驅動、明確enable、forward/neutral/park、實作reverse前拒絕不支援命令；油門煞車互鎖、角度與速率限制、非有限值、setpoint stale、report stale/invalid、override/fault、clock reset、process restart、cancel與到站保持。freshness依monotonic receipt管理，不能由timer重送舊值刷新；sim pause/reset與硬體watchdog語意分開。

mock reports 取實際模擬回授，不僅echo command。mock工程plant／steering map與真車tuning分開標示；本輪不加入必備delayed plant。

vehicle-readonly須確認無控制傳輸；即使無Nav2 publisher，driver也可能發startup/heartbeat/default frames。先驗證真正passive路徑或只啟動passive report receiver，transmitting driver保持停用，不能僅命名readonly就宣稱無輸出。replay不能開真實actuator transport。

## 7. 此次審查的界線與來源

這次未改Compose／launch／controller／images、未重啟GUI、未控制實車，也未將未知sensor型號填成已知。使用者對simulation_first_plan.md的修改保持原樣。

- https://gazebosim.org/docs/fortress/ros_installation/
- https://docs.docker.com/compose/how-tos/startup-order/
- https://github.com/astuff/pacmod2
- https://github.com/ros-drivers/velodyne/blob/ros2/velodyne_pointcloud/src/lib/pointcloudXYZIRT.cpp
- 本機package metadata、source/config及docs/validation/visible_motion_results.json。

英文介面與生命週期規格：docs/architecture/implementation-baseline.md。
