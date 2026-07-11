### 单手蓝牙遥控手柄 micropython 源码

支持 ESP32, ESP32-C3, ESP32-S3 等支持 BLE(低功耗蓝牙) 的 开发板

设备默认名称 "LOOKBON"
```
device_name = "LOOKBON"
```

设备 mac 地址每一台都不一样, 请查看外包装或手柄机身  
也可以使用 `test_get_mac_by_name.py` 获取  
实际使用的时候 请将 `mac_str` 改为你的设备 mac 地址
```
mac_str = "XX:XX:XX:XX:XX:XX"
```
