### 单手蓝牙遥控手柄 arduino 源码

支持 ESP32, ESP32-C3, ESP32-S3 等支持 BLE(低功耗蓝牙) 的 开发板


实际使用的时候 请将 `BLEAddress` 改为你的设备 mac 地址
```
static BLEAddress targetAddress("XX:XX:XX:XX:XX:XX");
```
