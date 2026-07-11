# CodexPad-C10 手柄 BLE 协议分析

> **日期**：2026-06-12
> **主题**：分析 CodexPad-C10 蓝牙手柄的 GATT 协议与数据格式
> **来源**：官方 Gitee 仓库 (`codex_pad_c10` + `codex_pad_guide` + `codex_pad_arduino_lib`)

---

## 一、手柄规格速览

| 参数 | 值 |
|------|-----|
| 蓝牙版本 | BLE 5.3 |
| 角色 | **外设 Peripheral（从机）** |
| 传输距离 | 50m 开阔环境 |
| 发射功率 | -16 ~ +6 dBm 可调 |
| 供电 | CR2032 纽扣电池（3.3V, 约2小时续航） |
| 输入 | 5按键 + 1双轴模拟摇杆 (8位, 0~255) |
| 广播超时 | 1分钟无连接自动关机 |
| 广播名 | `CodexPad-` 开头 |
| 指示灯 | 慢闪=广播中, 常亮=已连接, 快闪=低电量 |

**关键角色**：手柄是 **BLE Peripheral** → nRF52840 板子必须当 **BLE Central** 去连接手柄。这和 `sketch_feb3a.bak`（nRF52840 连弯曲传感器）架构一致！

---

## 二、BLE 通信协议（从 Arduino 库源码完全提取）

### 2.1 连接方式

手柄支持两种连接方式：

1. **BD_ADDR 直连**：用 MAC 地址直接连接（稳定，开发/测试用）
2. **按键掩码扫描连接**：手柄广播时上报当前按键状态，主机扫描后匹配掩码，连接 RSSI 最强的匹配设备（灵活，多手柄环境）

### 2.2 GATT Service/Characteristic 完整表

从 `codex_pad.cpp` 源码直接提取：

| Service UUID | Characteristic UUID | 标准/自定义 | 功能 |
|-------------|---------------------|:---:|------|
| **0xFFA0** (自定义) | **0xFFA1** (Notify) | 自定义 | **🔴 输入数据推送 — 核心通道** |
| 0x1800 (GAP) | 0x2A00 | 标准 | 设备名称 (Read) |
| 0x180A (Device Info) | 0x2A24 | 标准 | 型号 (Read) |
| 0x180A | 0x2A25 | 标准 | 序列号 (Read) |
| 0x180A | 0x2A26 | 标准 | 固件版本 (Read) |
| 0x180A | 0x2A29 | 标准 | 制造商名称 (Read) |
| 0x180F (Battery) | 0x2A19 | 标准 | 电池电量 (Read) |
| 0x1804 (Tx Power) | 0x2A07 | 标准 | 发射功率 (Write) |

**核心服务**：`0xFFA0` → `0xFFA1` Notify，这是手柄数据推送的**唯一通道**。

### 2.3 数据格式（Notify 推送 — 0xFFA1）

**每次通知 8 字节**（与 Bend Labs 传感器的 8 字节格式一致！）：

```
字节0-3: 按键状态位掩码 (uint32_t, little-endian)
         每个 bit 对应一个按键（见下方按键映射表）
字节4:   左摇杆 X 轴 (uint8_t, 0~255, 中位=128)
字节5:   左摇杆 Y 轴 (uint8_t, 0~255, 中位=128)
字节6:   右摇杆 X 轴 (uint8_t, 0~255, 中位=128) — C10 无效
字节7:   右摇杆 Y 轴 (uint8_t, 0~255, 中位=128) — C10 无效
```

### 2.4 按键位掩码映射

| Bit | 枚举名 | 按键 | C10 有效? |
|:---:|--------|------|:---:|
| 0 | kUp | 上 | ✅ |
| 1 | kDown | 下 | ✅ |
| 2 | kLeft | 左 | ✅ |
| 3 | kRight | 右 | ✅ |
| 4 | kSquareX | □/X | ✅ |
| 5 | kTriangleY | △/Y | ✅ |
| 6 | kCrossA | ×/A | ✅ |
| 7 | kCircleB | ○/B | ✅ |
| 8 | kL1 | L1 | ❌ (C10无) |
| 9 | kL2 | L2 | ❌ |
| 10 | kL3 | L3 | ❌ |
| 11 | kR1 | R1 | ❌ |
| 12 | kR2 | R2 | ❌ |
| 13 | kR3 | R3 | ❌ |
| 14 | kSelect | Select | ❌ |
| 15 | kStart | Start | ❌ |
| 16 | kHome | Home | ❌ |

> C10 只有 5 个按键（方向键 ×4 + 功能键 ×1），但库定义覆盖全系列产品。

### 2.5 广播数据（Manufacturer Specific Data）

扫描连接时，手柄在广播包中携带厂商自定义数据，**在扫描阶段就能读到按键状态和固件版本**：

```
字节 0-1:   Company ID = 0xC0DE (codex_pad.cpp 中为 0xFFFF 兼容)
字节 2-9:   Header "CodexPad" (8 字节 ASCII)
字节 10:    Version Major
字节 11:    Version Minor
字节 12:    Version Patch
字节 13-16: 当前按键状态 (uint32_t, 用于按键掩码扫描连接)
字节 17:    按键状态持续秒数
```

---

## 三、数据解析代码模板（供 nRF52840 固件使用）

```cpp
// 8 字节通知回调 — 0xFFA1 特征
void onNotify(uint8_t* data, uint16_t len) {
    if (len < 8) return;

    // 按键状态（位掩码）
    uint32_t buttons = data[0] | (data[1] << 8) | (data[2] << 16) | (data[3] << 24);

    // 摇杆值
    uint8_t leftX = data[4];  // 左右 (128=中位)
    uint8_t leftY = data[5];  // 上下 (128=中位)

    // 按键判断
    bool up    = buttons & (1 << 0);
    bool down  = buttons & (1 << 1);
    bool left  = buttons & (1 << 2);
    bool right = buttons & (1 << 3);
    bool btnA  = buttons & (1 << 6);  // Cross/A
}
```

---

## 四、与现有项目的集成方案

```
CodexPad-C10 手柄 (Peripheral)
    │ BLE 5.3, Service 0xFFA0 → Char 0xFFA1 Notify
    ▼
nRF52840 板子 (Central)
    │ 运行手柄接收固件：
    │   1. 按广播名 "CodexPad-" 扫描
    │   2. 连接设备，发现 GATT 服务
    │   3. 订阅 0xFFA1 Notify
    │   4. 收到 8 字节 → 解析按键+摇杆
    │   5. 通过 UART 转发给 ③ 号板（或直接驱动舵机）
    ▼
③ STM32 控制板
    │ 生成 PWM → 舵机动作
```

**架构要点**：
- nRF52840 当 BLE Central（和 `sketch_feb3a.bak` 连接弯曲传感器一样）
- 不需要 NUS 协议 — 手柄已有自己的自定义服务和特征
- 板子固件需要在 `sketch_feb3a.bak` 基础上修改：把扫描过滤 UUID 从 `0x1820` 换成 `0xFFA0`

---

## 五、相关文档归档位置

| 仓库 | 内容 |
|------|------|
| `06_文献与参考资料/codex_pad_c10/` | C10 产品手册、规格、按键布局 |
| `06_文献与参考资料/codex_pad_guide/` | 连接指南（原生 BLE / BLE 转串口 / I2C） |
| `06_文献与参考资料/codex_pad_arduino_lib/` | Arduino 库源码 + 示例 |