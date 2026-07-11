# Intel RealSense D435i — 相机交付包

> **交付日期**：2026-07-10
> **验证状态**：✅ RGB / 深度 / IMU 三路流全部打通

---

## 📷 这台相机的信息

| 项目 | 值 |
|------|-----|
| 型号 | Intel RealSense **D435I** |
| 序列号 | **043322075669** |
| 固件版本 | **5.16.0.1**（最新稳定版为 5.17.3，可升级但非必须） |
| USB | USB 3.2 |
| IMU 芯片 | **BMI055**（内置加速度计 + 陀螺仪） |
| 深度单位 | **0.001**（像素值 × 0.001 = 米，例如像素值 500 = 0.5m） |

---

## 🔬 相机内参（手眼标定 / 视觉算法必备）

### 深度相机
| fx | fy | cx | cy |
|------|------|------|------|
| 383.631 | 383.631 | 322.501 | 242.745 |

> 畸变系数：Brown Conrady 模型，k1=k2=k3=p1=p2=0

### RGB 相机
| fx | fy | cx | cy |
|------|------|------|------|
| 608.636 | 608.941 | 319.371 | 238.077 |

> 畸变系数：Brown Conrady 模型，k1=k2=k3=p1=p2=0

---

## 🐍 如何快速验证（3 步）

### 1. 安装 Python 依赖（只需一次）

```bash
pip install -r requirements.txt
```

或者手动安装：
```bash
pip install pyrealsense2==2.58.2 opencv-python==5.0.0 numpy==2.4.6
```

需要 Python 3.8 以上。`requirements.txt` 已锁定经过验证的版本。

### 2. 确认 SDK 已安装

从 [Intel RealSense GitHub Releases](https://github.com/IntelRealSense/librealsense/releases) 下载 `Intel.RealSense.SDK-Win10.exe`（≥ v2.58.2），安装后**重启电脑**。

验证安装成功：

```bash
rs-enumerate-devices
```

应该能看到 `Intel RealSense D435I` 的设备信息。

### 3. 运行验证脚本

```bash
cd 到这个文件夹
python verify_d435i.py
```

脚本会自动：
- 扫描设备 → 打印型号/序列号/固件
- 打印相机内参（fx/fy/cx/cy）
- 启动 **RGB + 深度 + 加速度计 + 陀螺仪** 四路数据流
- 保存一帧样本（`d435i_rgb.png` + `d435i_depth.png`）
- 弹出实时预览窗口（左:RGB / 右:深度伪彩色），按 **ESC** 退出

---

## 📁 文件夹内容

| 文件 | 说明 |
|------|------|
| `README.md` | 本文件 |
| `requirements.txt` | Python 依赖（锁定版本，方便环境复现） |
| `verify_d435i.py` | 一键验证脚本 |
| `device_info.txt` | `rs-enumerate-devices` 完整输出（含所有分辨率/帧率/格式，搭 ROS2 launch 必备） |
| `viewer_三路流.png` | RealSense Viewer 截图（RGB + 深度 + IMU 同时运行） |
| `d435i_rgb.png` | 一帧 RGB 样本图 |
| `d435i_depth.png` | 一帧深度样本图（16-bit PNG，像素值 × 0.001 = 米） |

---

## ⚠️ 注意事项

- **独占**：相机同一时间只能被一个程序占用。不要同时开 Viewer 和 Python 脚本
- **SDK 路径**：`rs-enumerate-devices` 和 `realsense-viewer` 默认安装在 SDK 的 `tools/` 目录
- **IMU 数值**：加速计即使静止也有 ~9.8 m/s² 的合加速度——这是**地球重力**，正常现象。陀螺仪静止时为 0