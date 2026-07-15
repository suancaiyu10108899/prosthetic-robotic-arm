# 上位机 — 假肢机械臂控制与调试工具

> **创建时间**：2026-06-12
> **当前阶段**：BLE 调试器（arm-ble-gui）开发中

---

## 项目列表

| 项目 | 路径 | 用途 | 技术栈 | 状态 |
|------|------|------|--------|:---:|
| arm-ble-gui | `D:\Dev\arm-ble-gui\` | BLE 调试验证工具 | Qt 6.11.0 + C++17 + CMake | 🔧 开发中 |

---

## arm-ble-gui 定位

调试工具，不是最终产品控制器。功能：

- 扫描附近 BLE 设备
- 连接 nRF52840 蓝牙板（NUS 协议）
- 双向收发数据（手机式控制 + 串口监视替代）
- 预设指令按钮（舵机控制占位）

等遥控器协议到手后，可在此基础上生长为正式控制器。

---

## ⚠️ Qt 6.8+ 改名记录

> **日期**：2026-06-12
> **发现**：在 Qt Maintenance Tool 中找不到 "Qt Bluetooth" 组件。

- **原因**：Qt 6.8 起，`Qt Bluetooth` 和 `Qt NFC` 合并为一个元模块 **Qt Connectivity**
- **在 Maintenance Tool 中**：勾选 `Qt Connectivity` 即可，它会自动包含 Bluetooth + NFC 子模块
- **在 CMake 中**：仍然使用 `find_package(Qt6 REQUIRED COMPONENTS Bluetooth)` ，不受改名影响
- **在代码中**：`#include <QBluetoothDeviceDiscoveryAgent>` 等头文件路径不变

> 📌 这条记录可以节省下一个人（或未来的自己）半小时的搜索时间。

---

## 环境依赖

| 工具 | 版本 | 备注 |
|------|------|------|
| Qt | 6.11.0 msvc2022_64 | 需勾选 Qt Connectivity |
| CMake | 4.3.0 | |
| MSVC | VS 2022 Community | 需运行 VsDevShell |
| Ninja | VS 内嵌 | 通过 VsDevShell 可用 |
| PlatformIO | 6.1.19 (pip) | 用于烧录 nRF52840 固件 |

---

## 构建命令

```powershell
# 每次新开终端先激活 MSVC 环境
. .\scripts\dev-shell.ps1

# 配置
cmake --preset win-msvc-debug

# 编译
cmake --build --preset win-msvc-debug

# 运行
.\build\win-msvc-debug\src\app\arm-ble-gui.exe