# pip install pyautogui
# pip install bleak

import time
import asyncio
import pyautogui
from bleak import BleakClient

# 1. 设置你的设备 MAC 地址
DEVICE_ADDRESS = "AE:0E:5B:B1:C1:8B"

# 2. 根据扫描结果，锁定具有 notify 属性的句柄
# 优先尝试 7，如果没数据就换 131 或 67
TARGET_HANDLE = 7


key_map = {
    "A2": "A",
    "A3": "B",
    "A4": "C",
    "A5": "D"
}

def notification_handler(handle, data):
    """
    当手柄数据变化时，此函数会被触发
    """
    # 将收到的字节流转换为十六进制字符串
    hex_payload = data.hex().upper()
    print(f"{time.time()} [Handle {handle}] 原始报文: {hex_payload}")

    # if hex_payload in key_map:
    #     target_key = key_map[hex_payload]
    #     pyautogui.press(target_key)
    #     print(f"映射按键: {target_key}")


async def main():
    print(f"正在尝试连接设备: {DEVICE_ADDRESS}...")

    # 设置连接超时为 20 秒
    async with BleakClient(DEVICE_ADDRESS, timeout=20.0) as client:
        if client.is_connected:
            print(f"连接成功！当前正在监听句柄: {TARGET_HANDLE}")

            # 使用 handle 而不是 UUID 启动通知，避免冲突
            await client.start_notify(TARGET_HANDLE, notification_handler)

            print("等待数据中... 请操作手柄按键！(按下 Ctrl+C 退出)")

            try:
                # 保持连接
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\n正在停止监听...")
            finally:
                await client.stop_notify(TARGET_HANDLE)
        else:
            print("连接失败，请确认手柄处于配对模式且未被其他程序占用。")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"发生错误: {e}")
