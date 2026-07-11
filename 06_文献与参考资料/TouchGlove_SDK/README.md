# TouchGlove SDK

提供 5 通道 `32 x 32 x 3` 的 dense 位移场与力场。

## 目录

- `dense_dashboard.py`: 图形控制台，支持离线回放、实时显示、录制与截图
- `ros2_dense_fields.py`: ROS2 dense 数据发布节点
- `dense_preflight.py`: Rust dense CUDA 初始化自检脚本
- `check_cuda_env.py`: CUDA / ONNX Runtime 环境检测脚本
- `models/dense_3ch.enc`: 默认加密 dense 模型，输入为 3 通道差值图 `(current - baseline) / 255`

## 环境配置

推荐使用 Python 3.10 环境运行 dense SDK：

```bash
conda create -n touchglove_dense_py310 python=3.10 -y
conda activate touchglove_dense_py310
python3 --version
cd /path/to/dist_dense
```

`/path/to/dist_dense` 是交付得到的 `dist_dense` 文件夹路径，例如 `/media/lxqs/ESD-USB/dist_dense`。后续命令都在这个目录下执行。

`python3 --version` 应显示 `Python 3.10.x`。

安装 Python 依赖：

```bash
pip install \
  numpy PySide6 matplotlib cryptography onnxruntime-gpu==1.23.2 \
  "nvidia-cuda-runtime-cu12>=12,<13" \
  "nvidia-cuda-nvrtc-cu12>=12,<13" \
  "nvidia-cublas-cu12>=12,<13" \
  "nvidia-cufft-cu12>=11,<12" \
  "nvidia-curand-cu12>=10,<11" \
  "nvidia-cudnn-cu12>=9,<10"
```

确认 NVIDIA 驱动可用：

```bash
nvidia-smi
```

确认 SDK 随包的 ONNX Runtime 动态库存在：

```bash
ls touch_glove_rust/libonnxruntime.so.1.23.2
ls touch_glove_rust/libonnxruntime_providers_cuda.so
```

SDK 会自动从当前 Python 环境的 `site-packages/nvidia/*/lib`、`/usr/local/cuda*/lib64` 和 `LD_LIBRARY_PATH` 中加载 CUDA / cuDNN 运行库。按上面的 `pip install` 安装后，通常不需要手动配置 `LD_LIBRARY_PATH`。

## CUDA 环境检测

首次部署或换机器后，先运行实时程序使用的 Rust 初始化自检：

```bash
cd /path/to/dist_dense
python3 dense_preflight.py
```

成功时会看到：

```text
[PASS] Rust dense CUDA 初始化通过。
```

再运行完整诊断：

```bash
cd /path/to/dist_dense
python3 check_cuda_env.py --verbose
```

检测内容：

- `onnxruntime` 是否可导入
- 是否存在 `CUDAExecutionProvider`
- `models/dense_3ch.enc` 是否能解密并用 CUDA session 加载
- 是否能完成一次 dummy dense 推理
- Rust SDK 是否能完成 dense CUDA 初始化

成功时会看到：

```text
[PASS] 环境检测通过
```

如果只想检查 CUDA provider 和模型加载，不跑推理：

```bash
python3 check_cuda_env.py --skip-inference
```

如果程序停在 `Registering CUDAExecutionProvider...`，说明 CUDA provider 正在加载 GPU 运行库，通常是迁移机的 CUDA/cuDNN 运行库缺失或不可见。重新执行上面的 `pip install ... nvidia-*-cu12 ...`，然后先跑 `python3 dense_preflight.py`，通过后再启动 GUI 或 ROS2 节点。

## 图形控制台

启动统一控制台：

```bash
python3 dense_dashboard.py
```

直接进入实时模式：

```bash
python3 dense_dashboard.py --realtime
```

直接进入离线回放：

```bash
python3 dense_dashboard.py --force_npy npy/force_xxxx.npy --disp_npy npy/disp_xxxx.npy --fps 30
```

控制台支持：

- 离线打开 `force_*.npy` / `disp_*.npy` 并回放
- 连接实时手套并进行 dense 推理
- 基准校准
- 实时录制并保存 `force_*.npy` / `disp_*.npy`
- 保存当前界面截图
- 5 通道切换
- 法向 / 切向显示模式

首次连接手套时，建议在手套自然放置、各通道无外力接触的状态下，多次进行基准校准，待显示结果稳定后再开始录制或发布数据。

显示模式：

- 法向：显示 `abs(dz)` 与 `abs(fz)` 热力图
- 切向：显示 `sqrt(dx^2 + dy^2)` 与 `sqrt(fx^2 + fy^2)` 热力图，并用 `32 x 32` 箭头显示切向方向

## ROS2 Dense 发布节点

节点将 `models/dense_3ch.enc` 传入 Rust SDK，由 Rust 内部完成图像读取、基准校准与 dense 推理；Python 层只发布 `disp` / `force` 结果。

首次连接或重新佩戴手套后，建议保持各通道无外力接触，并多次执行基准校准。

启动节点：

```bash
cd /path/to/dist_dense
source /opt/ros/humble/setup.bash
python3 ros2_dense_fields.py
```

默认发布：

- `disp`: `std_msgs/Float32MultiArray`
- `force`: `std_msgs/Float32MultiArray`

两个 topic 的 layout 都是：

```text
(channel, height, width, xyz) = (5, 32, 32, 3)
```
