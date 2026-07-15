# CodexPad连接使用指南：使用硬件平台内置BLE

## 概述

本文档适用于**内置BLE功能**的硬件平台。如果您的硬件平台（如 ESP32、ESP32-S3、Raspberry Pi Pico W、micro:bit 等）具备BLE通信能力，且您计划直接在代码中调用底层 BLE API（Arduino BLE 库、MicroPython 等）与 CodexPad 进行通信，请遵循本指南。

无论平台的主控芯片是自带射频电路，还是通过板载的**无线协处理器**实现蓝牙功能，本指南均适用。您将专注于业务逻辑，通过标准或平台特定的蓝牙库来建立连接和处理数据。

## 连接方式说明

CodexPad提供了两种灵活的主机连接方式，您可以根据开发场景和需求进行选择。

### 方式一：Bluetooth Device Address 直连

此方式通过手柄唯一的 **Bluetooth Device Address** 进行精准连接。

- **工作原理**：在您的主机代码中，预先写入目标手柄的Bluetooth Device Address。程序启动后将直接尝试与这个特定地址的设备建立连接。

- **核心特点**：**指向明确，连接稳定**。适用于开发环境固定、手柄与主机配对关系确定的场景（例如，某台机器人固定使用某个特定手柄控制）。

- **使用前准备**：请根据您的CodexPad系列，查阅对应产品文档以获取 Bluetooth Device Address (BD_ADDR)​ 的具体操作方法，并完成记录。

### 方式二：按键掩码扫描连接

此方式是 **CodexPad 产品的特色功能**，它通过让手柄在广播时上报按键状态，实现基于物理交互的智能匹配连接。

- **工作原理**：在您的主机代码中，定义一个“按钮掩码”（例如：同时按住 **Start键 + A键**）。主机在扫描附近设备时，只会与那些**按键状态恰好与掩码匹配**（即按住了指定按键组合且未按其他键）的、信号最强（RSSI最大）的手柄建立连接。

- **核心特点**：

    1. **防止干扰**：在多个手柄的环境中，能有效避免意外连接到其他设备。

    2. **灵活切换**：代码不绑定具体手柄Bluetooth Device Address，您可以随时拿起任何一台处于可发现状态、并正确触发按键条件的手柄进行连接，实现设备的无缝切换。

- **适用场景**：适用于多设备环境、演示场景、需要灵活更换手柄或不想在代码中硬编码硬件地址的项目。

- **硬件平台**：不适用于所有的硬件平台，具体请参考库的说明

> **提示**：关于“按键掩码扫描连接”更详细的设计意图、优势及使用示例，请参阅对应开发平台的库的文档和示例代码。

## 连接与使用

### Arduino IDE库和示例代码

适用于在 **Arduino IDE** 或 **PlatformIO** 中进行开发。

| 支持的硬件平台 |
| :--- |
| ESP32 |
| ESP32-S2 |
| ESP32-S3 |
| ESP32-C3 |
| ESP32-C5 |
| ESP32-C6 |
| ESP32-H2 |
| ESP32-P4 |

**详细说明**：[CodexPad Arduino Lib](../../../codex_pad_arduino_lib/blob/main/README.zh-CN.md#codexpad-arduino-lib)

---

### MicroPython库和示例代码

适用于在 **MicroPython** 固件上进行开发。

#### 支持的硬件平台

**理论支持范围**：本库理论上支持所有运行了内置标准**bluetooth**模块的**MicroPython**固件、且硬件本身具备 **低功耗蓝牙（BLE）** 功能的开发平台。您可以通过 [MicroPython官方下载页面（已筛选BLE功能）](https://micropython.org/download/?features=BLE)来查找和确认适合您设备的、支持蓝牙的官方固件。

下表列出了我们已测试可用的部分硬件平台：

| 支持的硬件平台 |
| :--- |
| ESP32 |
| ESP32-S3 |
| ESP32-C2 |
| ESP32-C3 |
| ESP32-C5 |
| ESP32-C6 |
| ESP32-P4 |
| Raspberry Pi Pico W |
| Raspberry Pi Pico 2 W |

**详细说明**：[CodexPad MicroPython Lib](../../../codex_pad_mpy_lib/blob/main/README.zh-CN.md#codexpad-micropython-lib)

---

### Micro:bit图形化扩展

适用于在 **MakeCode** 图形化编程环境中为 micro:bit 开发。

| 硬件平台 |
| :--- |
| micro:bit |

**详细说明**： [CodexPad Extension for micro:bit MakeCode](../../../codex_pad_makecode_extension/blob/main/READMD.zh-CN.md#codexpad-extension-for-microbit-makecode)

---

### Mind+库和示例程序

Mind+ CodexPad蓝牙手柄用户库链接：<https://gitee.com/emakefun_midplus_lib/codexpad>

[点击查看Mind+导入用户库方法](https://mindplus.dfrobot.com.cn/extensions-user-libraries)

[点击下载CodexPad蓝牙手柄Mind+示例程序](https://gitee.com/emakefun_midplus_lib/codexpad/releases/download/V0.0.1/codexPad%E6%89%8B%E6%9F%84%E6%B5%8B%E8%AF%95%E7%A4%BA%E4%BE%8B.zip)

---

### Mixly库和示例程序

[点击下载CodexPad蓝牙手柄Mixly库](https://gitee.com/emakefun_mixly_lib/codexpad/releases/download/V0.0.1/codexpad_Mixly%E5%BA%93.zip)

[点击下载CodexPad蓝牙手柄Mixly示例程序](https://gitee.com/emakefun_mixly_lib/codexpad/releases/download/V0.0.1/codexpad%E8%93%9D%E7%89%99%E6%89%8B%E6%9F%84Mixly%E7%A4%BA%E4%BE%8B.zip)

---
