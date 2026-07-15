# Windows BLE 蓝牙调试流程

> **日期**：2026-06-12
> **主题**：从 nRF Connect 到自写 Qt App 的完整 BLE 调试链路
> **工具链**：nRF Connect (Android) → nRF52840 板子 → 串口 → Qt 上位机

---

## 一、BLE 调试三层模型

你调试任何 BLE 外设时，本质都在验证这三层是否正常：

| 层 | 协议元素 | 你验证的工具 | 出错时的表现 |
|------|---------|------------|------------|
| **广播层** | GAP Advertisement | nRF Connect 扫描列表 | 找不到设备 |
| **连接层** | GATT Connection | 点 Connect 是否成功 | 连接超时/断连 |
| **数据层** | GATT Characteristic | TX/RX 特征读写 | 发送无响应 |

这个分层是调试的核心思路——**永远从下往上排查**：广播出不来就看固件是否正确烧录；连不上就看 GAP 参数；数据不通就看 UUID 是否匹配。

---

## 二、nRF Connect 的调试价值

你 6/11 用 nRF Connect 成功验证了全链路：

```
nRF Connect (Android 手机)
  ↓ 扫描
  找到 MAC: D3:52:88:3A:06:27 (带 NUS 服务)
  ↓ 连接
  蓝灯常亮 = GATT 连接建立
  ↓ 服务发现
  看到 6E400001-B5A3-F393-E0A9-E50E24DCCA9E (NUS)
  看到 6E400002-... (TX: 手机→板子)
  看到 6E400003-... (RX: 板子→手机)
  ↓ 写 TX 特征: "Hello你好"
  板子串口打印 "Hello你好" ✅
```

**nRF Connect 的作用**：
- 验证硬件链路无误（不是板子坏了）
- 抓取 UUID / MAC（这些值是自写 App 的硬编码常量）
- 排除固件问题（如果 nRF Connect 连不上，说明固件或硬件有问题）

---

## 三、自写 Qt App 替换 nRF Connect

你的 arm-ble-gui 做的事情，本质上就是 nRF Connect 的功能子集：

| nRF Connect 功能 | arm-ble-gui 对应 | 实现文件 |
|------|------|------|
| Scan 按钮 | BleScanner::startScan() | BleScanner.cpp |
| 设备列表 | DeviceScanPanel + QListWidget | DeviceScanPanel.cpp |
| Connect/Disconnect | BleConnection::connectToAddress() | BleConnection.cpp |
| TX 特征写 | SendPanel + BleConnection::sendText() | SendPanel.cpp |
| RX 特征通知监听 | LogPanel ← BleConnection::textReceived | LogPanel.cpp |

区别在于 nRF Connect 是通用的（支持所有服务和特征），arm-ble-gui 是**专用的**——只认 NUS UUID，连接后自动找 TX/RX 特征，用户体验更简洁。

---

## 四、串口监视 vs BLE App 的配合

你的 nRF52840 板子同时有两个通信通道：

```
           BLE (无线)                 串口 (MicroUSB有线)
              │                            │
     arm-ble-gui / nRF Connect      PlatformIO Monitor / Putty
              │                            │
              └─────→ nRF52840 板子 ←──────┘
                        │
                   double print:
                   收到BLE数据 → Serial.print()
```

**调试技巧**：
- 用 arm-ble-gui 发数据，同时看 PlatformIO 串口监视器确认板子收到了什么——这是"闭环验证"
- 如果 App 发 `90`，串口显示 `90` = BLE 链路 + 固件解析全对
- 如果 App 发 `90`，串口显示乱码 = 波特率不对或编码问题

---

## 五、Windows BLE 的特殊问题

### 5.1 蓝牙硬件必须支持 BLE 4.0+

Windows 需要蓝牙适配器同时支持 Classic Bluetooth 和 **Bluetooth Low Energy**。大部分笔记本内置蓝牙都支持（如 Intel Wireless Bluetooth），但老式 USB 蓝牙适配器可能只支持 Classic。

验证方法：
```
设备管理器 → 蓝牙 → 查看是否有 "Microsoft Bluetooth LE Enumerator"
有这个 = 支持 BLE ✅
```

你的电脑已确认：Intel Wireless Bluetooth + BLE Enumerator ✅

### 5.2 Qt BLE 依赖 WinRT API

Windows 上 Qt Bluetooth 的底层是 WinRT Bluetooth LE API，需要：
- Windows 10 1803 及以上
- 蓝牙在「设置」中为"开"
- 应用不需要管理员权限（但需要蓝牙权限，Qt 自动处理）

### 5.3 第一次连接可能慢

Windows 的 BLE 服务发现（`discoverServices` + `discoverDetails`）比 Android 慢 2-3 倍。正常现象，耐心等待 3-5 秒。

---

## 六、调试实战流程（推荐）

```
第1步：确认板子 BLE 在广播
  → 看 NeoPixel 蓝灯是否呼吸
  → 或者打开 Windows 设置 → 蓝牙 → 搜索设备，看是否出现 ARM-BLE

第2步：用 nRF Connect 连一次
  → 排除硬件/固件问题（只连一次就行，不用每次）

第3步：用 arm-ble-gui 扫描+连接
  → 点击扫描 → 找到 ARM-BLE → 连接 → 等 Ready 状态

第4步：双向验证
  → 在 arm-ble-gui 输入框输入 "test" → 发送
  → 同时看 PlatformIO 串口监视器是否打印 "test"
  → 如果没有：检查固件是否烧录正确（`main.cpp` 不是 `sketch_feb3a.bak`）

第5步：预设按钮测试
  → 点击"舵机 90°" → 串口打印 "90"
  → 此时舵机不会动（固件没有 Servo 逻辑），但数据通路验证通过
```

---

## 七、要点总结

1. BLE 调试永远从广播层往上排查（广播→连接→数据）
2. nRF Connect 是"验证硬件"，arm-ble-gui 是"自写工具"
3. 串口和 BLE 两个通道同时看 = 双保险
4. Windows 的 BLE 服务发现比手机慢，正常
5. 板子 MicroUSB 一根线搞定供电+编程+串口，不需要额外供电