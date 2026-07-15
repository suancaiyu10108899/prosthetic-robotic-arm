# CLAUDE.md — 多设备同步数据采集

> 🤖 项目 AI 入口。深入此项目时先读这个。
> 最后更新：2026-07-15

---

## 当前阶段

**🔵 设备打通 → 同步框架开发阶段**

已完成：四个设备逐一打通（D435i✅ SparQi×2✅ TouchGlove✅）
当前：双SparQi手环同步采集方案
下一步：四设备统一同步框架 `sync_main.py`

## 已完成事项

| # | 事项 | 日期 | 状态 |
|---|------|------|:--:|
| 1 | D435i 四路流+内参验证 | 7/10 | ✅ |
| 2 | SparQi Band3BA BLE打通 | 7/13 | ✅ ACK超时待回归 |
| 3 | TouchGlove USB→WSL2→GUI全通 | 7/13 | ✅ |
| 4 | SparQi Band794 BLE全链路 | 7/14 | ✅ |
| 5 | Workbench v1.0→v1.6 | 7/13-14 | ✅ |
| 6 | 机械臂控制完结归档 | 7/14 | ✅ |

## 待推进 Top 5

| 优先级 | 任务 | 状态 |
|:--:|------|:--:|
| P1 | SparQi 双设备同步采集方案 — 需两个COM适配器 | 🟡 |
| P1 | Band3BA ACK超时回归 | 🟡 |
| P1 | Band794 有效采样率排查（~682Hz vs 标称1000Hz） | 🟡 |
| P1 | IMU陀螺仪数据验证（摇手环看是否非零） | 🟡 |
| P2 | NOKOV动捕 XINGYING连接 | 🟡 |

> 完整任务看板 → `任务看板.md`

## 设备速查

| 设备 | MAC/ID | 状态 |
|:--|:--|:--:|
| SparQi Band3BA | `ED:9D:0F:48:F3:BA` | ✅ 待回归 |
| SparQi Band794 | `ED:A4:A3:B8:07:94` | ✅ |
| D435i | USB 3.2 | ✅ |
| TouchGlove | COM5→TCP→WSL2 | ✅ |
| NOKOV | 10.1.1.198 | 🟡 |

## 技术参数速查

- **SparQi SDK**: ResearchKit_SDK v1.0.0 (.pyd, cp310, 闭源)
- **手环采样率**: 标称1000Hz, 9ch EMG + 6轴IMU
- **BLE参数**: Broadcom适配器→COM6, MTU 247, PHY 2M, 连接间隔15ms
- **手套架构**: STM32(COM5)→TCP bridge→WSL2→CUDA ONNX→5×32×32×3 force+disp
- **手套5通道 Sensor ID**: `55045D1D9DF60905` `55075C8B9DF7BA0C` `550265A09DF60939` `5505DFAC9DF7BA06` `5505AE8F9DF7BB27`

## 开发环境

| 组件 | 路径 | 技术 |
|------|------|------|
| 手环工作台 | `D:\Dev\sparmqi-workbench\` | PyQt5+pyqtgraph+scipy |
| 手套管线 | `D:\Dev\data-collection\` | WSL2+Python 3.10+CUDA |
| SparQi Python环境 | `D:\Dev\sparqi-env\.venv` (Python 3.10) | ResearchKit SDK |
| D435i | Windows Python 3.11 + pyrealsense2 | — |

## 一键启动

```powershell
# SparQi Workbench (桌面双击)
C:\Users\tb137\Desktop\SparQi_Workbench.bat

# TouchGlove 手套
python D:\Dev\data-collection\scripts\glove_serial_bridge.py    # 窗口A
wsl -d Ubuntu-22.04 bash D:\Dev\data-collection\scripts\wsl_gui_launcher.sh  # 窗口B

# BLE扫描诊断
D:\Dev\sparqi-env\.venv\Scripts\python.exe D:\Dev\sparmqi-workbench\scripts\scan_devices.py
```

## 踩坑记录（最近 5 条）

| # | 坑 | 修复 |
|:--:|------|------|
| 1 | Band794 有效采样率~682Hz | BLE连接间隔15ms → 约67批次/秒天花板 |
| 2 | Band3BA start_capture ACK超时 | 手环固件状态问题(Band794一次就过)，重启手环+6次重试 |
| 3 | Workbench GUI不弹出 | 缺`self.show()`+多线程竞争COM6 |
| 4 | COM6 NRF_ERROR_TIMEOUT | SDK未正常close()锁住串口，拔插适配器 |
| 5 | TouchGlove usbipd不兼容 | usbipd-win与STM32 CDC不兼容，改用TCP bridge路线 |

## 参考文档

| 文档 | 路径 |
|------|------|
| 完整任务看板 | `任务看板.md` |
| 问题追踪 | `问题追踪.md` |
| 终态架构设计 | `架构设计/完整体系实施路线图_20260711.md` |
| Workbench开发规划 | `架构设计/SparQi_Workbench_开发规划_20260713.md` |
| 设备打通记录 | `设备打通记录/` |