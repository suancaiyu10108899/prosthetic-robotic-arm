# CodexPad Connection and Usage Guide: Using BLE to Serial Module

## Overview

This document applies to scenarios where you use the controller **via a BLE to Serial module**. If your hardware platform (e.g. Arduino UNO, Nano) does not have BLE capabilities and you need to use an external BLE to Serial module (e.g. NL-16) or a development board with an integrated BLE to Serial module (e.g. BLE-UNO) to receive controller data, please follow this guide.

Whether the BLE to Serial module is external or integrated on the development board, its working principle is the same: the Bluetooth chip handles wireless transmission and reception, and the main controller communicates with the Bluetooth chip via the serial port. You will send AT commands via the serial port to control the Bluetooth module's connection and receive data frames from the Bluetooth chip.

## Connection Method: Direct Connection via Bluetooth Device Address

- ***Working principle**: In your host code, pre-write the Bluetooth Device Address of the target controller. Configure the BLE to Serial module to master mode via AT commands, and then initiate the connection. After the program starts, it will directly attempt to establish a connection with the device at this specific address.

- **Key features**: **Clear targeting, stable connection**. Suitable for scenarios with a fixed development environment and a determined pairing relationship between the controller and host (for example, a specific robot is always controlled by a specific controller).

- **Preparation before use**: Please refer to the corresponding product documentation for your CodexPad series to obtain the specific operation method for the Bluetooth Device Address (BD_ADDR) and record it.

## Connection and Usage

### Arduino IDE Library and Example Code

This library and example code are suitable for scenarios where you use the controller **via a BLE to Serial module**, supporting the following two connection schemes:

- Development board with an integrated BLE to Serial module

    Suitable for development boards **with an onboard BLE to Serial module** (e.g. BLE-UNO). The main controller communicates with the Bluetooth chip via the serial port. The working principle is the same as "development board + external BLE to Serial module".

    | Applicable Development Boards |
    | :--- |
    | BLE-UNO |

- Development board with an external BLE to Serial module

    Suitable for development boards **without an onboard integrated BLE to Serial module** (e.g. Arduino UNO, Nano), by connecting an external BLE to Serial module (e.g. NL-16) to use the controller.

    **Supported External BLE to Serial Modules**

    | BLE to Serial Module |
    | :--- |
    | NL-16(V1.2+) |

    **Supported Hardware Platforms**

    | Supported Hardware Platforms |
    | :--- |
    | Arduino UNO |
    | Arduino Nano |

**Detailed description**: [CodexPadFrameDecoder Arduino lib](../../../codex_pad_frame_decoder_arduino_lib/blob/main/README.md#codexpadframedecoder-arduino-lib)

---
