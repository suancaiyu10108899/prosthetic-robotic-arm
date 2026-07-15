# Important Notes

## Protocol Description

CodexPad controllers communicate using a standard Bluetooth Low Energy (BLE) protocol, which is fundamentally different from the common BLE HID profile.

- **Protocol type**: The controller uses a custom standard BLE protocol optimized for embedded development — not the plug‑and‑play BLE HID protocol.

- **Connection and usage**: As a result, your computer or mobile operating system (Windows, macOS, Android, iOS, Linux) **will not recognise the controller as a standard game controller or input device** after pairing. It cannot be used directly in any game or application.

- **Intended use**: The controller is designed from the ground up as **a programmable input module**. You must write your own host‑side code to connect to it, read its data, and implement the control logic you need.

  - **Primary supported mode**: We provide comprehensive libraries and example code for mainstream hardware platforms. This is our recommended approach and receives official technical support.

  - **Advanced usage mode**: Experienced developers can also write host‑side code on a **computer (e.g., using Python, Node.js) or mobile device (e.g., using Android Studio, Swift)** to connect to and control the controller. This is an advanced option for specific projects, and **we do not offer official technical support, libraries, or examples for this mode**. Regarding the underlying BLE GATT characteristics, we will evaluate market demand before deciding whether to provide detailed documentation in the future.

  - **Theoretical compatibility**: In principle, the controller **supports any hardware platform capable of acting as a BLE central device**. If you intend to use it on a platform we have not explicitly validated (such as other microcontrollers, single‑board computers, or custom hardware), you will need to **develop your own host‑side driver based on our open communication protocol**, or watch for official support in future updates.

> **💡 Please note**: This controller is a development tool designed for **programmable embedded projects**. If you need a plug‑and‑play solution for a PC or phone, it will not suit your needs. If you are a capable developer who wishes to integrate this controller into a PC or mobile application, you will need to research its BLE communication protocol on your own.
