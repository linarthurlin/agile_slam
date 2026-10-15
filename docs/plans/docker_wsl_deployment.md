# Docker image 復用、WSL2 與容器部署修訂

日期：2026-10-14。本文件為 implementation_plan.md 的環境／部署決策補充；有差異時以本修訂為準。

## 1. 結論

Agile_SLAM 可以直接從既有 `agile_control_ros2:latest` 建立 container，不必先重建整個 image。它可作 Humble baseline 的基底；尚不能直接當完整 simulator image。優先順序更新為：復用指定 image → 驗證 FAST-LIO 與 PACMod2 interface → derived image 補 Gazebo → 單一 container 跑通 → 按需要拆分 → 再評估 Jazzy/Harmonic。

不用為每個 ROS node 各開 container。開發第一版選一個 container、數個 ROS processes，由 launch 管理；穩定後以 simulator、estimation/platform、real vehicle I/O 作部署邊界。image、container、process、host 是不同概念：一個 image 可開多個 containers，一個 container 可跑多個 ROS processes；不需要多台 host。

## 2. 已實測的本機狀態

- 專案已改為 `D:\UCSD\Lectures\AVL\Agile_SLAM`。
- WSL：Ubuntu-22.04 與 docker-desktop，兩者 running、version 2。
- 使用者確認的 image ID：`sha256:a6acca67607edcb48e66adfec152714ad480b0b0854587c6dcca72034f2084ca`；本機 tag `agile_control_ros2:latest`，約 5.54 GB，linux/amd64。
- 以唯讀、無網路、無裝置暫時 container 檢查：Ubuntu 22.04.5、ROS Humble。
- ROS package discovery 有 `fast_lio`、`pacmod2`、`pacmod2_msgs`、`pacmod_twist_bridge`、Nav2、RViz2、robot_state_publisher、xacro。
- dpkg 有 pacmod2 2003.1.1、pacmod2_msgs 1.0.0、CycloneDDS 與 rmw_cyclonedds_cpp。
- 查詢未找到 gz/ign executable 或 Gazebo/ros_gz packages；本輪未發現 Velodyne/RealSense ROS package。這是查詢結果，不保證其他自訂位置完全沒有相關檔案。
- entrypoint source `/opt/ros/humble/setup.bash`、條件式 source `/workspace/ros_ws/install/setup.bash`，設定 `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` 與 `CYCLONEDDS_URI=file:///etc/cyclonedds.xml`。
- `/etc/cyclonedds.xml` 指定 `NetworkInterface name="lo"`。不同 bridge containers 的 lo 是各自的，不能拿此設定作跨容器 DDS。

實測只確認安裝／設定與 shell 啟動；未啟動 FAST-LIO、PACMod CAN driver 或 Gazebo，未驗證 GPU、DDS data flow、即時效能。image 有 PACMod2 套件不等同實車板卡世代已確認。

## 3. 如何使用 image

### 3.1 已載入的本機 image

此 image 已在 daemon 中，直接 docker run 即可，不需要 docker load。若未來拿到的是 docker save 的 .tar/.tar.gz，用 `docker load --input <archive>`；docker export 的 rootfs archive 是不同格式，import 不會還原原 image 的完整啟動設定。[Docker load](https://docs.docker.com/reference/cli/docker/image/load/)

以下可在 PowerShell 執行，僅開 shell，沒有裝置或 real control launch：

```powershell
docker run --rm -it --name agile-slam-dev --network none --entrypoint /bin/bash agile_control_ros2:latest
```

image 原 entrypoint 可用於正常互動工作，但稽核／初次檢查 override entrypoint，避免自動載入未知 workspace/environment。上例沒有 source ROS，需手動 source；network none 只是檢查用，正式 ROS profile 改為經驗證的 network。

### 3.2 Derived image 與可重現性

建立 Agile_SLAM 自己的 Dockerfile，FROM 固定本機 base image／registry digest，再裝經核對的 Gazebo/Fortress、ros_gz、ros2_control、Ackermann、sensor dependencies 與 avl packages。不要只在互動 container 裡 apt install 然後依賴 docker commit。

注意使用者提供的是本機 image ID，不是 registry RepoDigest；不能直接把這串當任意 registry 的 `name@sha256:...` 使用。先建立版本化 local tag、檢查 ID；跨機器以 archive SHA256 或推送後的 RepoDigest 固定來源，保留 derived Dockerfile、apt resolved versions、workspace commit。

目前 image 原 workspace 在 `/workspace/ros_ws`；禁止 bind mount 整個新專案到 `/workspace`，否則會遮蔽既有 packages。新 overlay 放 `/opt/agile_slam_ws` 或 `/workspace/agile_slam_ws`，source 順序 base ROS → existing workspace → Agile_SLAM overlay。避免重複 package 覆蓋未記錄的 FAST-LIO 版本。

build/install/log 使用 Linux volume，source 可從指定 D: path 掛入；bag 與大型暫存優先 WSL ext4/volume。sim profile 不給 CAN、USB 或 privileged。已存在的 entrypoint 只是 source/export/exec，本輪讀取未見自動啟動車控。

## 4. 容器切分決策

| 階段／服務 | 預設位置 | 理由／條件 |
|---|---|---|
| 初期模擬 bringup | 單一 derived dev container：Gazebo、bridge、TF、FAST-LIO、mock PACMod | 先排除跨容器 discovery 變數；不同 process 可分別重啟，不需每個 node 各一個 image |
| sim service | 穩定後單獨 container：Gazebo＋ros_gz＋simulation-specific adapters | renderer/GPU dependencies、world reset 與 fault injection 獨立 |
| platform service | sensor normalization、robot description、FAST-LIO／其他 LIO、diagnostics | 先維持一個共同 ROS/runtime 版本，避免不必要的 cloud/service 拆分 |
| vehicle-sim | mock PACMod／DBW plant，可併入 sim 或 platform | 明定單一 owner；sim 時不啟動真正 CAN driver |
| vehicle-real | 原生 Linux 的獨立 process，或具有所需 CAN 權限的 container | 隔離 actuator device 權限與 lifecycle；LIO restart 不得隱含 re-enable DBW |
| recorder/evaluator | 初期共用 dev；有資源隔離需求再獨立 | 可以個別停止錄製，控制磁碟與 CPU 負載 |
| calibration tool | 有 ROS1/Python/依賴衝突時獨立 offline container | 處理 bag/資料，不持有車控權限 |

LIO 要獨立 container 的實際理由：CUDA/GTSAM/Python 衝突、獨立版本實驗、不同 restart policy、資源限制。拆開不會自動得到更低 latency 或 fault safety；控制 watchdog 與 disable semantics 仍必須實作。PACMod 真車 service 不設定無條件 restart=always/re-enable。

FAST-LIO 已有安裝，改為第一個 compatibility spike，而不是立即再裝 GLIM/LIO-SAM。確認來源 commit、ROS2 port、輸入 cloud time/ring schema、IMU需求、extrinsic convention、TF publishing、bag sample；能跑不等於已有完整 loop closure/global SLAM。保留既有計畫的真值隔離與 snapshot/rolling-scan gate，其他 SLAM 作比較候選。

## 5. WSL2 的角色與建議拓樸

```text
Windows：編輯專案、Docker Desktop、GPU host driver
  └─ WSL2 backend／Ubuntu-22.04：Linux terminal 與開發工具
       └─ Docker Desktop Linux engine
            ├─ 第一階段 agile-slam-dev
            └─ 第二階段 sim + platform + optional recorder
實車：原生 Ubuntu＋NIC/USB/SocketCAN＋sensor/PACMod drivers
```

Docker Desktop 的 WSL2 backend 與你用來下指令的 Ubuntu distro 是不同角色；在 Ubuntu terminal 下 docker 指令不代表 daemon 跑在該 distro。用 `docker context show`、`docker info` 確認。先使用已有 Docker Desktop WSL integration，不另外再裝一套 distro 內 Docker daemon，避免 images、volumes、network contexts 分散。[Docker WSL2 backend](https://docs.docker.com/desktop/features/wsl/)

WSL Ubuntu 22.04 可以啟動 Ubuntu24.04-based Linux container；container userspace 與 distro userspace 不必一致。仍須驗證 host kernel、GPU、圖形與 driver 相容。Jazzy/Harmonic 維持中期候選，不因取得既有 Humble image 而急著同時升級所有依賴。

### 5.1 GPU 與 GUI 分開驗收

Docker Desktop Windows GPU 支援以 WSL2 backend 與 NVIDIA GPU 為官方路線；先確認 Windows driver/WSL，測 container CUDA，再測 Gazebo EGL/OpenGL renderer與 RViz。CUDA 成功不代表 Gazebo GPU lidar 或 WSLg 顯示成功。[Docker GPU support](https://docs.docker.com/desktop/features/gpu/)

先以 headless physics 啟動，再測 headless rendering、RGB/depth/GPU lidar，最後加 GUI。沿用來源 X11 mount/DISPLAY 不保證適用 WSLg；必須按實際 sockets/runtime variables 寫 gui-wsl override。若 Desktop GUI 路徑不穩，允許 Gazebo/RViz 跑在 WSL distro，其他節點 container 化，但這會增加一個 DDS boundary，必須另外驗證。

## 6. DDS/network 決策與 gate

### 6.1 初期

單 container 內先驗證現有 CycloneDDS loopback configuration；不預先宣稱 multicast-on-lo 必然可靠。固定 ROS_DOMAIN_ID、RMW、message definitions、QoS。稽核 manifest 保存 CYCLONEDDS_URI、interface 與 network mode。

### 6.2 多 containers

預設嘗試單一 user-defined bridge network，為 CycloneDDS 建新的設定：移除 lo-only 限制，選 container 可達 interface／auto selection，必要時配置明確 peers。不要為了拆 containers 沿用 source compose 的 host networking 與原 lo XML。multicast／unicast 選項依實測決定；service DNS/peer configuration 必須在 CycloneDDS 版本上驗證。

Linux native host network 可減少 namespace 差異，但 Docker Desktop host networking 是 4.34+ 的 opt-in，僅 layer4 TCP/UDP、不能直接 bind host NIC IP，不能假定具有完整 Linux host-network 特性或 DDS multicast 行為。[Docker host networking](https://docs.docker.com/engine/network/drivers/host/)

發現 ROS topics 並不代表資料可傳。驗收必須涵蓋 talker/listener、IMU、完整 PointCloud2、TF static late join、QoS、rate/size/loss/latency、container restart後 rediscovery、sim clock/reset。初期控制/感測器 DDS 全留在同一 Linux/container network，不以開一個 port 或 `host.docker.internal` 代替 DDS 設定。

### 6.3 WSL／LAN／真實感測器

需要跨 Windows/WSL/LAN 時，Windows11 22H2+ 可評估 mirrored mode，官方列出 multicast support；仍需核對 Hyper-V/Windows firewall、NIC選擇、UDP與DDS peers。mirrored WSL 不能自動改變 Docker Desktop container network。[WSL networking](https://learn.microsoft.com/en-us/windows/wsl/networking)

Velodyne UDP packet flow、device destination IP、broadcast/unicast 與 ROS DDS 是不同鏈路，分別測。主機 discovery 成功不代表感測器 UDP 可進入 container。

## 7. PACMod 與硬體

模擬僅使用 PACMod-compatible command/report mock；真 driver 等實車階段才啟動。先識別此 pacmod2 package 的 CAN backend、launch/config、board/firmware/DBC。不要因 image 有 pacmod2 就判定實車一定為 PACMod2。

SocketCAN 不是 TCP/UDP port，Docker Desktop 的 host network不能當作 CAN passthrough。WSL USB 可透過 usbipd-win 附加，但 CAN kernel module、adapter driver、RealSense streaming、reconnect、throughput仍需驗證；Docker Desktop沒有一般直接 USB passthrough，不能假設加 `--device` 就能看到 Windows 裝置。[WSL USB](https://learn.microsoft.com/en-us/windows/wsl/connect-usb)、[Docker Desktop FAQ](https://docs.docker.com/desktop/troubleshoot-and-support/faqs/general/)

推薦真車用原生 Ubuntu，PACMod driver 靠近 CAN adapter；模擬工作站透過明確 ROS interface 或離線 bag 接軌。若一定要在 WSL/CAN gateway做 HIL，另寫有 timeout、timestamp、diagnostics 的 gateway方案並做延遲/失聯驗證，不納入 MVP。

## 8. 更新後 tickets 與 gate

1. IMG-01：保存指定 image ID、版本化 tag/archive checksum、entrypoint/DDS/package audit（本次已取得初步證據）。追查原 Dockerfile與FAST-LIO來源 commit。
2. ENV-01：確認 Docker context/WSL integration、GPU/GUI、storage；不重裝 WSL，不平行維護第二個 daemon。
3. IMG-02：從既有 image 建 derived simulator image；單次 colcon build、新 overlay、明確版本依賴；先 Humble/Fortress baseline，保留支援期限風險與Harmonic後續 spike。
4. LIO-01：使用 image 內 fast_lio 做 official/sample bag及source-schema檢查；確立 TF ownership與point time策略。
5. NET-01：單 container資料鏈通過後，建立 bridge/CycloneDDS profile與兩container點雲/IMU/restart驗收。通過才把 sim/platform 拆分。
6. DBW-01：PACMod2 mock semantic parity，real driver不在 sim mode啟動；實車 board/DBC確認後再做硬體 read-only reports。
7. 更新 setup SOP、manifest、Compose profiles；P0/P1以既有 image加速，但不在 benchmark前刪除原time/calibration gates。

本輪只做 image的隔離暫時檢查與文件更新；沒有安裝套件、啟動長駐服務、變更 WSL/Docker設定或操作CAN。下一個實作批次應是 IMG-01補齊來源、ENV-01與IMG-02。
