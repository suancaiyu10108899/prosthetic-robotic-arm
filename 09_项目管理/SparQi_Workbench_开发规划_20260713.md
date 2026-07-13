# Spar Qi Workbench — 开发规划

> **日期**：2026-07-13
> **前提**：Spar Qi 手环已打通（BLE→COM6, MAC=ED:9D:0F:48:F3:BA, 9ch EMG 1000Hz）

---

## 一、背景与动机

Spar Qi SDK 自带的 `main.py` 和 `realtime_visualization.bak` 虽然能显示实时波形，但存在以下限制：

| 问题 | 影响 |
|------|------|
| Y 轴固定 ±500 | CH1 均值 5287、CH8 均值 -9321，高通后波动 ±2000，信号被严重裁剪 |
| 鼠标交互全禁用 | `setMouseEnabled(x=False, y=False)`，无法缩放观察 1ms 细节 |
| 无滤波切换 | 只有 10Hz 高通，无法实时试验 50Hz 陷波/带通/整流/RMS 包络 |
| 无录制控制 | 采集自动开始直到关窗，没有开始/停止按钮 |
| 无设备面板 | 不显示 MAC、COM 口、连接状态 |
| 单视图 | 只能 9 宫格，无法通道对比 |
| CSV 路径固定 | 每次覆盖旧数据 |

需要一个**交互式调试工作台**，最大化发挥 1000Hz 采样的可视化能力。

---

## 二、目标功能

### 2.1 设备信息面板
- 显示当前连接的设备 MAC、名称、COM 口、采样率
- 实时显示连接状态（Connected / Connecting / Error）

### 2.2 录制管理
- 开始/停止按钮
- 自动创建 `session_YYYYMMDD_HHMMSS/` 目录
- 每次录制保存：
  - `emg_YYYYMMDD_HHMMSS.csv`（原始 9 通道数据）
  - `metadata.json`（设备信息 + 时间戳 + 滤波设置）

### 2.3 双视图
| 视图 | 功能 |
|------|------|
| 9 宫格视图 | 3×3 EMG 子图，Y 轴自适应，鼠标缩放/平移/框选 |
| 通道对比视图 | 勾选任意 N 通道叠加在同一图，图例标注颜色 |

### 2.4 实时信号处理面板
| 复选框 | 功能 | 默认 |
|--------|------|:--:|
| 50Hz Notch | 工频陷波（Q=30） | ☐ |
| 20-500Hz Bandpass | Butterworth 4 阶带通 | ☐ |
| Rectify | 全波整流 | ☐ |
| RMS Envelope (50ms) | 滑动窗口 RMS，白色粗线叠加 | ✅ |

### 2.5 调整显示
- 鼠标滚轮缩放 X 轴 — 缩到 0.2s 看清 1ms 采样间隔
- 鼠标框选放大
- 右键拖动平移
- 右键菜单 "View All" 恢复全览
- 工具栏 🔒 锁定按钮（防止误触缩放）

---

## 三、技术栈

| 层 | 技术 | 说明 |
|---|---|---|
| UI | PyQt5 + pyqtgraph | 窗口 + GPU 加速曲线 |
| 信号处理 | scipy.signal | 实时 lfilter / iirnotch / butter |
| BLE 驱动 | ResearchKit_SDK (.pyd) | 手环通信 |
| 数据管理 | CSV + JSON | 轻量、可复用 |

---

## 四、项目结构

```
D:\Dev\sparmqi-workbench\         ← 新 GitHub 仓库（私人）
├── .gitignore
├── README.md
├── requirements.txt
├── workbench.py                  ← 主程序
├── src/
│   └── ResearchKit_SDK/          ← .pyd 链接（不存 Git）
├── docs/
│   ├── devlog/
│   │   └── 2026-07-13_开发规划.md
│   └── debug-log/
│       └── INDEX.md
├── emg_data/                     ← 采集数据（.gitignore）
└── scripts/
    └── check_device.py           ← 快速诊断脚本
```

> ⚠️ `src/ResearchKit_SDK/` 通过 sys.path 引用 `D:\Dev\sparqi-env\src\ResearchKit_SDK\`，不复制。.pyd 二进制不入库。

---

## 五、开发计划（预计 1-2 小时）

| 步骤 | 任务 | 时间 |
|:--:|------|--:|
| 1 | 创建 GitHub 仓库 `sparmqi-workbench`（私人） | 5 min |
| 2 | 创建项目骨架 + `.gitignore` + `requirements.txt` | 5 min |
| 3 | 写 `workbench.py` 主程序（~300 行） | 40 min |
| 4 | 测试运行 — BLE 连接 + 两个视图 + 滤波面板 | 15 min |
| 5 | 写 `devlog/2026-07-13_开发规划.md` + `debug-log/INDEX.md` | 10 min |
| 6 | 推送 GitHub | 5 min |
| 7 | 更新 `d:\假肢机械臂\` 的任务看板 + AI_MEMORY + 推送 | 5 min |

---

## 六、依赖环境

```powershell
# Python 3.10 虚拟环境（已在 D:\Dev\sparqi-env\.venv）
D:\Dev\sparqi-env\.venv\Scripts\python.exe workbench.py

# 依赖（已安装）
pyqtgraph, PyQt5, scipy, numpy
```

---

## 七、验收标准

- ✅ 窗口弹出后 1 秒内自动连接手环
- ✅ 9 宫格视图能看到去直流波形（10Hz 高通）
- ✅ 鼠标可缩放 X 轴到 <0.5s 窗口，看清 1kHz 采样细节
- ✅ 通道对比视图能勾选 2-4 通道叠加
- ✅ 勾选 "RMS Envelope" 后能看到白色包络粗线
- ✅ 点击 "Start Recording" → 采集 → "Stop" → `emg_data/` 下生成 CSV + metadata.json
- ✅ 手工关闭窗口后 BLE 资源正常释放