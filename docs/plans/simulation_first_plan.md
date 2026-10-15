# Simulator-first development plan

日期：2026-10-14。優先範圍：簡單場景、車輛運動、sensor sanity、Nav2。GUI 由使用者手動關閉，先前 exit code 不再列為已確認的自發 GUI 故障。

## 1. 可在 simulator 完成的工作

| 順序 | 開發內容 | 起始場景／操作 | 驗收證據 |
|---|---|---|---|
| S0 | 基礎環境與車控 | 平地、牆、箱體；靜止／低速直行 | spawn、controllers、timeout、重啟與可重現設定 |
| S1 | 感測器與 TF sanity | 已知距離平面；靜止、左右轉 | frame、軸向、量測範圍、CameraInfo、有效點數、量測頻率、時間順序 |
| S2 | 低速車輛模型 | 0.3/0.6 m/s、不同轉彎半徑、figure-eight | wheel odom 對獨立真值、速度／曲率誤差、停止距離；此為模擬模型檢查 |
| S3 | Nav2 靜態導航 | 空地目標、單箱體繞行、寬走道 | 成功／取消／不可達目標、path、costmaps、保守 footprint、command limits |
| S4 | 錄製／重播 | 固定路線與固定參數 | bag QoS、TF static late join、唯一 clock、manifest、重播結果一致性 |
| S5 | 全域定位／建圖 | warehouse／depot／環路 | AMCL 或 SLAM 唯一 map→odom authority，處理輪速 drift；不再使用已知起點 identity alignment |
| S6 | 完整 sensors 與資料整合 | 三顆前 LiDAR、多 camera、RealSense profile | topic/frame/schema、遮蔽／視野、資料量與運算負載；未知型號保持 placeholder |
| S7 | 校正與故障注入 | 標靶區、不同平面、充分運動激發 | truth/nominal 分離、內外參、offset/drift/jitter/dropout、held-out 驗證 |
| S8 | PACMod 模擬 | drive-by-wire mock  | enable/override/fault、gear、油門煞車互鎖、steering map、timeout/report parity |
| S9 | 強健性與效能 | 動態障礙、窄路、低特徵、CPU/GPU 負載 | 失敗偵測、queue/loss、latency、RTF、恢復行為、CI regression |

模擬可驗證軟體介面、演算法流程、理想幾何與指定故障下的行為。實際鏡頭／LiDAR factory calibration、USB/NIC/CAN、PTP/PPS、機構振動、真車煞車與輪胎參數仍必須實測。模擬 PACMod mock 不等同已驗證真實 firmware／DBC。

## 2. 本次先完成的簡單實驗

- 新增 navigation 場景：40×24 m 地圖範圍、邊界牆、中心箱體與兩個 landmarks；沒有大型外部 meshes。
- JSON 是障礙物位置唯一來源，同時產生 Gazebo SDF 與 0.1 m occupancy map；CI 檢查生成檔同步。
- wheel odometry 只讀 joint_states，加入後軸控制 frame；ground truth 僅給 evaluator。
- Nav2：Humble 1.1.x、Smac Hybrid-A*／DUBIN、最小轉彎半徑 4 m、Regulated Pure Pursuit、0.6 m/s 上限；關閉原地旋轉與旋轉 recovery。
- LiDAR 經 reliable subscriber 轉為 height-filtered virtual obstacle scan；保留原始 PointCloud2。
- 第一版 map→odom 為已知起點的 identity alignment；尚未使用 AMCL／SLAM，不能當成全域定位已完成。
- 直線目標 (3,0) 與繞箱體目標 (16,0) 已各完成一次；後者由獨立 evaluator 檢查保守車身 footprint，沒有取樣到與指定箱體重疊。
- 15 秒 sensor window 檢查時間順序、frame、資料格式、有效點數與接收頻率；RGB 輸出率及軟體渲染 RTF 保留效能限制。

這是低速靜態導航基線。全域路徑使用預先生成地圖；未知／動態障礙的自主繞行、長時間 drift、完整碰撞證明與高擬真 LIO 不在本次通過範圍。

## 3. 下一批簡單測試

1. 固定起點重跑直行與左右繞行各三次，報告真值位置／yaw 誤差與成功率，而非只看 Nav2 action success。
2. 添加專用 wall-distance 與 sensor-axis 測試；驗證 LiDAR min/max range、IMU 正負方向、camera intrinsic/optical frame 與靜態 TF。
3. 測試 goal cancel、occupied goal、不可行轉彎、controller 中止；確認不出現原地旋轉要求或殘留車控命令。
4. 跑 5–20 分鐘負載測試，分開 wall time、sim time、sensor generation 與 ROS delivery；調整 RGB/profile，避免以降頻掩蓋資料漏收。
5. 錄下 minimal bag，加入 QoS overrides、calibration/config/run manifests，再做 clock reset／replay regression。
6. 引入 warehouse/depot 後再建立 AMCL／SLAM profile，最後擴充多感測器校正與 PACMod mock。

## 4. 現成場景研究與選擇

| 來源 | 適合用途 | 對目前 Fortress 的判斷 |
|---|---|---|
| Gazebo 官方 ign-gazebo6 examples/worlds | shapes、sensors、physics 小實驗 | 優先；使用對應版本 branch，選小型無外部資產例子 |
| TurtleBot4 humble worlds | depot、warehouse、maze，結構特徵與導航 | 優先評估；官方對應 Humble/Fortress，但取用 world，不沿用小型差速車的 footprint/controller |
| Gazebo Fuel 的 Warehouse／shelves／barriers | 模組化倉庫、走廊、障礙區 | 可組裝；每個資產記錄 owner/version/hash/license，預先 cache，避免 CI 啟動時下載 |
| AWS RoboMaker Small Warehouse ros2 branch | 更豐富 warehouse assets | 次選；原始啟動方式仍是 Classic gazebo，來源目前已 archive，需改 plugins/URIs/launch 並檢查效能與資產授權 |
| 原 golf_cart_sim tracks | outdoor／loop regression | 可再用；先確認 mesh license、碰撞幾何與垂直特徵，不把平坦賽道當理想 SLAM 場景 |

本次沒有下載／vendor 外部 warehouse 資產；先建立小型自有測試場，避免把網路依賴與大型 mesh 效能混入基礎驗收。此建議已由使用者指定的 small_city 取代，詳見下方進度。

來源：

- [Gazebo Fortress examples](https://github.com/gazebosim/gz-sim/tree/ign-gazebo6/examples/worlds)
- [TurtleBot4 官方 simulator manual](https://turtlebot.github.io/turtlebot4-user-manual/software/turtlebot4_simulator.html)
- [TurtleBot4 humble warehouse world](https://github.com/turtlebot/turtlebot4_simulator/blob/humble/turtlebot4_ignition_bringup/worlds/warehouse.sdf)
- [AWS archived repository](https://github.com/aws-robotics/aws-robomaker-small-warehouse-world)／[原 ros2 branch](https://github.com/aws-robotics/aws-robomaker-small-warehouse-world/tree/ros2)
- [Nav2 Humble RPP](https://api.nav2.org/nav2-humble/html/md_nav2_regulated_pure_pursuit_controller_README.html)

操作方式與英文驗收報告分別見 docs/navigation.md、docs/validation/navigation.md。

## 5. small_city 實作進度（2026-10-15）

依使用者指定，主場景改為 small_city；固定 collection 與官方 osrf/gazebo_models 的來源 commit。36 個模型採本機快取，原始檔、授權與雜湊保留；大型資產與衍生地圖不進 Git。

已完成本輪城市基線：Classic→Fortress 轉換、材質／COLLADA 修正、道路視覺轉換、保守碰撞輪廓地圖、城市啟動 profile、GUI 資產掛載。預設 software Ogre2；WSL GPU profile 僅供實驗，目前不列為可用驗收設定。

| 階段 | 本輪證據 | 尚未完成 |
|---|---|---|
| S0 | 城市場景、spawn、controllers、Nav2 啟用 | 冷啟動重複性統計 |
| S1 | 15 秒 sensor/frame/schema/時間順序檢查通過 | 已知牆距／軸向專用測試、RGB 完整率與延遲 |
| S2 | 低速行駛至 3/8/16 m；真值僅供 evaluator | 固定速度、左右圓周、figure-eight、停止距離 |
| S3 | 三個接續目標通過；cancel 與 occupied goal 通過 | 各路線三次獨立重跑、路口轉彎／不可行曲率 |
| S4 | 靜止短 bag 與獨立 domain sensor replay 通過 | 動態 bag、QoS 固定、TF late join、clock reset、manifest 回歸 |
| S5–S9 | 保留後續開發順序 | 定位／SLAM、完整 sensors、校正故障注入、PACMod mock、長時間強健性 |

接續優先順序：先補 S1/S2 專用幾何與運動測試，再補 S3 重複路線／路口、S4 動態錄製與重播；完成後才加入 AMCL／SLAM。實車感測器型號與 e6 尺寸未確認前，模型須標示 placeholder；現有 LiDAR 缺逐點時間，不能直接宣稱 FAST-LIO deskew 有效。

本輪感測器 RTF 約 0.38、RGB 約 23 Hz（依模擬時間），屬明確效能限制。3/8/16 m 真值誤差約 0.33/0.35/0.36 m；取樣未出現保守輪廓重疊，不等同完整碰撞安全證明。英文操作與證據：docs/small_city.md、docs/validation/small_city.md。
