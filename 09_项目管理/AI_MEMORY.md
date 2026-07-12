# AI 记忆管理文件

> **用途**：本文件帮助 AI 助手在每次对话中快速了解项目全貌，实现持续跟进。
> **维护规则**：每次与 AI 协作完成重要工作后，更新本文件对应的部分。
> **最后更新**：2026-07-12 23:30

---

## 1. 项目基本信息

| 项目 | 内容 |
|------|------|
| **项目名称** | 假肢机械臂 |
| **项目路径** | `d:\假肢机械臂\`（文档）+ `D:\Dev\arm-ble\`（nRF52固件）+ `D:\Dev\arm-ble-s3\`（ESP32-S3固件）+ `D:\Dev\arm-ble-gui\`（上位机）+ `D:\Dev\data-collection\`（数据采集） |
| **GitHub** | `prosthetic-robotic-arm` |
| **负责人** | （你的名字 / 年级：大二下） |
| **开始时间** | 2026年6月 |
| **当前阶段** | ✅ ③号板联调 | ✅ 全链路交付 | ✅ v2.10 长按区分 | ✅ D435i 相机打通 | ✅ WSL2 环境就绪 | ✅ TouchGlove 手套打通 |

## 2. 开发环境

| 项目 | 路径 | GitHub | 工具 |
|------|------|------|------|
| 文档管理仓库 | `d:\假肢机械臂\` | prosthetic-robotic-arm | Git + GitHub |
| nRF52 固件（当前主交付） | `D:\Dev\arm-ble\` | arm-ble-firmware | PlatformIO（nordicnrf52） |
| ESP32-S3 固件（备用） | `D:\Dev\arm-ble-s3\` | arm-ble-s3-firmware | PlatformIO（espressif32） |
| 上位机 GUI | `D:\Dev\arm-ble-gui\` | arm-ble-gui | Qt 6.11 + CMake + MSVC |
| 数据采集 Pipeline | `D:\Dev\data-collection\` | 本地 | WSL2 + Python 3.10/3.11 + ONNX Runtime GPU |

## 3. 设备打通状态

| 设备 | 接口 | 环境 | 状态 |
|:--|:--|:--|:--:|
| D435i 相机 | USB 3.2 | Windows 原生 | ✅ 四路流 + 内参 |
| nRF52840 BLE 桥 | UART TX D0 | 裸机 | ✅ v2.10 主交付 |
| ESP32-S3 BLE 桥 | UART TX GPIO17 | 裸机 | ✅ v1-final 备用 |
| **TouchGlove 手套** | **COM5→TCP→WSL2** | **WSL2 + CUDA** | **✅ 7/12 打通** |
| Spar Qi 手环 | BLE→COM7 | Windows Python 3.10 | ⬜ 待硬件 |
| NOKOV 动捕 | 局域网 | Windows | ⬜ 待硬件 |

### TouchGlove 连接架构（7/12 打通）

```
手套 STM32 (COM5) → Windows bridge.py (TCP 0.0.0.0:12345)
  → WSL2 gateway (172.25.176.1) → socat → /tmp/ttyGlove
  → Python SDK → CUDA ONNX dense 推理 → 5×32×32×3 force+disp
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

## 5. 关键技术踩坑（手套打通总结）

| # | 坑 | 根因 | 教训 |
|:--:|------|------|------|
| 1 | usbipd "Device in error state" ×7 | usbipd-win 5.3.0 与 STM32 CDC 不兼容 | 同错误 3 次换路线 |
| 2 | WSL2 localhost 连不上 Windows | WSL2 NAT 模式下 localhost 不转发 | 用 `ip route show default` |
| 3 | nameserver IP 不是 Windows | `10.255.255.254` 是 Hyper-V DNS | 同上 |
| 4 | 命令行多层引号嵌套 | PowerShell 吃掉单引号/`&`/`!` | 写成脚本文件再调用 |

**正确流程**：确认 COM5 → bridge.py (0.0.0.0:12345) → 拿 gateway IP → socat 建 PTY → SDK 直连。总耗时 < 3 分钟。

## 6. 待解决问题

- ❌ 夹爪舵机故障（待学长更换）
- 🟡 CodexPad-C10 手柄（待到手）
- 🟡 arm-ble-gui BLE 设备列表不显示
- 🟡 舵机限位/角度 / GX12 母头引脚（等学长确认）
- 🟡 TouchGlove GUI 启动 + glove_collect.py 采集脚本（下一步）
- 🟡 手套 soft filter / 校准 SOP（使用前需确认）

## 7. 学习笔记索引

| 笔记 | 内容 |
|------|------|
| `07_学习笔记/传感器与信号处理/D435i相机打通记录_20260710.md` | D435i SDK + 四路流 + 内参 |
| `07_学习笔记/传感器与信号处理/多设备同步采集体系深度探索_20260711.md` | D435i + TouchGlove + BLE 同步架构 |
| `07_学习笔记/嵌入式开发/新硬件接入通用方法论_20260710.md` | 新硬件接入标准流程 |
| `../Dev/data-collection/docs/debug-log/2026-07-12_手套USB直通排查.md` | 手套打通全记录 + 踩坑总结 |
| `09_项目管理/完整体系实施路线图_20260711.md` | 项目整体规划 |