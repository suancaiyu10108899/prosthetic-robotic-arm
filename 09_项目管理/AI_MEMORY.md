# AI 记忆管理文件

> **用途**：本文件帮助 AI 助手在每次对话中快速了解项目全貌，实现持续跟进。
> **维护规则**：每次与 AI 协作完成重要工作后，更新本文件对应的部分。
> **最后更新**：2026-07-13 12:10

---

## 1. 项目基本信息

| 项目 | 内容 |
|------|------|
| **项目名称** | 假肢机械臂 |
| **项目路径** | `d:\假肢机械臂\`（文档）+ `D:\Dev\arm-ble\`（nRF52固件）+ `D:\Dev\arm-ble-s3\`（ESP32-S3固件）+ `D:\Dev\arm-ble-gui\`（上位机）+ `D:\Dev\data-collection\`（数据采集） |
| **GitHub** | `prosthetic-robotic-arm` |
| **负责人** | （你的名字 / 年级：大二下） |
| **开始时间** | 2026年6月 |
| **当前阶段** | ✅ ③号板联调 | ✅ v2.10 长按区分 | ✅ D435i 相机打通 | ✅ TouchGlove 手套打通 (含 GUI) |

## 2. 开发环境

| 项目 | 路径 | GitHub | 工具 |
|------|------|------|------|
| 文档管理仓库 | `d:\假肢机械臂\` | prosthetic-robotic-arm | Git + GitHub |
| nRF52 固件（当前主交付） | `D:\Dev\arm-ble\` | arm-ble-firmware | PlatformIO（nordicnrf52） |
| ESP32-S3 固件（备用） | `D:\Dev\arm-ble-s3\` | arm-ble-s3-firmware | PlatformIO（espressif32） |
| 上位机 GUI | `D:\Dev\arm-ble-gui\` | arm-ble-gui | Qt 6.11 + CMake + MSVC |
| 数据采集 Pipeline | `D:\Dev\data-collection\` | 本地 | WSL2 + Python 3.10 + ONNX Runtime GPU (CUDA 12) |

## 3. 设备打通状态

| 设备 | 接口 | 环境 | 状态 |
|:--|:--|:--|:--:|
| D435i 相机 | USB 3.2 | Windows 原生 | ✅ 四路流 + 内参 |
| nRF52840 BLE 桥 | UART TX D0 | 裸机 | ✅ v2.10 主交付 |
| ESP32-S3 BLE 桥 | UART TX GPIO17 | 裸机 | ✅ v1-final 备用 |
| **TouchGlove 手套** | **COM5→TCP→WSL2** | **WSL2 + CUDA** | **✅ 7/12 打通 → 7/13 GUI 打通** |
| Spar Qi 手环 | BLE→COM7 | Windows Python 3.10 | ⬜ 待硬件 |
| NOKOV 动捕 | 局域网 | Windows | ⬜ 待硬件 |

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

### 手套 USB 打通（7/12）
| # | 坑 | 根因 | 教训 |
|:--:|------|------|------|
| 1 | usbipd "Device in error state" ×7 | usbipd-win 5.3.0 与 STM32 CDC 不兼容 | 同错误 3 次换路线 |
| 2 | WSL2 localhost 连不上 Windows | WSL2 NAT 模式下 localhost 不转发 | 用 `ip route show default` |
| 3 | 命令行多层引号嵌套 | PowerShell 吃掉单引号/`&`/`!` | 写成脚本文件再调用 |

### GUI 打通（7/13）— 完整排查链路
| # | 症状 | 根因 | 修复 |
|:--:|------|------|------|
| 4 | PySide6 `import` 成功但 QApp 崩溃 | 缺失 `libxcb-cursor0`, `libxcb-icccm4`, `libwayland-cursor0` | `sudo apt install` + PySide6 6.11.1 |
| 5 | 字体异常 | `fonts-noto-cjk` 未安装 | `sudo apt install fonts-noto-cjk` |
| 6 | **核心问题**: 企鹅图标在任务栏但窗口不可见 | **WSLg RDP RAIL 不转发 Qt 原生 Wayland surfaces**（GTK/XWayland 正常） | 见下文 |
| 7 | xcb 插件加载失败 (PySide6 6.11.1) | 6.11.1 的 `libqxcb.so` 缺 `libxcb-shape.so.0` + `libxcb-cursor.so.0` | `sudo apt install libxcb-shape0` |
| 8 | xcb 仍然失败 | WSL `--shutdown` 后 ldconfig 缓存过期 | `sudo ldconfig` + 降级到 PySide6 6.5.3 |
| 9 | WSLg 虚拟屏幕 640×480 | WSLg 在无活跃 X11 连接时缩放到最小分辨率 | 创建 `~/.wslgconfig` 强制 1920×1080（后来清空恢复自动检测） |

### GUI 问题核心诊断方法
```
1. gnome-calculator (GTK3/XWayland) → ✅ 可见 → WSLg 本身正常
2. PySide6 简单窗口 (Wayland) → ❌ 不可见 → Qt Wayland 有问题
3. PySide6 简单窗口 (xcb) → ❌ 崩溃 → 缺失 libxcb-shape.so.0
4. 安装 libxcb-shape0 → ✅ xcb 正常 → dense_dashboard.py 成功!
```

**关键结论**：WSLg 的 RDP RAIL 转发只处理 X11 窗口（通过 XWayland）。Qt 原生 Wayland surfaces 虽然成功创建并注册 Rail 映射，但像素数据不转发。**解决方案是强制 `QT_QPA_PLATFORM=xcb`**。

## 6. 待解决问题

- ❌ 夹爪舵机故障（待学长更换）
- 🟡 CodexPad-C10 手柄（待到手）
- 🟡 arm-ble-gui BLE 设备列表不显示
- 🟡 舵机限位/角度 / GX12 母头引脚（等学长确认）
- 🟡 手套 soft filter / 校准 SOP（使用前需确认）

## 7. 新增脚本清单（data-collection/scripts/）

| 脚本 | 用途 |
|------|------|
| `glove_serial_bridge.py` | Windows 端 COM5→TCP :12345 桥（常驻后台） |
| `wsl_connect_glove.sh` | WSL2 端 socat 连接 + PTY 创建 |
| `test_glove_wsl.py` | SDK 5 通道连接验证 |
| `glove_collect.py` | 采集 force+disp .npy 数据 |
| `wsl_gui_launcher.sh` | **一键启动**: socat + dense_dashboard.py（xcb 模式） |
| `wsl_test_one_shot.sh` | 一键 SDK 验证（socat + 5 通道） |
| `wsl_test_simple_window.sh` | PySide6 极简窗口测试（30s 大红窗口） |
| `wsl_test_x11.sh` | X11 模式窗口测试 |
| `wsl_diag_qt.sh` | Qt 平台插件诊断 |
| `wsl_diag_display.sh` | WSLg 环境变量 + DRI + 屏幕诊断 |
| `fix_pyside6.sh` | 安装 PySide6 系统依赖 + 升级 |
| `fix_pyside6_downgrade.sh` | PySide6 6.11.1 → 6.5.3 降级（恢复 xcb 兼容） |
| `fix_xcb.sh` | xcb 依赖修复 |
| `fix_xcb_shape.sh` | libxcb-shape0 安装 + xcb 验证 |
| `check_wslg.sh` | WSLg PySide6/matplotlib 快速诊断 |
| `start_glove.ps1` | PowerShell 一键启动脚本（含 --gui 开关） |

## 8. 配置文件变更

| 文件 | 变更 | 原因 |
|------|------|------|
| `c:\Users\tb137\.wslgconfig` | 创建后清空 | 曾强制 1920×1080，后恢复自动检测（WSLg 重启后正常） |
| `wsl_gui_launcher.sh` | `QT_QPA_PLATFORM=xcb` | 绕过 WSLg wayland 不转发 bug |
| PySide6 版本 | 6.5.3（从 6.11.1 降级） | 6.11.1 的 xcb 插件缺系统库依赖 |

## 9. 一键启动命令（当前生效）

```powershell
# 窗口A: TCP 桥（常驻后台）
python D:\Dev\data-collection\scripts\glove_serial_bridge.py

# 窗口B: GUI 仪表盘（WSLg 窗口弹出）
wsl -d Ubuntu-22.04 bash D:\Dev\data-collection\scripts\wsl_gui_launcher.sh
```

## 10. 学习笔记索引
| 笔记 | 内容 |
|------|------|
| `07_学习笔记/传感器与信号处理/D435i相机打通记录_20260710.md` | D435i SDK + 四路流 + 内参 |
| `07_学习笔记/传感器与信号处理/多设备同步采集体系深度探索_20260711.md` | D435i + TouchGlove + BLE 同步架构 |
| `07_学习笔记/嵌入式开发/新硬件接入通用方法论_20260710.md` | 新硬件接入标准流程 |
| `../Dev/data-collection/docs/debug-log/2026-07-12_手套USB直通排查.md` | 手套 USB 打通全记录 |
| `../Dev/data-collection/docs/debug-log/2026-07-13_GUI打通全记录.md` | GUI 打通全记录（本次） |
| `09_项目管理/完整体系实施路线图_20260711.md` | 项目整体规划 |