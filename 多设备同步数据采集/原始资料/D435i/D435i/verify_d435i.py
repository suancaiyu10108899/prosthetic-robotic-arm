#!/usr/bin/env python3
"""
D435i 三路流验证脚本
功能：同时采集 RGB + 深度 + IMU（加速度计+陀螺仪），保存一帧样本，实时预览
用法：python verify_d435i.py
输出：d435i_rgb.png / d435i_depth.png（当前目录）
"""

import pyrealsense2 as rs
import numpy as np
import cv2
import os

# ==================== 1. 列出设备信息 ====================
print("=" * 60)
print("[INFO] 扫描 RealSense 设备...")
ctx = rs.context()
devices = ctx.query_devices()
if len(devices) == 0:
    print("[FAIL] 没有检测到 RealSense 设备！请检查 USB 连接。")
    exit(1)

for dev in devices:
    print(f"  型号:      {dev.get_info(rs.camera_info.name)}")
    print(f"  序列号:    {dev.get_info(rs.camera_info.serial_number)}")
    print(f"  固件:      {dev.get_info(rs.camera_info.firmware_version)}")
    print(f"  USB 类型:  {dev.get_info(rs.camera_info.usb_type_descriptor)}")
    print()

# ==================== 2. 启动所有流 ====================
print("[INFO] 启动数据流...")
pipeline = rs.pipeline()
config = rs.config()

# RGB 流
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
# 深度流
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
# D435i IMU 流（加速度计 + 陀螺仪）
config.enable_stream(rs.stream.accel)
config.enable_stream(rs.stream.gyro)

profile = pipeline.start(config)

# ==================== 3. 获取内参（重要！记录给学长学姐） ====================
depth_intr = profile.get_stream(rs.stream.depth).as_video_stream_profile().get_intrinsics()
color_intr = profile.get_stream(rs.stream.color).as_video_stream_profile().get_intrinsics()

print("=" * 60)
print("[INTRINSICS] 相机内参（记录下来给学长学姐）：")
print(f"  Depth: fx={depth_intr.fx:.3f}, fy={depth_intr.fy:.3f}, "
      f"cx={depth_intr.ppx:.3f}, cy={depth_intr.ppy:.3f}")
print(f"  Color: fx={color_intr.fx:.3f}, fy={color_intr.fy:.3f}, "
      f"cx={color_intr.ppx:.3f}, cy={color_intr.ppy:.3f}")
print(f"  Depth 畸变系数: {depth_intr.coeffs}")
print(f"  Color 畸变系数: {color_intr.coeffs}")
print("=" * 60)

# ==================== 4. 等自动曝光稳定后采集一帧 ====================
print("[INFO] 等待自动曝光稳定（约 1 秒）...")
for _ in range(30):
    pipeline.wait_for_frames()

frames = pipeline.wait_for_frames()

# RGB
color_frame = frames.get_color_frame()
if not color_frame:
    print("[FAIL] 未获取到 RGB 帧")
else:
    color = np.asanyarray(color_frame.get_data())
    cv2.imwrite("d435i_rgb.png", color)
    print(f"  [OK] RGB 已保存:       d435i_rgb.png ({color.shape[1]}x{color.shape[0]})")

# 深度
depth_frame = frames.get_depth_frame()
if not depth_frame:
    print("[FAIL] 未获取到深度帧")
else:
    depth = np.asanyarray(depth_frame.get_data())
    cv2.imwrite("d435i_depth.png", depth)
    print(f"  [OK] 深度已保存:       d435i_depth.png ({depth.shape[1]}x{depth.shape[0]}, 16-bit)")

# IMU - 加速度计
accel_frame = frames.first_or_default(rs.stream.accel)
if accel_frame:
    a = accel_frame.as_motion_frame().get_motion_data()
    print(f"  [IMU] 加速度计 (m/s^2): x={a.x:.4f}, y={a.y:.4f}, z={a.z:.4f}")
else:
    print("  [WARN] 未获取到加速度计数据")

# IMU - 陀螺仪
gyro_frame = frames.first_or_default(rs.stream.gyro)
if gyro_frame:
    g = gyro_frame.as_motion_frame().get_motion_data()
    print(f"  [IMU] 陀螺仪 (rad/s):  x={g.x:.4f}, y={g.y:.4f}, z={g.z:.4f}")
else:
    print("  [WARN] 未获取到陀螺仪数据")

print()
print("=" * 60)
print("[OK] D435i 三路流全部打通！")
print("   显示实时画面中，按 ESC 退出...")
print("   左侧 = RGB 彩色 | 右侧 = 深度伪彩色")
print("=" * 60)

# ==================== 5. 实时预览 ====================
try:
    while True:
        frames = pipeline.wait_for_frames()

        # RGB
        c = np.asanyarray(frames.get_color_frame().get_data())
        # 深度
        d = np.asanyarray(frames.get_depth_frame().get_data())
        # 深度伪彩色映射（0-65535 尺度缩放）
        d_vis = cv2.applyColorMap(cv2.convertScaleAbs(d, alpha=0.03), cv2.COLORMAP_JET)

        # 并排显示
        display = np.hstack((c, d_vis))
        cv2.imshow("D435i - Left:RGB | Right:Depth | Press ESC to exit", display)

        if cv2.waitKey(1) & 0xFF == 27:  # ESC
            break
finally:
    pipeline.stop()
    cv2.destroyAllWindows()
    print("[INFO] 数据流已关闭，再见。")
