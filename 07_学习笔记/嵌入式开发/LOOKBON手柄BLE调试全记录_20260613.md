# LOOKBON 手柄 BLE 调试全记录 — 从扫描到解析的完整历程

> **日期**：2026-06-13
> **目标**：让 Adafruit Feather nRF52840 Express（板①）作为 BLE Central 连接 VR LOOKBON 手柄并接收按键/摇杆数据
> **手柄 MAC**：`0D:CE:99:03:5D:D2`

---

## 0. 背景知识

### 整个流程需要打通 5 层

```
扫描 → GAP连接 → CCCD订阅 → Notify数据 → 协议解析 → 舵机输出
```

每一层都可能卡住。今天每卡一层就写一个版本，一共 11 个版本才全通。

### 开发环境

- VS Code + PlatformIO (pip 安装，命令行编译)
- 命令：`python -m platformio run --project-dir=d:\Dev\arm-ble --target upload`
- 串口：`python -m platformio device monitor --project-dir=d:\Dev\arm-ble --baud 115200`
- 板子通过 MicroUSB 连接 PC，烧录用 COM7，串口用 COM6

### 关键库约束

Adafruit Bluefruit nRF52 Libraries 封装了 Nordic SoftDevice（底层蓝牙协议栈）。但 LOOKBON 手柄用的是定制 BLE 芯片，与 Adafruit 封装不完全兼容——这就是今天 80% 的问题来源。

---

## 1. 第一层：扫描 — v1.0 到 v1.5

### 问题：板子扫不到手柄

**v1.0 串口输出**：
```
[READY] passive scan...
[HEARTBEAT] scanCount=1 discovering=NO    ← 只扫到 1 个设备就停了
[RESTART] scan was count=1                ← 10 秒后重启
[HEARTBEAT] scanCount=0 discovering=NO    ← 重启后又是 0
```

**现象**：`scanCount=1` 每轮只看到一个设备，不是 LOOKBON。然后 onScan 回调永久不触发，直到 loop 中 10 秒后强制重启扫描。

**根因**：`Bluefruit.begin(0, 1)` — **第一个参数是 Peripheral 数量，第二个才是 Central**。但即使改对参数 `begin(0,1)` 纯 Central 模式，Adafruit 扫描器在收到第一个广播包后就停止回调。

**v1.5 修复**：三大改动同时生效

```cpp
// 1. 双角色模式（而非纯 Central）
Bluefruit.begin(1, 1);

// 2. 被动扫描（不主动请求扫描响应，功耗低，干扰少）
Bluefruit.Scanner.useActiveScan(false);

// 3. loop 中每 10 秒重启扫描器，打破 Adafruit 的休眠 loop
if (now - g_lastRestart > 10000) {
    Bluefruit.Scanner.stop();
    delay(500);
    Bluefruit.Scanner.start(0);
}
```

**成功后输出**：
```
>>> LOOKBON MATCH! mac=0D:CE:99:03:5D:D2
[CONNECT] OK conn=0
```

**为什么 loop 重启有效？** Adafruit 扫描器在 start() 后会设置一个内部定时器。一旦 onScan 回调触发后定时器不重置，后续广播包就被忽略。`stop()` + `start()` 重置了全部内部状态。

---

## 2. 第二层：GATT 服务发现 — v1.6 到 v1.9

### 问题：连接成功但立刻断开

**v1.6 串口输出**：
```
[CONNECT] OK conn=0
[ERR] service          ← discover() 失败
[DISCONN] reason 0x16  ← 我们主动断开
```

**我们当时的代码**：
```cpp
static void onConnect(uint16_t conn) {
    g_svc = new BLEClientService(BLEUuid("AE30..."));
    if (!g_svc->discover(conn)) {
        Bluefruit.disconnect(conn);  // ← 失败就挂断
    }
}
```

**根因**：Adafruit 的 `BLEClientService::discover()` 调用 Nordic SoftDevice 的 `sd_ble_gattc_primary_services_discover()`，发 GATT 发现命令给手柄。LOOKBON 手柄的 BLE 芯片对 GATT 服务发现命令的应答格式与 Adafruit 库期望的不符 → discover 返回 false。

**v1.8 尝试**：保持连接循环重试 5 次

```
[DISCOVER] attempt #1
[RETRY] discover failed (1/5), keeping connection alive...
[DISCOVER] attempt #2
...
[GIVEUP] 5 retries exhausted, disconnecting
```

结论：discover 永远不可能成功，与重试无关。

**v1.9 修复**：完全跳过 discover，直接写 CCCD

Python 参考代码 `ble_python.py` 完全不做服务发现，直接用已知 handle 号：
```python
await client.start_notify(7, notification_handler)  # 不调 discover！
```

v1.9 仿照用 Nordic SD API 直写：
```cpp
uint16_t cccdHandle = 7 + 1;  // CCCD 通常在 char handle + 1
uint16_t cccdVal    = 0x0001;  // enable notification
sd_ble_gattc_write(conn, &param);  // 直接写
```

**为什么必须跳过 discover？** discover 是 GATT 客户端主动问服务端"你有什么服务/特征"，而 LOOKBON 手柄没有正确实现服务发现应答。但手柄确实在用 AE30 服务和 AE02 特征发 Notify——只是它不响应"问我有什么"的请求。直接告诉它"我订阅你的数据"是可以的。

---

## 3. 第三层：CCCD 订阅 — v2.0 到 v2.4

### 问题：CCCD 写入成功但收不到 Notify

**v2.3 串口输出**：
```
[CONNECT] conn=0
[CCCD] wrote 0x0001 to handle 8      ← CCCD 似乎写成功了
[CCCD] wrote 0x0001 to handle 68
[CCCD] wrote 0x0001 to handle 132
[OK] subscribed
[EVT] DISCONNECTED reason=0x8         ← 但 8 秒后断连！(0x08=超时)
```

**v2.3 的 onConnect 代码**：
```cpp
static void onConnect(uint16_t conn) {
    delay(2000);                      // ← 阻塞！在 SoftDevice 中断上下文
    writeCCCD(conn, 7);
    writeCCCD(conn, 67);
    writeCCCD(conn, 131);
}
```

**根因**：`onConnect` 回调在 **Nordic SoftDevice 的中断处理线程** 中执行。`delay(2000)` 阻塞了 SoftDevice 处理 BLE 链路层的心跳事件 → 手柄 8 秒没收到任何交互包 → 超时断连。

等价于：你在电话里接起后沉默 2 秒不说话，然后连吼三句话——对方已经被你沉默到挂电话了。

**v2.4 修复**：将 CCCD 写入移到 loop() 中温和执行

```cpp
// onConnect 只设标志，不阻塞
static void onConnect(uint16_t conn) {
    g_connHandle  = conn;
    g_cccdPhase   = 1;                         // 从 phase 1 开始
    g_cccdNextTime = millis() + 2000;           // 2 秒后第一次尝试
}

// loop 中每 2 秒写一个 CCCD
void loop() {
    if (g_cccdPhase >= 1 && g_cccdPhase <= 3 && now - g_cccdNextTime > 2000) {
        writeOneCCCD(g_connHandle, kCCCDHandles[g_cccdPhase - 1]);
        g_cccdPhase++;
    }
}
```

**v2.4 成功后**：
```
[CCCD] wrote 0x0001 to handle 8 (char handle 7)
[DATA] h=8 raw=A5 → BTN=0x0 X=128 Y=128    ← 🎉 数据来了！
[DATA] h=8 raw=D1 → BTN=0x0 X=128 Y=128
[DATA] h=8 raw=D3 → BTN=0x0 X=128 Y=128
```

---

## 4. 第四层：协议解析 — v2.5 到 v2.6

### 问题：有数据但 BTN/X/Y 全是默认值

**v2.5 串口输出**：
```
[DATA] raw= → BTN=0x0 X=128 Y=128   ← 乱码！BTN永远是0
[DATA] raw= → BTN=0x0 X=128 Y=128
```

`raw=` 说明 `Serial.print((char)hvx->data[i])` 将单字节 0xA5 当 ASCII 打印，0xA5 不是可打印字符 → 显示乱码。

**v2.5 的解析器**（错误版本）：
```cpp
// 以为是 ASCII 字符串 "A5\n"
ParsedInput parseLookbon(const uint8_t* data, size_t len) {
    char event = (char)data[0];  // 'A' ← 但 data[0] 是 0xA5 不是 'A'!
    char key   = (char)data[1];  // '5' ← data 只有 1 个字节！
}
```

**v2.6 修复**：hex 打印 + 单字节协议

```cpp
// hex 打印看到真相
for (uint16_t i = 0; i < hvx->len; i++) {
    if (hvx->data[i] < 0x10) Serial.print('0');
    Serial.print(hvx->data[i], HEX);  // 输出: 0xA3, 0xD1...
}

// 单字节解析：高 nibble = 事件，低 nibble = 编号
uint8_t event = (byte >> 4) & 0x0F;  // 0xA→单击, 0xB→长按, 0xC→释放, 0xD→方向
uint8_t key   = byte & 0x0F;          // 0x1=@, 0x2=A, ... 0x7=L
```

**v2.6 成功后**：
```
[DATA] raw=0xA3 → BTN=0x80 X=128 Y=128    ← B 键单击！
[DATA] raw=0xD1 → BTN=0x0 X=128 Y=0       ← 摇杆上！
[DATA] raw=0xB2 → BTN=0x40 X=128 Y=128    ← A 键长按！
[DATA] raw=0xC2 → BTN=0x0 X=128 Y=128     ← A 键释放！
```

---

## 5. 最终协议表

| 字节 | 含义 |
|------|------|
| `0xA1`-`0xA7` | 单击 @/A/B/C/D/R/L |
| `0xB1`-`0xB7` | 长按 |
| `0xC1`-`0xC7` | 释放 |
| `0xD0` | 摇杆中位 |
| `0xD1` | 摇杆 ↑ (Y=0) |
| `0xD2` | 摇杆 ↓ (Y=255) |
| `0xD3` | 摇杆 ← (X=0) |
| `0xD4` | 摇杆 → (X=255) |
| `0xD5` | 摇杆 ↖ (X=0,Y=0) |
| `0xD6` | 摇杆 ↙ (X=0,Y=255) |
| `0xD7` | 摇杆 ↗ (X=255,Y=0) |
| `0xD8` | 摇杆 ↘ (X=255,Y=255) |

---

## 6. 核心教训

### 6.1 不要信任库的 API

Adafruit 的 `BLEClientService::discover()` 对其他 BLE 设备可能有效，对 LOOKBON 无效。直接调用底层 `sd_ble_gattc_write()` 反而成功了。

### 6.2 中断上下文 ≠ 主循环

`onConnect` 在 SoftDevice 中断上下文中运行。`delay()` 在中断里会阻塞整个 BLE 栈。任何耗时操作都应移到 `loop()`。

### 6.3 hex 日志比 ASCII 日志可靠

`raw=A5` 和 `raw=0xA5` 看起来差不多，但前者是"把 0xA5 当 ASCII 打印成乱码"，后者才是"打印这个字节的十六进制值"。调试阶段始终用 hex。

### 6.4 协议假设要验证

我们假设 LOOKBON 用 ASCII 字符串协议——错了。它用单字节编码。是 hex 日志验证了真相。

---

## 7. 版本速查表

| 版本 | 策略 | 结果 | 关键发现 |
|:---:|------|:---:|------|
| v1.0-v1.4 | 纯 Central 扫描 | ❌ count=1 卡死 | `begin(0,1)` 扫描器 bug |
| **v1.5** | 双角色 + 被动扫描 + loop 重启 | ✅ 扫到 | 三合一修复 |
| v1.6-v1.8 | GATT discover | ❌ 不兼容 | 库 API 假设错误 |
| **v1.9** | 跳过 discover 直写 CCCD | ✅ CCCD OK | Python 代码启示 |
| v2.0-v2.3 | onConnect 阻塞式 CCCD | ❌ 超时断连 | 中断上下文陷阱 |
| **v2.4** | loop 温和 CCCD | ✅ 数据通道 | 关键架构修复 |
| v2.5 | 修复解析器 | ❌ 仍是 ASCII | 协议假设错误 |
| **v2.6** | hex 打印 + 单字节解析 | ✅ 全通 | 协议真相验证 |