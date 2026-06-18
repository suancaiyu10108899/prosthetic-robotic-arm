# AI 记忆管理文件

> **用途**：本文件帮助 AI 助手在每次对话中快速了解项目全貌，实现持续跟进。
> **维护规则**：每次与 AI 协作完成重要工作后，更新本文件对应的部分。
> **最后更新**：2026-06-19 01:22

---

## 1. 项目基本信息

| 项目 | 内容 |
|------|------|
| **项目名称** | 假肢机械臂 |
| **项目路径** | `d:\假肢机械臂\`（文档）+ `D:\Dev\arm-ble\`（nRF52固件）+ `D:\Dev\arm-ble-esp32\`（ESP32替补）+ `D:\Dev\arm-ble-gui\`（上位机） |
| **GitHub** | `prosthetic-robotic-arm` |
| **负责人** | (你的名字 / 年级：大二下) |
| **开始时间** | 2026年6月 |
| **当前阶段** | ✅ ESP32 BLE+UART 全链路打通 (v6-final) | ❌ nRF52840 板1 报废 (12V 事故) | 🟡 盒子待定 |

## 2. 当前任务背景

- 老师原有机械臂被**剧组借用改造**
- 需要用**未来工场8200pro树脂**做光固化打印（3单合计 ¥944.70，发票已归档至 `00_原始压缩包归档/发票_20260615_944.70/`）

### 电控系统架构（已确认）

```
蓝牙信号源 (VR LOOKBON / CodexPad-C10)
    │ BLE
    ▼
┌─ 电池模块 (电池箱) ────────────────┐
│  ① BLE→UART 桥                      │
│     ✅ nRF52840 v2.9-final (板1 报废) │
│     ✅ ESP32 v6-final (替补, 可用)    │
│  ② 电压转换板                         │
└──────────┬──────────────────────────┘
           │ UART TX (D17=GPIO17, 115200, 3.3V)
┌─ 机械臂控制板 ──────────────────────┐
│  ③ STM32/cybathlon   ← 发PWM        │
└────────────────────────────────────┘
```

- **板① nRF52840**：Adafruit Feather nRF52840 Express（MAC: D3:52:88:3A:06:27）— **板1 12V 事故报废**
- **板① 替补 ESP32**：ESP32-WROOM-32 DevKit（MAC: 48:e7:29:a0:02:20）— **v6-final 验证通过**
- **板②**：电压转换，纯硬件
- **板③**：STM32，在学长处

### 开发环境

| 项目 | 路径 | 工具 |
|------|------|------|
| 文档管理仓库 | `d:\假肢机械臂\` | Git + GitHub |
| nRF52 固件 | `D:\Dev\arm-ble\` | PlatformIO (nordicnrf52 + Arduino) |
| ESP32 固件 | `D:\Dev\arm-ble-esp32\` | PlatformIO (espressif32 + Arduino) |
| GitHub (固件) | https://github.com/suancaiyu10108899/arm-ble-firmware | ✅ |

> PlatformIO 命令入口：`python -m platformio run --project-dir=<path> --target upload`

## 3. 当前交付状态 (2026-06-19)

### ESP32 替补板 (v6-final) ✅ 全链路打通

| 交付物 | 路径 | 状态 |
|--------|------|:---:|
| **固件 v6-final** | `D:\Dev\arm-ble-esp32\src\main.cpp` | ✅ (NimBLE + UART TX=D17, 示波器验证) |
| 协议解析器 | `D:\Dev\arm-ble-esp32\src\handle_parser.h/cpp` | ✅ (复用 nRF52 版) |
| platformio.ini | `D:\Dev\arm-ble-esp32\platformio.ini` | ✅ (含 NimBLE 依赖) |
| README | `D:\Dev\arm-ble-esp32\README.md` | ✅ (含 GATT UUID dump + 调试历程) |

### nRF52 板 (v2.9-final) ✅ BLE 全通, TX 波形验证

| 交付物 | 路径 | 状态 |
|--------|------|:---:|
| **固件 v2.9 (final)** | `D:\Dev\arm-ble\src\main.cpp` | ✅ (BLE 全通, UART TX=D0 波形验证) |
| 协议解析器 | `D:\Dev\arm-ble\src\handle_parser.h/cpp` | ✅ |
| platformio.ini | `D:\Dev\arm-ble\platformio.ini` | ✅ |
| README | `D:\Dev\arm-ble\README.md` | ✅ |

### 备份

| 文件 | 说明 |
|------|------|
| `docs/main_v2.9_final.cpp` | nRF52 最终生产固件 |
| `docs/main_v2.9_prod_backup.cpp` | v2.9 第二备份 |
| `docs/main_20260618_uart_test_backup.cpp` | 双引脚交替 TX 测试 |

### 技术验证

| 层 | nRF52840 | ESP32 |
|----|:---:|:---:|
| 扫描 LOOKBON | ✅ | ✅ |
| GAP 连接 | ✅ | ✅ |
| GATT 服务发现 | ✅ (直写 CCCD) | ✅ (getCharacteristics(true)) |
| CCCD 通知订阅 | ✅ (handles 7/67/131) | ✅ (4 channels) |
| Notify 数据接收 | ✅ | ✅ |
| 协议解析 (BTN/X/Y) | ✅ | ✅ |
| **UART TX 物理层（示波器验证）** | ✅ D0, 3.06V | ✅ D17, 3.3V |
| 电池供电自动启动 | ✅ | 🟡 待验证 |
| 电平兼容 (3.3V ↔ STM32) | ✅ | ✅ |
| 板子可用性 | ❌ (12V 报废) | ✅ |

## 4. 重要约定与规则

1. **STL/SolidWorks 大文件**：不入 Git（`.gitignore` 已配置），AI 不读取内容
2. **文件命名规范**：你画零件加`【打印件/加工件/铝方管】`前缀，他人文件保留原名
3. **打印材料**：未来工场8200pro树脂（光固化）+ 尼龙件
4. **代码与文档分离**：代码在 `D:\Dev\`（纯英文），文档在 `d:\假肢机械臂\`
5. **AI 辅助原则**：AI 帮你写代码、查文档、做分析，但物理直觉和独立排查能力不可替代。代码要能读懂、能修改。

## 5. 关键技术发现

### Bluefruit (nRF52) 系列

- `Bluefruit.begin(peripheralCount, centralCount)` — 第一个参数是 Peripheral，第二个是 Central
- 纯 Central 模式 onScan 只触发一次 → `begin(1,1)` + loop 重启绕过
- `BLEClientService::discover()` 与 LOOKBON 不兼容 → 直写 CCCD
- `onConnect` 回调在 SoftDevice 中断上下文 → `delay(2000)` 阻塞 → 移到 loop
- LOOKBON 协议：单字节编码（高 nibble=事件，低 nibble=按键）
- `while (!Serial)` USB CDC 死等 bug → 3 秒超时
- **A2(P0.30) 5V 损坏** → D0(P0.25) 替代 + 高驱动 H0H1 (3.06V)
- **SoftDevice 与 UARTE 寄存器直驱 TX 不冲突** — 已验证
- **GPIO 输入管全部击穿 (D1/A4/A5)** — 5V 倒灌 VDD 轨

### NimBLE-Arduino (ESP32) 系列 — 2026-06-18/19

| # | 发现 | 解决方案 |
|:--:|------|------|
| 1 | `connect()` 不能在 `NimBLEAdvertisedDeviceCallbacks::onResult()` 里调用 | 扫描回调只存 `g_targetAddr`，`connect()` 移到 `loop()` |
| 2 | `getCharacteristics(false)` 返回空 — `false` 只取本地缓存，发现阶段不填充 | 改为 `getCharacteristics(true)` 强制远端 ATT 读取 |
| 3 | 服务发现需要 4 秒延迟 — 连接握手后 GATT 表需要时间同步，2 秒不够 | `millis() - discoTime > 4000` |
| 4 | `dev->getName()` 返回 `std::string` 不是 Arduino `String` | 用 `std::string::find()` 和 `tolower()` |
| 5 | `[SUB] 0` ≠ 没收到数据 — `canNotify()` 可能因 UUID 属性解析不一致返回 false | 直接 `subscribe(true, callback)` 全量订阅 |

### LOOKBON GATT 服务结构 (UUID dump from ESP32)

| Service UUID | Characteristics |
|:---:|------|
| 0x1800 (Generic Access) | 0x2a00 (Device Name, Read) |
| 0xae30 | 0xae01(R) 0xae02(Notify) 0xae03(R) 0xae04(Notify) 0xae05(R) 0xae10(W) |
| 0xae3a | 0xae3b(R) 0xae3c(Notify) |
| 0xae00 | 0xae01(R) 0xae02(Notify) |

### 硬件事故记录

| # | 日期 | 事故 | 后果 |
|:--:|------|------|------|
| 1 | 6/15 | 降压板未插稳 | 板1 烧毁 (第一块 nRF52) |
| 2 | 6/17 | TX(A2) 误焊到③号板 5V 输出 | A2 损坏, D1/A4/A5 输入管击穿 |
| 3 | 6/18 | 12V 带电焊接灌入 VDD | 板1 彻底报废 (3V/GND 短路) |

## 6. 待解决问题

- 🟡 **③号板通信联调**：UART 波特率/帧格式/舵机数量/限位（在学长处）
- 🟡 **盒子适配**：ESP32 DevKit 51×28mm vs Feather 51×23mm — 暂不装盒或需重新设计
- 🟡 **手柄按键连发**：Notify 高频率 → STM32 端需做防抖
- 🟡 **CodexPad-C10 手柄**：待到手，协议已分析完毕
- 🟡 **arm-ble-gui BLE 设备列表不显示**（跨线程信号/槽，Qt 6.11 + MSVC）
- 🟡 **GX12 母头引脚定义**：待学长确认
- [x] nRF52840 v2.9-final: BLE 全通 + UART TX=D0 示波器验证
- [x] ESP32 v6-final: NimBLE 全通 + UART TX=D17 示波器验证
- [x] handle_parser 代码复用：两个平台 100% 兼容
- [x] A2 损坏确认、D0 替代确认、GPIO 输入管击穿确认
- [x] 所有文档更新 (AI_MEMORY, README×2, 问题追踪)

## 7. 固件版本历程

### nRF52840 (Bluefruit 库)

| 版本 | 策略 | 结果 |
|:---:|------|:---:|
| v1.5 | 被动扫描 + loop 10s 重启 | ✅ 扫到 LOOKBON |
| v1.9 | 跳过 discover 直写 CCCD | ✅ CCCD OK |
| v2.4 | loop 温和 CCCD | ✅ 数据通道打通 |
| v2.6 | 单字节解析器 | ✅ BTN/X/Y 正确 |
| v2.7 | UART TX(A2) + 电池供电修复 | ✅ 软件层交付 |
| v2.8 | 0xAA/0xBB 帧协议 | ⚠️ A2 物理层不通 |
| **v2.9** | **TX→D0 + 高驱动 + 示波器验证** | ✅ 全链路打通, 板不慎报废 |

### ESP32 (NimBLE-Arduino 库)

| 版本 | 策略 | 结果 |
|:---:|------|:---:|
| v1 | 基础框架 | ❌ `Serial.begin` 被注释 |
| v2 | `connect()` 在扫描回调中 | ❌ `[FAIL] connect` |
| v3 | `connect(dev, true)` + 30s 超时 | ❌ NimBLE 扫描回调限制 |
| v4 | `connect()` 移到 loop | ✅ 连接成功, `[SUB] total=0` |
| v5 | `getCharacteristics(false)` → `true` | ❌ 缓存未填充 |
| **v6** | **`getCharacteristics(true)` + 4s 延迟** | ✅ `[SUB] total=4` 全链路打通 |

## 8. 板① 开发阶段总结 (2026-06-19)

### 量化统计

| 指标 | 数值 |
|------|------|
| nRF52 固件版本数 | 13 (v1.0 → v2.9) |
| ESP32 固件版本数 | 6 (v1 → v6) |
| UART TX 调试轮数 | nRF52: 9 轮 / ESP32: 0 轮（直接复用） |
| NimBLE BLE 调试轮数 | 5 轮（v2→v6） |
| 代码行数 | nRF52: 217 行 / ESP32: 130 行 |
| 示波器验证 | 5 次（D0×3, D17×1, A2×1 无声） |
| 硬件事故 | 3 次 |
| AI 对话轮数 | ~160 轮，跨越 6 天 |
| 跨平台代码复用率 | `handle_parser` 100% |

### 引脚最终分配

| 板 | 引脚 | 丝印 | 功能 | 状态 |
|---|:--:|:--:|------|:--:|
| nRF52840 | P0.25 | D0 | UART TX → GX12 | ✅ (板报废) |
| **ESP32** | **GPIO17** | **TX2/D17** | **UART TX → GX12** | ✅ (当前交付板) |

## 9. 换新板后的操作

### ESP32（当前使用的板子）
```
1. D17 (TX2) → GX12 → ③号板 RX
2. GND → GX12 → ③号板 GND
3. 上电, 连 LOOKBON, 按 A/B/C/D
4. 示波器 D17 确认 0xAA/dir/0xBB 帧
```

### nRF52840（如果买了新 Adafruit Feather）
```
1. 烧录: python -m platformio run --project-dir=D:\Dev\arm-ble --target upload
2. 飞线: D0(P0.25) → GX12 → ③号板 RX
3. 同上验证
```

## 10. 学习笔记索引

| 笔记 | 路径 | 内容 |
|------|------|------|
| BLE通讯/舵机 | `07_学习笔记/嵌入式开发/nRF52_BLE传感器与舵机控制_20260610.md` | BLE通信、舵机映射 |
| IIR/死区滤波 | `07_学习笔记/控制算法/IIR滤波与死区滤波_20260610.md` | IIR低通、死区 |
| 传感器原理 | `07_学习笔记/传感器与信号处理/...EMG肌电控制_20260610.md` | 传感器原理 |
| 3D打印 | `07_学习笔记/机械设计/3D打印工艺与实操积累_20260611.md` | 光固化 |
| Qt BLE开发 | `07_学习笔记/嵌入式开发/Qt_BLE上位机开发与编译_20260612.md` | Qt 6.11 BLE |
| Windows BLE调试 | `07_学习笔记/嵌入式开发/Windows_BLE蓝牙调试流程_20260612.md` | BLE三层模型 |
| C10协议 | `07_学习笔记/嵌入式开发/CodexPad_C10手柄BLE协议分析_20260612.md` | C10协议 |
| LOOKBON协议 | `07_学习笔记/嵌入式开发/VR_BLE手柄LOOKBON协议分析_20260612.md` | LOOKBON协议 |
| BLE调试全记录 | `07_学习笔记/嵌入式开发/LOOKBON手柄BLE调试全记录_20260613.md` | nRF52 v1.0-v2.7 全历程 |
| UART TX 调试全记录 | `../Dev/arm-ble/docs/debug-log/2026-06-17_UART_TX调试全记录.md` | 7轮测试+结论 |
| NimBLE BLE 调试 | `../Dev/arm-ble-esp32/README.md` | ESP32 v1→v6 全记录 + GATT UUID dump |