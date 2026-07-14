# AI 记忆管理文件

> **用途**：本文件帮助 AI 助手在每次对话中快速了解项目全貌，实现持续跟进。
> **维护规则**：每次与 AI 协作完成重要工作后，更新本文件对应的部分。
> **最后更新**：2026-07-14 14:20

---

## 1. 项目基本信息

| 项目 | 内容 |
|------|------|
| **项目名称** | 假肢机械臂 |
| **当前主任务** | 多设备同步数据采集体系（D435i + SparQi手环 + TouchGlove手套 + NOKOV动捕） |
| **已完成任务** | ✅ 机械臂控制（蓝牙手柄→BLE桥→STM32→舵机），6/19 ③号板联调完毕，学长/老师交付闭环 |
| **项目路径** | `d:\假肢机械臂\`（文档）+ `D:\Dev\arm-ble\`（nRF52固件）+ `D:\Dev\arm-ble-s3\`（ESP32-S3固件）+ `D:\Dev\arm-ble-gui\`（上位机）+ `D:\Dev\data-collection\`（数据采集） |
| **GitHub** | `prosthetic-robotic-arm` |
| **负责人** | （你的名字 / 年级：大二下） |
| **开始时间** | 2026年6月 |

## 2. 开发环境

| 项目 | 路径 | GitHub | 工具 | 用途 |
|------|------|------|------|------|
| 文档管理仓库 | `d:\假肢机械臂\` | prosthetic-robotic-arm | Git + GitHub | 项目文档、笔记、规划 |
| nRF52 固件 | `D:\Dev\arm-ble\` | arm-ble-firmware | PlatformIO（nordicnrf52） | 📦 已完结（机械臂控制） |
| ESP32-S3 固件 | `D:\Dev\arm-ble-s3\` | arm-ble-s3-firmware | PlatformIO（espressif32） | 📦 已完结（备用板） |
| 上位机 GUI | `D:\Dev\arm-ble-gui\` | arm-ble-gui | Qt 6.11 + CMake + MSVC | 📦 已完结 |
| 数据采集 Pipeline | `D:\Dev\data-collection\` | 本地 | WSL2 + Python 3.10 + ONNX Runtime GPU (CUDA 12) | 🔵 当前主攻 |
| SparQi Workbench | `D:\Dev\sparmqi-workbench\` | 本地 | PyQt5 + pyqtgraph + scipy | 🔵 当前主攻（手环可视化） |

## 3. 设备打通状态（仅当前主攻任务）

| 设备 | 接口 | 环境 | 状态 |
|:--|:--|:--|:--:|
| D435i 相机 | USB 3.2 | Windows 原生 | ✅ 7/10 四路流 + 内参 |
| Spar Qi 手环 #1 (Band3BA) | BLE→COM6 | Windows Python 3.10 | ✅ 7/13 打通，ACK 超时待回归 |
| Spar Qi 手环 #2 (Band794) | BLE→COM6 | Windows Python 3.10 | ✅ 7/14 打通，一次通过 |
| TouchGlove 手套 | COM5→TCP→WSL2 | WSL2 + CUDA | ✅ 7/12 打通 → 7/13 GUI |
| NOKOV 动捕 | 局域网→XINGYING (10.1.1.198) | Windows | 🟡 SDK 已归档，待连接 |

> 📦 机械臂控制相关设备（nRF52840/ESP32-S3 BLE桥、STM32控制板、舵机组）已交付闭环，详见 `08_周报与汇报/阶段回顾_机械臂控制完结_20260714.md`

### Spar Qi 手环详细信息
- **MAC**: Band3BA=`ED:9D:0F:48:F3:BA`, Band794=`ED:A4:A3:B8:07:94`
- **传感器**: 9ch EMG (1000Hz 标称) + 6轴 IMU (AX/AY/AZ/GX/GY/GZ, 可选 25-500Hz) + PPG(3ch) + EDA(4ch)
- **物理电极**: 14 个电极触点 → 9 个 EMG 差分通道（映射关系待确认）
- **IMU**: 已验证 SDK 支持，硬件是否实际装载待验证
- **SDK**: ResearchKit_SDK v1.0.0 (.pyd, cp310), Python 3.10 专属
- **Workbench**: v1.1, 路径 `D:\Dev\sparmqi-workbench\`

### TouchGlove 连接架构
```
手套 STM32 (COM5) → Windows bridge.py (TCP 0.0.0.0:12345)
  → WSL2 gateway (172.25.176.1) → socat → /tmp/ttyGlove
  → Python SDK → CUDA ONNX dense 推理 → 5×32×32×3 force+disp
  → PySide6 GUI (xcb/XWayland 模式) ✅
```
**5 通道 Sensor ID：**
`55045D1D9DF60905` `55075C8B9DF7BA0C` `550265A09DF60939` `5505DFAC9DF7BA06` `5505AE8F9DF7BB27`

## 4. 重要约定与规则

1. **STL/SolidWorks 大文件**：不入 Git，AI 不读取内容
2. **文件命名规范**：你画零件加`【打印件/加工件/铝方管】`前缀
3. **打印材料**：未来工场8200pro树脂（光固化）+ 尼龙件
4. **代码与文档分离**：代码在 `D:\Dev\`（纯英文），文档在 `d:\假肢机械臂\`
5. **WSL2 连 Windows 永远用 `ip route show default`** 拿 gateway IP，不要用 localhost 或 nameserver
6. **多行跨环境命令永远写成脚本文件**，不要在命令行里嵌套 PowerShell→bash→Python 引号
7. **WSLg Qt GUI 必须用 xcb 插件**（`QT_QPA_PLATFORM=xcb`），wayland native surfaces 不被 RDP RAIL 转发

## 5. 关键技术踩坑

### SparQi BLE 连接（7/14）
| # | 坑 | 根因 | 修复 |
|:--:|------|------|------|
| 1 | 重连失败 "not in scan results" | `close()`+新 `open()` 适配器导致手环广播中断 | 保持同一 client 实例，等 5s 后 re-scan 再重连 |
| 2 | Band3BA start_capture CMD 0x01 超时 | 手环固件状态问题（Band794 一次就过） | 重启手环 + 加重试逻辑 |

### 手套 USB 打通（7/12）
| # | 坑 | 根因 | 教训 |
|:--:|------|------|------|
| 1 | usbipd "Device in error state" ×7 | usbipd-win 5.3.0 与 STM32 CDC 不兼容 | 同错误 3 次换路线 |
| 2 | WSL2 localhost 连不上 Windows | WSL2 NAT 模式下 localhost 不转发 | 用 `ip route show default` |

### GUI 打通（7/13）— 核心结论
WSLg 的 RDP RAIL 转发只处理 X11 窗口（通过 XWayland）。Qt 原生 Wayland surfaces 像素数据不转发。**解决方案是强制 `QT_QPA_PLATFORM=xcb`**。

## 6. SDK 档案位置

| 设备 | SDK 路径 | 内容 |
|:--|:--|:--|
| Spar Qi 肌电手环 | `D:\Dev\sparqi-env\` | ✅ SDK + .venv(Python 3.10) + wheel + emg_data + sync_data |
| SparQi Workbench | `D:\Dev\sparmqi-workbench\` | ✅ v1.1 + scan_devices.py + test_band794.py |
| NOKOV 动捕 | `D:\动捕+机电手环资料\NOKOV\NOKOV\` | XING_Python_SDK-2.4.0 + XINGYING 安装包 + C#/Linux SDK + PDF 手册 |

## 7. 待解决问题（仅当前主攻任务）

- 🟡 Band3BA start_capture ACK 超时 — 待重启手环回归测试
- 🟡 Band794 有效采样率 682Hz — 待排查（可能 BLE 连接间隔限制）
- 🟡 SPAR Qi 14 电极→9 通道映射 — 待拍内侧照片确认
- 🟡 IMU 模块硬件验证 — 待启用 IMU 采集测试
- 🟡 Workbench GUI 未弹出 — 需在 Windows 图形会话中直接运行
- 🟡 Workbench 下拉框不触发自动切换连接 — 需加 Connect 按钮
- 🟡 录制时未保存 metadata.json
- 🟡 NOKOV 动捕 XINGYING 连接
- 🟡 四设备同步框架 `sync_main.py`

## 8. 参考文档索引

| 文档 | 内容 |
|------|------|
| `08_周报与汇报/阶段回顾_机械臂控制完结_20260714.md` | 📦 机械臂控制完结归档 |
| `09_项目管理/完整体系实施路线图_20260711.md` | 四设备同步采集规划 |
| `09_项目管理/任务看板.md` | 当前任务看板 |
| `../Dev/sparmqi-workbench/docs/devlog/2026-07-14_双设备支持.md` | 手环双设备打通记录 |
| `../Dev/sparmqi-workbench/docs/devlog/2026-07-13_项目初始化.md` | Workbench 初始开发 |
| `../Dev/data-collection/docs/debug-log/2026-07-12_手套USB直通排查.md` | 手套打通记录 |
| `../Dev/data-collection/docs/debug-log/2026-07-13_GUI打通全记录.md` | GUI 打通记录 |
| `07_学习笔记/传感器与信号处理/D435i相机打通记录_20260710.md` | D435i SDK |
| `07_学习笔记/传感器与信号处理/多设备同步采集体系深度探索_20260711.md` | 同步架构探索 |
| `07_学习笔记/嵌入式开发/新硬件接入通用方法论_20260710.md` | 硬件接入方法论 |

## 9. 一键启动命令（当前生效）

```powershell
# SparQi Workbench (手环可视化)
D:\Dev\sparqi-env\.venv\Scripts\python.exe d:\Dev\sparmqi-workbench\workbench.py

# TouchGlove 手套
# 窗口A: TCP 桥（常驻后台）
python D:\Dev\data-collection\scripts\glove_serial_bridge.py
# 窗口B: GUI 仪表盘（WSLg 窗口弹出）
wsl -d Ubuntu-22.04 bash D:\Dev\data-collection\scripts\wsl_gui_launcher.sh