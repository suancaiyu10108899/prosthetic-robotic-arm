# AI 记忆管理文件

> **用途**：本文件帮助 AI 助手在每次对话中快速了解项目全貌，实现持续跟进。
> **维护规则**：每次与 AI 协作完成重要工作后，更新本文件对应的部分。
> **最后更新**：2026-06-13 19:18

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
| **当前阶段** | ✅ VR LOOKBON 手柄调试完成 — 扫描/GAP/CCCD/Notify/解析 全链路打通 |

## 2. 当前任务背景

- 老师原有机械臂被**剧组借用改造**
- 需要用**未来工场8200pro树脂**做光固化打印
- 同时有一**另一只手**（合作方设计）的零件也要打印

### 电控系统架构（已确认）

```
蓝牙信号源 (VR LOOKBON / CodexPad-C10)
    │ BLE
    ▼
┌─ 电池模块 (电池箱) ────────────────┐
│  ① Adafruit Feather nRF52840 Express   │  ← ✅ 手柄 BLE 连接全通
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

## 5. 🔴 关键技术发现（2026-06-13）

### Bluefruit.begin 参数顺序坑

`Bluefruit.begin(peripheralCount, centralCount)` — **第一个参数是 Peripheral，第二个才是 Central**。

### 纯 Central 模式扫描器 bug

`begin(0,1)` 纯 Central 模式下，`onScan` 回调只触发一次后永久休眠 → 通过 `begin(1,1)` + loop 重启绕过。

### GATT 发现不兼容

Adafruit 库 `BLEClientService::discover()` 与 LOOKBON 不兼容 → 参照 Python `ble_python.py` 跳过 discover，直接 `sd_ble_gattc_write` 写 CCCD。

### SoftDevice 中断上下文阻塞

`onConnect` 回调在 SoftDevice 中断上下文中执行，`delay(2000)` 阻塞事件处理导致手柄超时断连 → 将 CCCD 写入移到 loop 中温和执行。

### LOOKBON 协议：单字节编码

高 nibble = 事件类型 (0xA=单击/0xB=长按/0xC=释放/0xD=方向)，低 nibble = 按键/方向编号。

### 手柄连接现状

| 层 | 状态 | 版本 |
|----|:---:|:---:|
| 扫描 LOOKBON | ✅ | v1.5 |
| GAP 连接 | ✅ | v1.5 |
| CCCD 写入 | ✅ | v1.9 |
| Notify 数据接收 | ✅ | v2.4 |
| 协议解析 (BTN/X/Y) | ✅ | v2.6 |
| 连接后停扫描 | ✅ | v2.5 |

## 6. 待解决问题

- 🔴 **③号板通信接口**：UART/SPI/I2C协议、引脚、波特率未知（在学长处）
- 🟡 **CodexPad-C10 手柄**：待到手，协议已分析完毕
- 🟡 **舵机控制验证**：BTN/X/Y 映射到舵机需要实测

## 7. 固件版本历程

| 版本 | 策略 | 结果 |
|:---:|------|------|
| v1.5 | 被动扫描 + loop 10s 重启 | ✅ 扫到 LOOKBON |
| v1.6-v1.8 | GATT discover | ❌ 不兼容 |
| v1.9 | 跳过 discover 直写 CCCD | ✅ CCCD OK |
| v2.0-v2.3 | 事件回调 + 全量日志诊断 | 发现 onConnect 阻塞 |
| **v2.4** | **loop 温和 CCCD** | **✅ 数据通道打通** |
| v2.5 | 连接后停扫描 | ✅ |
| **v2.6** | **单字节解析器** | **✅ BTN/X/Y 全部正确** |

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
| 日志4 | `D:\Dev\arm-ble\docs\devlog\2026-06-13_手柄调试图鉴.md` | 手柄调试 (v1.0-v2.6 完整) |