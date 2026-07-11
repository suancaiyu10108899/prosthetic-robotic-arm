# CodexPad Connection and Usage Guide: Using the Built-in BLE of Hardware Platforms

## Overview

This document applies to hardware platforms with **built-in BLE capabilities**. If your hardware platform (such as ESP32, ESP32-S3, Raspberry Pi Pico W, micro:bit, etc.) has BLE communication capabilities and you plan to call low-level BLE APIs (Arduino BLE library, MicroPython, etc.) directly in your code to communicate with CodexPad, please follow this guide.

Whether the platform's main controller chip has an integrated radio circuit or implements Bluetooth functionality via an onboard **wireless coprocessor**, this guide applies. You will focus on business logic, using standard or platform-specific Bluetooth libraries to establish connections and process data.

## Connection Methods Description

CodexPad provides two flexible host connection methods. You can choose based on your development scenario and needs.

### Method 1: Direct Connection via Bluetooth Device Address

This method performs a precise connection using the controller's unique **Bluetooth Device Address**.

- **Working principle**: In your host code, pre-write the Bluetooth Device Address of the target controller. After the program starts, it will directly attempt to establish a connection with the device at this specific address.

- **Key features**: **Clear targeting, stable connection**. Suitable for scenarios with a fixed development environment and a determined pairing relationship between the controller and host (for example, a specific robot is always controlled by a specific controller).

- **Preparation before use**: Please refer to the corresponding product documentation for your CodexPad series to obtain the specific operation method for the Bluetooth Device Address (BD_ADDR) and record it.

### Method 2: Scan and Connect via Button Mask

This method is a **featured features of CodexPad products**. It enables intelligent matching connections based on physical interaction by having the controller report button states during advertising.

- **Working principle**: In your host code, define a "button mask" (e.g. simultaneously holding **Start + A** button). When the host scans for nearby devices, it will only connect to the controller with the strongest signal (largest RSSI) whose **button states exactly match the mask** (i.e., the specified button combination is held and no other buttons are pressed).

- **Key features**:

    1. **Prevents interference**: In environments with multiple controllers, it effectively avoids accidental connections to other devices.

    2. **Flexible switching**: The code does not bind to a specific controller's Bluetooth Device Address. You can pick up any controller that is in a discoverable state and correctly triggers the button condition to connect, enabling seamless device switching.

- **Applicable scenarios**: Suitable for multi-device environments, demo scenarios, projects requiring flexible controller replacement, or when you don't want to hard-code a hardware address in the code.

- **Hardware platforms**: Not applicable to all hardware platforms; please refer to the library documentation for specifics.

> **Note**: For more detailed design intent, advantages, and usage examples of "Scan and Connect via Button Mask," please refer to the library documentation and example code for the corresponding development platform.

## Connection and Usage

### Arduino IDE Library and Example Code

Suitable for development in **Arduino IDE** or **PlatformIO**.

| Supported Hardware Platforms |
| :--- |
| ESP32 |
| ESP32-S2 |
| ESP32-S3 |
| ESP32-C3 |
| ESP32-C5 |
| ESP32-C6 |
| ESP32-H2 |
| ESP32-P4 |

**Detailed description**: [CodexPad Arduino Lib](../../../codex_pad_arduino_lib/blob/main/README.md#codexpad-arduino-lib)

---

### MicroPython Library and Example Code

Suitable for development on **MicroPython** firmware.

#### Supported Hardware Platforms

**Theoretical Support Scope**: This library theoretically supports all development platform running **MicroPython** firmware with the built-in standard **bluetooth** module, provided the hardware itself has **Bluetooth Low Energy (BLE)** capability. You can check the [official MicroPython download page (filtered for BLE)](https://micropython.org/download/?features=BLE) to find suitable firmware for your device.

The following table lists the available hardware platforms that we have tested:

| Supported Hardware Platforms |
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

**Detailed description**: [CodexPad MicroPython Lib](../../../codex_pad_mpy_lib/blob/main/README.md#codexpad-micropython-lib)

---

### Micro:bit Graphical Extension

Suitable for development for micro:bit in the **MakeCode** graphical programming environment.

| Hardware Platform |
| :--- |
| micro:bit |

**Detailed description**: [CodexPad Extension for micro:bit MakeCode](../../../codex_pad_makecode_extension/blob/main/README.md#codexpad-extension-for-microbit-makecode)

---
