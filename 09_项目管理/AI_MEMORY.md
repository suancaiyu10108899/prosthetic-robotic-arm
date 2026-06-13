# AI 记忆管理文件

> **用途**：本文件帮助 AI 助手在每次对话中快速了解项目全貌，实现持续跟进。
> **维护规则**：每次与 AI 协作完成重要工作后，更新本文件对应的部分。
> **最后更新**：2026-06-13 17:48

---

## 1. 项目基本信息

| 项目 | 内容 |
|------|------|
| **项目名称** | 假肢机械臂 |
| **项目路径** | `d:\假肢机械臂\`（文档） + `D:\Dev\arm-ble\`（固件） + `D:\Dev\arm-ble-gui\`（上位机） |
| **GitHub** | `prosthetic-robotic-arm` / `arm-ble-firmware` / `arm-ble-gui` |
| **负责人** | (你的名字 / 年级：大二下) |
| **实验室** | (实验室名称) |
| **开始时间** | 2026年6月 |
| **当前阶段** | 🔧 VR LOOKBON 手柄调试 — 纯Central扫描器 count=1 bug确认，v1.4 双角色 `begin(1,1)` 待烧录测试 |

## 2. 当前任务背景

- 老师原有机械臂被**剧组借用改造**
- 需要用**未来工场8200pro树脂**做光固化打印
- 同时有一**另一只手**（合作方设计）的零件也要打印
- 另一只手包含：接受腔、尼龙件（左盖/把/箍/连杆/销）、树脂件（E-1/E-2）

### 电控系统架构（已确认）

```
蓝牙信号源 (VR LOOKBON / CodexPad-C10)
    │ BLE
    ▼
┌─ 电池模块 (电池箱) ────────────────┐
│  ① Adafruit Feather nRF52840 Express   │  ← 🔴 当前任务：手柄 BLE 连接
│     (nRF52840, MicroUSB 供电+编程)     │
│  ② 电压转换板                         │  ← 纯硬件，无需编程
└──────────┬──────────────────────────┘
           │ 有线信号 (UART/SPI/I2C)
           ▼
┌─ 机械臂控制板 ──────────────────────┐
│  ③ STM32/cybathlon   ← 发PWM        │  ← 用塔克DAP无线调试
└────────────────────────────────────┘
```

- **板①**：**Adafruit Feather nRF52840 Express**（nRF52840 芯片，MAC: D3:52:88:3A:06:27）
- **板②**：电压转换，纯硬件，无需编程
- **板③**：STM32 控制板，用塔克 DAP（ESP32-S3, 30m）无线调试（在学长处）

### 开发环境

| 项目 | 路径 | 工具 |
|------|------|------|
| 文档管理仓库 | `d:\假肢机械臂\` | Git + GitHub |
| 固件开发 | `D:\Dev\arm-ble\` | PlatformIO 6.1.19 (pip) |
| 上位机开发 | `D:\Dev\arm-ble-gui\` | Qt 6.11.0 + CMake + MSVC 2022 |
| GitHub (固件) | https://github.com/suancaiyu10108899/arm-ble-firmware | ✅ |
| GitHub (上位机) | https://github.com/suancaiyu10108899/arm-ble-gui | ✅ |

> PlatformIO 命令入口：`python -m platformio run --project-dir=d:\Dev\arm-ble --target upload`

## 3. 目录结构（当前）

```
d:\假肢机械臂\
├── 00_原始压缩包归档/
├── 01_机械结构/
│   ├── 原版机械臂/
│   └── 另一只手/
├── 02_电子与控制/
│   ├── 系统架构说明.md
│   ├── 元器件采购清单.md
│   ├── 电池模块/Arduino蓝牙板/
│   └── ...
├── 03_嵌入式代码/原版机械臂_Arduino/
├── 04_上位机/README.md
├── 06_文献与参考资料/
│   ├── codex_pad_arduino_lib/
│   ├── codex_pad_c10/
│   ├── codex_pad_guide/
│   ├── vr-ble/
│   ├── vr-ble-arduino/
│   └── vr-ble-python-pc/
├── 07_学习笔记/
├── 08_周报与汇报/
│   └── 周报_第24周_20260613.md
└── 09_项目管理/
```

## 4. 重要约定与规则

1. **STL/SolidWorks 大文件**：不入 Git（`.gitignore` 已配置），AI 不读取内容
2. **文件命名规范**：你画零件加`【打印件/加工件/铝方管】`前缀，他人文件保留原名
3. **打印材料**：未来工场8200pro树脂（光固化）+ 尼龙件
4. **代码与文档分离**：代码在 `D:\Dev\arm-ble\` 和 `D:\Dev\arm-ble-gui\`（纯英文），文档在 `d:\假肢机械臂\`

## 5. 🔴 关键技术发现（2026-06-13 下午更新）

### Bluefruit.begin 参数顺序坑

`Bluefruit.begin(peripheralCount, centralCount)` — **第一个参数是 Peripheral，第二个才是 Central**。v0.2-v0.8 全部写反了 `begin(1,0)` = 1 Peripheral + 0 Central（扫描器从未以 Central 角色启动）。

### 纯 Central 模式扫描器 bug（v1.3 证实）

`begin(0,1)` 纯 Central 模式下，`onScan` 回调**只触发一次就永久休眠**：
- v1.0: `start(10000)` + `setStopCallback` → count=1 卡死
- v1.1: `start(0)` 无限扫描 → 同样 count=1
- v1.3: 全量日志证实只扫到一台陌生电脑 `48:05:E2:0F:60:ED`，onScan 不再触发
- v1.2: 跳过扫描器 MAC直连 → `Central.connect()` busy/failed（库需要广播缓存）
- **v1.4**: `begin(1,1)` 双角色 — 正在验证中

### 手柄连接现状

| 设备 | 能力 |
|------|------|
| 手机 (nRF Connect) | ✅ 扫描 + 连接 + 收 Notify (A1-A7, D1-D8) |
| PC (Windows 蓝牙) | ✅ 扫描到 57 个设备（含 LOOKBON） |
| nRF52840 begin(0,1) 纯Central | ❌ onScan 只触发一次后永久休眠 (v1.0-v1.3) |
| nRF52840 MAC 直连 | ❌ Central.connect() busy/failed (v1.2) |
| nRF52840 begin(1,1) 双角色 | 🔬 v1.4 待烧录测试 |
| PC (Qt LookbonReceiver) | ⚠️ GAP OK，服务发现待完成 |

### arm-ble-gui 新增 LOOKBON 直连

`ble/LookbonReceiver.h/cpp` — GAP 层连接已验证通过（3 分钟持续）。`connectToDevice("0D:CE:99:03:5D:D2")` → `connected` 信号触发，手动关机正常断连。Qt 6.11 128-bit UUID (AE30/AE02) 服务发现待调试。

## 6. 待解决问题

- 🔴 **nRF52840 扫描器 bug**：v1.3 全量日志证实纯Central下 onScan 只触发一次 → v1.4 双角色 `begin(1,1)` 待烧录
- 🔴 **Qt LookbonReceiver 服务发现**：`discoverServices` 后 AE30 匹配需验证
- 🔴 **③号板通信接口**：UART/SPI/I2C协议、引脚、波特率未知（在学长处）
- 🟡 **CodexPad-C10 手柄**：待到手，协议已分析完毕

## 7. 固件版本历程

| 版本 | begin 参数 | 策略 | 结果 |
|:---:|------|------|------|
| v0.2 | `(1,1)` | 双角色 + 扫广播名 | 扫到 1 台路过电脑 |
| v0.3 | `(1,1)` | 去 UUID 过滤 + Active Scan | 同上 |
| v0.4 | `(1,0)` ❌ | 纯 Central + 无过滤 | `count=1` 卡住 |
| v0.5 | `(1,0)` ❌ | MAC 直连 + delay | Central busy 循环 |
| v0.6 | `(1,0)` ❌ | 异步 MAC 直连 | Central busy 循环 |
| v0.7 | `(0,1)` ✅ | 纯 NUS Peripheral | 等 GUI 数据 |
| v0.8 | `(1,0)` ❌ | scan+report 连接 | 无扫描回调 |
| v1.0 | `(0,1)` ✅ | 纯主机 + start(10000) | `count=1` 仍卡住 |
| v1.1 | `(0,1)` ✅ | start(0) 无限扫描 | `count=1` 卡死 (17:34) |
| v1.2 | `(0,1)` ✅ | 跳过扫描器 MAC直连 | `Central.connect()` busy/failed |
| v1.3 | `(0,1)` ✅ | 全量日志诊断 | 仅扫到陌生电脑, onScan永久停 |
| v1.4 | `(1,1)` 🔬 | 双角色 + 全量日志 | 待烧录测试 |

## 8. 学习笔记索引

| 笔记 | 路径 | 内容 |
|------|------|------|
| 笔记1 | `07_学习笔记/嵌入式开发/nRF52_BLE传感器与舵机控制_20260610.md` | BLE通信、舵机映射 |
| 笔记2 | `07_学习笔记/控制算法/IIR滤波与死区滤波_20260610.md` | IIR低通、死区 |
| 笔记3 | `07_学习笔记/传感器与信号处理/...EMG肌电控制_20260610.md` | 传感器原理 |
| 笔记4 | `07_学习笔记/机械设计/3D打印工艺与实操积累_20260611.md` | 光固化、螺丝收纳 |
| 笔记5 | `07_学习笔记/嵌入式开发/Qt_BLE上位机开发与编译_20260612.md` | Qt 6.11 BLE |
| 笔记6 | `07_学习笔记/嵌入式开发/Windows_BLE蓝牙调试流程_20260612.md` | BLE三层模型 |
| 笔记7 | `07_学习笔记/嵌入式开发/CodexPad_C10手柄BLE协议分析_20260612.md` | C10协议 |
| 笔记8 | `07_学习笔记/嵌入式开发/VR_BLE手柄LOOKBON协议分析_20260612.md` | LOOKBON协议 |
| 日志1 | `D:\Dev\arm-ble\docs\devlog\2026-06-11_环境搭建.md` | 环境搭建 |
| 日志2 | `D:\Dev\arm-ble\docs\devlog\2026-06-11_BLE验证.md` | BLE双向验证 |
| 日志3 | `D:\Dev\arm-ble-gui\docs\devlog\2026-06-12_项目初始化.md` | GUI初始化 |
| 日志4 | `D:\Dev\arm-ble\docs\devlog\2026-06-13_手柄调试图鉴.md` | 手柄调试 (v0.2-v1.4, 11版) |