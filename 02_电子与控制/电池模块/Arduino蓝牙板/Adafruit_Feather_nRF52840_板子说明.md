# Adafruit Feather nRF52840 Express — 板子说明（中文简版）

> **来源**：Adafruit 官方文档 + 平台定义 + 本项目的固件分析
> **整理日期**：2026-06-11
> **板子全名**：Adafruit Feather nRF52840 Express
> **核心芯片**：Nordic nRF52840 (ARM Cortex-M4F @ 64MHz, 1MB Flash, 256KB RAM)
> **官方链接**：https://learn.adafruit.com/adafruit-feather-nrf52840-express

---

## 一、主要特性

| 参数 | 值 |
|------|-----|
| 芯片 | Nordic nRF52840 |
| 核心 | ARM Cortex-M4F（带硬件浮点） |
| 主频 | 64 MHz |
| Flash | 1 MB (其中 796KB 可供 Arduino 使用) |
| RAM | 256 KB (可供 Arduino 使用 ~243KB) |
| 蓝牙 | BLE 5.0 (Bluetooth 5) |
| USB | 原生 USB (nRF52840 内建，非转换芯片) |
| 充电芯片 | 板载 Li-Po 锂电池充电 (JST 接口) |
| 编程接口 | MicroUSB 口（与供电共用） |
| 尺寸 | 51mm × 23mm × 8mm |

## 二、电源

| 来源 | 说明 |
|------|------|
| MicroUSB | 最常用——同时供电 + 烧录程序 |
| Li-Po 电池 | 焊接在板子背面的 JST 接口，板载充电管理 |
| 3.3V 排针 | 可外部供电（**仅 3.3V，不要接 5V**） |

> ⚠️ **重要**：nRF52840 工作在 3.3V。所有 IO 引脚**只能接受 3.3V**，用 5V 信号会烧毁芯片。

## 三、常用引脚 （本项目相关）

| Arduino 编号 | nRF52 端口 | 功能 | 本项目用途 |
|:-----------:|:----------:|------|-----------|
| `LED_BUILTIN` (13) | P1.15 | 红色板载 LED | Blink 测试用 |
| `A2` | P0.04 | 模拟/数字 IO | `sketch_feb3a.ino` 接舵机信号线 |
| `A0` ~ `A5` | 多个模拟通道 | 模拟读数 / 通用 IO | — |
| `SCL` | P0.11 | I2C 时钟线 | 可接传感器 |
| `SDA` | P0.12 | I2C 数据线 | 可接传感器 |
| `TX` | P0.25 | UART 发 | 有线通信到 ③ 号板 |
| `RX` | P0.24 | UART 收 | 有线通信到 ③ 号板 |
| `SCK` | P1.13 | SPI 时钟 | — |
| `MO` | P1.14 | SPI 主机出从机入 | — |
| `MI` | P1.11 | SPI 主机入从机出 | — |
| `NEOPIXEL` (8) | P1.09 | 板载 RGB 彩色 LED | 状态指示 (可选) |

> **板载 LED 说明**：红色 LED 连在 pin 13；RGB LED（NeoPixel）连在 pin 8，可通过 `Adafruit_NeoPixel` 库控制颜色。

## 四、实物连接步骤

```
电脑 USB ──(MicroUSB 数据线)──▶ 板子 MicroUSB 口
                                   │
                                   ├─ 板子自动供电（无需额外电池）
                                   ├─ 设备管理器出现新 COM 口
                                   └─ 可烧录程序
```

1. 用**数据 MicroUSB 线**（不是充电线）连接
2. 打开设备管理器查看新 COM 口名称
3. 运行烧录命令（PlatformIO 自动检测 COM 口）
4. 板载红色 LED 开始闪烁 → 成功

## 五、开发环境快速参考

### PlatformIO 项目结构 (`D:\Dev\arm-ble\`)

```
platformio.ini 中关键配置：
━━━━━━━━━━━━━━━━━━━━━━━━━━
[env:adafruit_feather_nrf52840_express]
platform = nordicnrf52
board = adafruit_feather_nrf52840
framework = arduino
monitor_speed = 115200
━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 常用命令

```powershell
# 编译
python -m platformio run --project-dir=d:\Dev\arm-ble

# 编译+烧录
python -m platformio run --project-dir=d:\Dev\arm-ble --target upload

# 串口监视
python -m platformio device monitor --project-dir=d:\Dev\arm-ble
```

## 六、关键注意事项

| 注意 | 说明 |
|------|------|
| ⚠️ IO 电压 | **仅 3.3V**，切勿接 5V 信号 |
| ⚠️ MicroUSB 线 | 必须用数据线（4芯），充电线（2芯）无法通信 |
| ⚠️ 烧录失败 | 双击板子 Reset 按钮进入 Bootloader 模式再试 |
| BLE 天线 | 板载陶瓷天线，方向性不强但不要用手遮挡 |
| 电池 | 如果需要电池供电，接 3.7V Li-Po 到板子背面 JST 口 |

---

> 📌 **补充参考**：完整引脚图、电路原理图请访问 Adafruit 官方页面。
> 同时建议归档一份板子实物照片到 `02_电子与控制/电池模块/Arduino蓝牙板/` 下。