# AI 记忆管理文件

> **用途**：本文件帮助 AI 助手在每次对话中快速了解项目全貌，实现持续跟进。
> **维护规则**：每次与 AI 协作完成重要工作后，更新本文件对应的部分。
> **最后更新**：2026-07-14 20:15

---

## 1. 项目基本信息

| 项目 | 内容 |
|------|------|
| **项目名称** | 假肢机械臂 |
| **当前主任务** | 多设备同步数据采集体系（D435i + SparQi手环 + TouchGlove手套 + NOKOV动捕） |
| **已完成任务** | ✅ 机械臂控制（蓝牙手柄→BLE桥→STM32→舵机），6/19 ③号板联调完毕，学长/老师交付闭环 |
| **项目路径** | `d:\假肢机械臂\`（文档）+ `D:\Dev\sparmqi-workbench\`（手环工作台）+ `D:\Dev\data-collection\`（手套管线） |
| **GitHub 文档仓库** | `prosthetic-robotic-arm`（public） |
| **GitHub 代码仓库** | `sparmqi-workbench`（**PRIVATE**）+ `arm-ble-firmware` + `arm-ble-s3-firmware` + `arm-ble-gui` |
| **负责人** | （你的名字 / 年级：大二下） |
| **开始时间** | 2026年6月 |

## 2. 开发环境

| 项目 | 路径 | GitHub | 工具 | 用途 |
|------|------|------|------|------|
| 文档管理仓库 | `d:\假肢机械臂\` | prosthetic-robotic-arm | Git + Markdown | 项目文档、笔记、规划 |
| nRF52固件 | `D:\Dev\arm-ble\` | arm-ble-firmware | PlatformIO | 📦 已完结 |
| ESP32-S3固件 | `D:\Dev\arm-ble-s3\` | arm-ble-s3-firmware | PlatformIO | 📦 已完结 |
| 上位机GUI | `D:\Dev\arm-ble-gui\` | arm-ble-gui | Qt 6.11 + MSVC | 📦 已完结 |
| 手环工作台 | `D:\Dev\sparmqi-workbench\` | sparmqi-workbench(**PRIVATE**) | PyQt5+pyqtgraph+scipy | 🔵 v1.6 |
| 手套管线 | `D:\Dev\data-collection\` | 本地 | WSL2+Python 3.10+CUDA | 🔵 |

## 3. 设备打通状态（仅当前主攻任务）

| 设备 | 接口 | 环境 | 状态 |
|:--|:--|:--|:--:|
| D435i 相机 | USB 3.2 | Windows 原生 | ✅ 7/10 四路流+内参 |
| SparQi 手环 #1 (Band3BA) | BLE→COM6 | Windows Python 3.10 | ✅ 7/13 打通，ACK超时待回归 |
| SparQi 手环 #2 (Band794) | BLE→COM6 | Windows Python 3.10 | ✅ 7/14 全链路通过 |
| TouchGlove 手套 | COM5→TCP→WSL2 | WSL2+CUDA | ✅ 7/12→7/13 |
| NOKOV 动捕 | 局域网→XINGYING | Windows | 🟡 SDK已归档 |

> 📦 机械臂控制（nRF52840/ESP32-S3/STM32/舵机组）已交付闭环，详见 `08_周报与汇报/阶段回顾_机械臂控制完结_20260714.md`

### SparQi 手环详细信息

| 属性 | 值 |
|------|------|
| **两台MAC** | Band3BA=`ED:9D:0F:48:F3:BA`, Band794=`ED:A4:A3:B8:07:94` |
| **传感器** | 9ch EMG(500/1000/2000Hz) + 6轴IMU(25-500Hz) + PPG(3ch,待验证) + EDA(4ch,待验证) |
| **物理电极** | 14方电极分两组(6+8) → 9 EMG差分通道 + 参考/地/DRL |
| **背面圆盘** | 疑似PPG光学窗口（绿光LED+光电二极管），待验证 |
| **SDK** | ResearchKit_SDK v1.0.0 (.pyd, cp310)，Python 3.10专属，闭源 |
| **BLE参数** | Broadcom适配器→COM6, MTU 247, PHY 2M, 连接间隔15ms |

### 采样率实测数据

| 设备 | 标称 | 实测有效速率 | 偏差 |
|------|:--:|:--:|:--:|
| Band794（新） | 1000 Hz | ~682 Hz | -32% |
| Band3BA（旧） | 1000 Hz | ~989 Hz | -1% |

> Band794 偏低可能是 BLE 连接间隔(15ms)限制 → 约 67 批次/秒 × 每批10点 ≈ 670 Hz 天花板

### Workbench v1.6 功能表

| 模块 | 功能 |
|------|------|
| **BLE交互** | 两步走：启动扫描→用户选设备+勾IMU→点击连接 |
| **实时显示** | 9宫格EMG(3×3) + 通道对比(可选通道叠加+图例) |
| **IMU** | 连接前勾选启用 → IMU选项卡显示加速度3轴+陀螺仪3轴曲线 |
| **信号处理** | 10Hz高通(默认) / 50Hz陷波 / 20-500Hz带通 / 全波整流 / RMS包络, 可切换 |
| **视图控制** | 滚轮缩放+右键平移+「重置视图」恢复自适应 |
| **录制** | session目录存储(emg.csv+imu.csv+meta.json+备注), index.csv全局索引 |
| **回放** | session列表加载 → 进度条拖动 → 三选项卡回放(9宫格/通道对比/IMU), 0.5-4x倍速 |
| **设备选择** | 下拉框列全部Band设备, 默认选Band794(★标记), 重扫按钮 |

### TouchGlove 连接架构
```
手套STM32(COM5) → Windows bridge.py(TCP 0.0.0.0:12345)
  → WSL2 gateway → socat → /tmp/ttyGlove
  → Python SDK → CUDA ONNX推理 → 5×32×32×3 force+disp
  → PySide6 GUI(xcb/XWayland模式) ✅
```
**5通道 Sensor ID：** `55045D1D9DF60905` `55075C8B9DF7BA0C` `550265A09DF60939` `5505DFAC9DF7BA06` `5505AE8F9DF7BB27`

## 4. 重要约定与规则

1. **STL/SolidWorks大文件**：不入Git，AI不读取内容
2. **代码与文档分离**：代码在 `D:\Dev\`（纯英文），文档在 `d:\假肢机械臂\`
3. **WSL2连Windows**：用 `ip route show default` 拿gateway IP
4. **WSLg Qt GUI**：必须用xcb插件（`QT_QPA_PLATFORM=xcb`）
5. **SparQi Workbench是PRIVATE仓库**，SDK .pyd不入库

## 5. 关键技术踩坑

### SparQi BLE 连接（7/14）
| # | 坑 | 根因 | 修复 |
|:--:|------|------|------|
| 1 | 重连失败"not in scan results" | `close()`+新`open()`导致手环广播中断 | 保持同一client, 等5s re-scan再连 |
| 2 | Band3BA start_capture CMD 0x01超时 | 手环固件状态问题(Band794一次就过) | 重启手环+6次重试 |
| 3 | Workbench GUI不弹出(3次迭代) | 缺`self.show()`+多线程竞争COM6 | v1.3修复 |
| 4 | COM6 NRF_ERROR_TIMEOUT | SDK未正常close()锁住串口 | 拔插适配器+每次close() |
| 5 | IMU勾选后卡退 | stop_capture→open竞态 | v1.4fix: 只设标志位, 连接前选好 |

### 手套USB打通（7/12）
| 1 | usbipd错误×7 | usbipd-win与STM32 CDC不兼容 | 换路线 |
| 2 | WSL2 localhost不通 | WSL2 NAT不转发 | 用`ip route show default` |

### GUI打通（7/13）
核心结论：WSLg RDP RAIL只转发X11窗口，Qt Wayland surfaces不转发 → 强制`QT_QPA_PLATFORM=xcb`

## 6. SDK/资料档案位置

| 资源 | 路径 |
|------|------|
| SparQi SDK | `D:\Dev\sparqi-env\src\ResearchKit_SDK\` + `.venv(Python 3.10)` + wheel |
| SparQi Workbench | `D:\Dev\sparmqi-workbench\` v1.6 (PRIVATE GitHub) |
| 前人同步代码 | `D:\Dev\sparqi-env\sync_data\` + `main_emg_nokov_aligned.py` |
| NOKOV SDK | `D:\动捕+机电手环资料\NOKOV\` |
| TouchGlove SDK | `06_文献与参考资料/TouchGlove_SDK/` |

## 7. 待解决问题

### 手环
- 🟡 Band3BA start_capture ACK超时 — 待重启回归
- 🟡 Band794 有效采样率682Hz — 可能BLE连接间隔限制
- 🟡 14电极→9通道物理映射 — 待戴手上做手势验证
- ⚠️ IMU陀螺仪数据全为零 — 待摇晃手环验证（需先确认IMU确实启用成功）
- ❓ PPG硬件是否存在 — 待看背面圆盘有无绿光
- 🟡 双设备同时采集方案 — 需两个COM口适配器

### 其他
- 🟡 NOKOV动捕 XINGYING连接
- 🟡 四设备同步框架 `sync_main.py`
- 🟡 手眼标定（D435i↔手套）
- 🟡 手套soft filter/校准SOP

## 8. 一键启动

```powershell
# SparQi Workbench (桌面双击)
C:\Users\tb137\Desktop\SparQi_Workbench.bat

# TouchGlove 手套
python D:\Dev\data-collection\scripts\glove_serial_bridge.py    # 窗口A
wsl -d Ubuntu-22.04 bash D:\Dev\data-collection\scripts\wsl_gui_launcher.sh  # 窗口B
```

## 9. 参考文档索引

| 文档 | 内容 |
|------|------|
| `08_周报与汇报/阶段回顾_机械臂控制完结_20260714.md` | 📦 机械臂控制完结归档 |
| `09_项目管理/完整体系实施路线图_20260711.md` | 四设备同步采集规划 |
| `09_项目管理/任务看板.md` | 当前任务看板 |
| `../Dev/sparmqi-workbench/docs/devlog/2026-07-14_推进汇总.md` | 今天全部推进记录 |
| `../Dev/sparmqi-workbench/docs/devlog/2026-07-13_项目初始化.md` | Workbench初始开发 |