# AI 记忆管理文件

> **用途**：本文件帮助 AI 助手在每次对话中快速了解项目全貌，实现持续跟进。
> **维护规则**：每次与 AI 协作完成重要工作后，更新本文件对应的部分。
> **最后更新**：2026-06-21 22:40

---

## 1. 项目基本信息

| 项目 | 内容 |
|------|------|
| **项目名称** | 假肢机械臂 |
| **项目路径** | `d:\假肢机械臂\`（文档）+ `D:\Dev\arm-ble\`（nRF52固件）+ `D:\Dev\arm-ble-s3\`（ESP32-S3固件）+ `D:\Dev\arm-ble-gui\`（上位机） |
| **GitHub** | `prosthetic-robotic-arm` |
| **负责人** | （你的名字 / 年级：大二下） |
| **开始时间** | 2026年6月 |
| **当前阶段** | ✅ ③号板联调一遍过 | ✅ 全链路交付 | ✅ v2.10 长按区分 | 期末复习 |

## 2. 当前任务背景

- 老师原有机械臂被**剧组借用改造**
- 需要用**未来工场8200pro树脂**做光固化打印（3单合计 ¥944.70，发票已归档至 `00_原始压缩包归档/发票_20260615_944.70/`）

### 电控系统架构（已确认）

```
蓝牙信号源（VR LOOKBON / CodexPad-C10）
    │ BLE
    ▼
┌─ 电池模块（电池箱） ────────────────┐
│  ① BLE→UART 桥                      │
│     ✅ nRF52840 v2.10（新板，主交付，长按0x05-0x08） │
│     ✅ ESP32-S3 v1-final（备用交付）  │
│  ② 电压转换板                         │
└──────────┬──────────────────────────┘
           │ UART TX（115200, 3.3V）
┌─ 机械臂控制板 ──────────────────────┐
│  ③ STM32/cybathlon   ← 发PWM        │
└────────────────────────────────────┘
```

- **板① nRF52840 新板**：Adafruit Feather nRF52840 Express（第2块，6/19 14:00 一遍烧录通过，示波器+焊接一次搞定）
- **板① 替补 ESP32-S3**：ESP32-S3-DevKitC-1 v1.1（MAC： e8:f6:0a:a7:2b:14）— **v1-final 备用板 ✅**
- **板②**：电压转换，纯硬件
- **板③**：STM32，在学长处

### 板子演变史

| 序号 | 板子 | 状态 |
|:--:|------|:--:|
| 1 | nRF52840 Feather #1 | ❌ 12V 带电焊接报废（6/18） |
| 2 | ESP32-WROOM DevKit | ❌ 发热报废（6/19 凌晨） |
| 3 | ESP32-S3-DevKitC-1 | ✅ 备用板（6/19 凌晨打通） |
| **4** | **nRF52840 Feather #2** | **✅ 当前主交付板（6/19 下午一遍过）** |

### 开发环境

| 项目 | 路径 | GitHub | 工具 |
|------|------|------|------|
| 文档管理仓库 | `d:\假肢机械臂\` | [prosthetic-robotic-arm](https://github.com/suancaiyu10108899/prosthetic-robotic-arm) | Git + GitHub |
| nRF52 固件（当前主交付） | `D:\Dev\arm-ble\` | [arm-ble-firmware](https://github.com/suancaiyu10108899/arm-ble-firmware) | PlatformIO（nordicnrf52） |
| ESP32-S3 固件（备用） | `D:\Dev\arm-ble-s3\` | [arm-ble-s3-firmware](https://github.com/suancaiyu10108899/arm-ble-s3-firmware) | PlatformIO（espressif32） |
| 上位机 GUI | `D:\Dev\arm-ble-gui\` | [arm-ble-gui](https://github.com/suancaiyu10108899/arm-ble-gui) | Qt 6.11 + CMake + MSVC |
| ESP32 固件（已废板） | `D:\Dev\arm-ble-esp32\` | —（本地存档） | PlatformIO（espressif32） |

> PlatformIO 命令入口：`python -m platformio run --project-dir=<path> --target upload`

## 3. 当前交付状态（2026-06-21 22:40）

### nRF52840 新板（主交付） ✅ 一遍过

| 交付物 | 路径 | 状态 |
|--------|------|:---:|
| **固件 v2.10** | `D:\Dev\arm-ble\src\main.cpp` | ✅ BLE 全通 + UART TX=D0（P0.25）+ 长按 0x05-0x08 |
| 协议解析器 | `D:\Dev\arm-ble\src\handle_parser.h/cpp` | ✅ |
| platformio.ini | `D:\Dev\arm-ble\platformio.ini` | ✅ |
| README | `D:\Dev\arm-ble\README.md` | ✅ 含 5 分钟上手 + Arduino IDE 双路径 |

### ESP32-S3（备用） ✅

| 交付物 | 路径 | 状态 |
|--------|------|:---:|
| **固件 v1-final** | `D:\Dev\arm-ble-s3\src\main.cpp` | ✅ NimBLE + NeoPixel + UART TX=GPIO17 |
| 协议解析器 | `D:\Dev\arm-ble-s3\src\handle_parser.h/cpp` | ✅ |
| platformio.ini | `D:\Dev\arm-ble-s3\platformio.ini` | ✅（NimBLE + NeoPixel 依赖） |

### 备份

| 文件 | 说明 |
|------|------|
| `D:\Dev\arm-ble\docs\main_v2.9_final.cpp` | nRF52 最终生产固件 |
| `D:\Dev\arm-ble\docs\main_v2.9_prod_backup.cpp` | v2.9 第二备份 |
| `D:\Dev\arm-ble\docs\main_20260618_uart_test_backup.cpp` | 双引脚交替 TX 测试 |

### 技术验证总表

| 层 | nRF52840 | ESP32-S3 |
|----|:---:|:---:|
| 扫描 LOOKBON | ✅ | ✅ |
| GAP 连接 | ✅ | ✅ |
| GATT 服务发现 | ✅（直写 CCCD） | ✅（getCharacteristics（true）） |
| CCCD 通知订阅 | ✅ | ✅ |
| Notify 数据接收 | ✅ | ✅ |
| 协议解析（BTN/X/Y） | ✅ | ✅ |
| 单击/长按 区分 | ✅ v2.10 | 🟡 |
| UART TX 物理层（示波器） | ✅ D0（P0.25）, 3.06V | ✅ GPIO17, 3.3V |
| 电池供电自动启动 | ✅ | 🟡 |
| 电平兼容（3.3V ↔ STM32） | ✅ | ✅ |

## 4. 重要约定与规则

1. **STL/SolidWorks 大文件**：不入 Git（`.gitignore` 已配置），AI 不读取内容
2. **文件命名规范**：你画零件加`【打印件/加工件/铝方管】`前缀，他人文件保留原名
3. **打印材料**：未来工场8200pro树脂（光固化）+ 尼龙件
4. **代码与文档分离**：代码在 `D:\Dev\`（纯英文），文档在 `d:\假肢机械臂\`
5. **AI 辅助原则**：AI 帮你写代码、查文档、做分析，但物理直觉和独立排查能力不可替代。代码要能读懂、能修改。

## 5. 关键技术发现

### Bluefruit（nRF52）系列

- `Bluefruit.begin（peripheralCount, centralCount）` —— 第一个参数是 Peripheral，第二个是 Central
- 纯 Central 模式 onScan 只触发一次 → `begin（1,1）` + loop 重启绕过
- `BLEClientService::discover（）` 与 LOOKBON 不兼容 → 直写 CCCD
- `onConnect` 回调在 SoftDevice 中断上下文 → `delay（2000）` 阻塞 → 移到 loop
- LOOKBON 协议：单字节编码（高 nibble=事件，低 nibble=按键）
- `while （！Serial）` USB CDC 死等 bug → 3 秒超时
- **A2（P0.30） 5V 损坏** → D0（P0.25）替代 + 高驱动 H0H1（3.06V）
- **SoftDevice 与 UARTE 寄存器直驱 TX 不冲突** —— 已验证
- **GPIO 输入管全部击穿（D1/A4/A5）** —— 5V 倒灌 VDD 轨

### NimBLE-Arduino（ESP32 系列） —— 2026-06-18/19

| # | 发现 | 解决方案 |
|:--:|------|------|
| 1 | `connect（）` 不能在 `NimBLEAdvertisedDeviceCallbacks::onResult（）` 里调用 | 扫描回调只存 `g_targetAddr`，`connect（）` 移到 `loop（）` |
| 2 | `getCharacteristics（false）` 返回空 —— `false` 只取本地缓存，发现阶段不填充 | 改为 `getCharacteristics（true）` 强制远端 ATT 读取 |
| 3 | 服务发现需要 4 秒延迟 —— 连接握手后 GATT 表需要时间同步，2 秒不够 | `millis（） - discoTime > 4000` |
| 4 | `dev->getName（）` 返回 `std::string` 不是 Arduino `String` | 用 `std::string::find（）` 和 `tolower（）` |
| 5 | `[SUB] 0` ≠ 没收到数据 —— `canNotify（）` 可能因 UUID 属性解析不一致返回 false | 直接 `subscribe（true, callback）` 全量订阅 |

### LOOKBON GATT 服务结构（UUID dump from ESP32）

| Service UUID | Characteristics |
|:---:|------|
| 0x1800（Generic Access） | 0x2a00（Device Name, Read） |
| 0xae30 | 0xae01（R） 0xae02（Notify） 0xae03（R） 0xae04（Notify） 0xae05（R） 0xae10（W） |
| 0xae3a | 0xae3b（R） 0xae3c（Notify） |
| 0xae00 | 0xae01（R） 0xae02（Notify） |

### 硬件事故记录

| # | 日期 | 事故 | 后果 |
|:--:|------|------|------|
| 1 | 6/15 | 降压板未插稳 | nRF52 板#1 烧毁 |
| 2 | 6/17 | TX（A2）误焊到③号板 5V 输出 | A2 损坏, D1/A4/A5 输入管击穿 |
| 3A | 6/18 | 12V 带电焊接灌入 VDD | nRF52 板#1 彻底报废（3V/GND 短路） |
| 3B | 6/19 凌晨 | ESP32 WROOM 上电发烫 | ESP32 替补板报废 |

## 6. 待解决问题

- ❌ 夹爪舵机故障（插头有电，舵机本体不转，待学长更换）
- ✅ **③号板通信联调 —— 6/19 下午一遍过**
- ✅ **v2.10 长按区分 —— 6/21 部署**
- 🟡 **CodexPad-C10 手柄**：待到手，协议已分析完毕
- 🟡 **arm-ble-gui BLE 设备列表不显示**（跨线程信号/槽，Qt 6.11 + MSVC）
- 🟡 **舵机限位/角度** —— 学长确认中
- 🟡 **GX12 母头引脚定义** —— 学长确认中
- 🟡 **手柄按键连发 100+ 帧** —— ③号板 STM32 端需做防抖
- [x] nRF52840 v2.10：BLE 全通 + UART TX=D0 + 长按 0x05-0x08
- [x] ESP32-S3 v1-final：NimBLE 全通 + UART TX=GPIO17 示波器验证
- [x] 新 nRF52840 板#2 一遍烧录通过（6/19 14:00）
- [x] handle_parser 代码复用：三个平台 100% 兼容
- [x] 所有仓库公开 + 文档同步
- [x] ③号板联调完成（通信、解析、舵机控制均正常，6/19 下午）

## 7. 固件版本历程

### nRF52840（Bluefruit 库）

| 版本 | 策略 | 结果 |
|:---:|------|:---:|
| v1.5 | 被动扫描 + loop 10s 重启 | ✅ 扫到 LOOKBON |
| v1.9 | 跳过 discover 直写 CCCD | ✅ CCCD OK |
| v2.4 | loop 温和 CCCD | ✅ 数据通道打通 |
| v2.6 | 单字节解析器 | ✅ BTN/X/Y 正确 |
| v2.7 | UART TX（A2） + 电池供电修复 | ✅ 软件层交付 |
| v2.8 | 0xAA/0xBB 帧协议 | ⚠️ A2 物理层不通 |
| v2.9 | TX→D0 + 高驱动 + 示波器验证 | ✅ 全链路打通（新板一遍过） |
| **v2.10** | **长按 0x05-0x08 区分** | **✅ 部署完成** |

### ESP32（NimBLE-Arduino 库）

| 版本 | 策略 | 结果 |
|:---:|------|:---:|
| v1-v5 | 扫描回调限制 + 缓存问题迭代 | NimBLE 5 条经验积累 |
| **v6** | **connect 移 loop + getCharacteristics（true） + 4s 延迟** | ✅ 全链路打通 |

## 8. 引脚最终分配

| 板 | 引脚 | 丝印 | 功能 | 状态 |
|---|:--:|:--:|------|:--:|
| **nRF52840 #2** | **P0.25** | **D0** | **UART TX → GX12** | **✅ 主交付板** |
| ESP32-S3 | GPIO17 | TX2/D17 | UART TX → GX12 | ✅ 备用 |
| nRF52840 #1 | P0.25 | D0 | UART TX | ❌ 板报废 |

## 9. 换新板后的操作

### nRF52840（主交付板）
```
1. MicroUSB 供电
2. 已烧录 v2.10
3. D0（P0.25）飞线 → GX12 → ③号板 RX
4. GND → GX12 → ③号板 GND
5. 上电, D4 蓝灯 = BLE 已连接, 按 A/B/C/D → D3 红灯闪 + D0 示波器 AA/dir/BB
```

### ESP32-S3（备用板）
```
1. Type-C 供电
2. 已烧录 v1-final
3. GPIO17（丝印 TX2/D17）→ GX12 → ③号板 RX
4. GND → GX12 → ③号板 GND
5. 上电, NeoPixel 蓝 = 已连接, 绿闪 = 发送帧
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
| 6/21 日总结 | `08_周报与汇报/日总结_2026-06-21.md` | v2.10 改动 + 仓库公开 + 远程烧录全过程 |