# Linux Cline 交接文档 — 机械臂改装调试

> 最后更新：2026-07-22
> 本文档供 Linux 环境下的 Cline AI 助手接手上手使用。

---

## 一、项目背景

这是一个 **3 自由度腕部 + 1 自由度夹爪** 的小型机械臂改装调试项目。

**物理结构**：
```
世界原点（袖筒固定）
  └── q1: 绕 X 轴旋转 ±180°（前臂旋转）
      └── q2: 绕 Y 轴俯仰 [-90°, 15°]（腕部俯仰）
          └── q3: 绕 X 轴滚转 ±180°（腕部滚转）
              └── g: 夹爪开合 [0°, 90°]（平行四边形+齿轮耦合，单自由度）
```

**控制方式**：PC 直连 4 个 Feetech 舵机（USB-TTL），无单片机。触觉传感器通过 FT232H（SPI→USB）接入 PC。

**全链路语言**：100% Python（pyserial + PyQt5 + numpy + scipy + pyftdi）

---

## 二、你的任务

| 优先级 | 任务 | 输出 | 依赖 |
|:--:|------|------|:--:|
| P1 | 实现 `python/kinematics.py`：正运动学 fkine() + 6×4 雅可比 jacobian() | 代码 + pytest | `requirements.txt` + `docs/ik_algorithm.md` |
| P1 | 创建 `ros2_ws/src/arm_description/`：URDF 可视化 + launch 文件 + RViz | ROS2 package | URDF 已就绪（`urdf/model.SLDASM.urdf`） |
| P2 | 实现逆运动学 ikine() | 扩展到 kinematics.py | fkine 完成 |
| P2 | 创建 `ros2_ws/src/arm_kinematics/`：IK Service 节点 | ROS2 package | ikine 完成 |
| P3 | MoveIt2 运动规划集成 | 仿真环境 | 前 4 项完成 |

---

## 三、技术参数速查

### 运动学模型

```
独立坐标：q = [q1, q2, q3, g]（rad）

正运动学：
  T0G = Rx(q1) · Tx(50mm) · Ry(q2) · Tx(30mm) · Rx(q3)

夹爪耦合（平行四边形约束）：
  qA = +g, qB = -g, qTipA = -g, qTipB = +g

TCP 零位（q = 0 时）：
  位置 = [227, 0, 0] mm
  两侧指尖轴沿局部 +X 前移 40mm 后的中点
```

| 参数 | 值 |
|:--|:--|
| L12（前臂→俯仰轴） | 50 mm |
| L23（俯仰轴→滚转轴） | 30 mm |
| grip.rootX | 54 mm |
| grip.rootY | 6 mm |
| grip.linkX | 53 mm |
| grip.linkY | 2 mm |
| grip.contactX | 40 mm |
| q1 限位 | ±180° |
| q2 限位 | -90° ~ 15° |
| q3 限位 | ±180° |
| g 限位 | 0° ~ 90° |

### 雅可比

```
6×4 几何雅可比（基坐标系表达）
前三行：TCP 线速度 [mm/rad]
后三行：TCP 角速度 [rad/rad]

q3 的线速度列 ≈ 0（TCP 在滚转轴线上）
g 的角速度列 = 0（平行四边形约束）
```

> 详细逆解推导见 `arm-mod/docs/ik_algorithm.md`

---

## 四、环境要求

```bash
# 系统
Ubuntu 22.04 (WSL2 或 VirtualBox)

# ROS2
Humble (rclpy)

# Python
Python 3.10 或 3.11

# 依赖安装
cd arm-mod
pip install -r python/requirements.txt
# pyserial>=3.5, PyQt5>=5.15, numpy>=1.24, scipy>=1.10, pyftdi>=0.55

# ROS2 环境
source /opt/ros/humble/setup.bash

# URDF 可视化
cp urdf/model.SLDASM.urdf ros2_ws/src/arm_description/urdf/
# 然后在 RViz 中加载验证
```

---

## 五、从哪里开始

```
1. git clone arm-mod（GitHub PRIVATE，确保已添加为 Collaborator）
2. 读 arm-mod/CLAUDE.md → 了解代码工程全局
3. 读 arm-mod/docs/ik_algorithm.md → 运动学算法细节
4. 读本文件 → 了解项目背景
5. pip install -r requirements.txt
6. 从 kinematics.py 的正运动学 fkine() 开始实现
```

---

## 六、关联仓库

| 仓库 | 用途 | GitHub 链接 |
|:--|:--|:--|
| **arm-mod** | 仿真 + 控制代码 | `https://github.com/suancaiyu10108899/arm-mod` |
| **LabDocs** | 完整项目文档 + MATLAB 验证代码 | `https://github.com/suancaiyu10108899/prosthetic-robotic-arm` |

> ⚠️ 两个仓库均为 GitHub PRIVATE，需 Collaborator 权限才能访问。

## 七、协作规则

- **Phase 完成后立即 Git commit + push** — 不等对话结束
- 踩坑 → 追加到 `arm-mod/CLAUDE.md` 踩坑记录区
- 任务状态变化 → 更新 `arm-mod/任务看板.md`
- 日总结 → 各自在 Linux 上写，提交到 LabDocs 的 `机械臂改装调试/日总结/`
- 算法疑问 → 查阅 LabDocs 中的 MATLAB 验证代码（`子系统/机械臂控制/MATLAB仿真/`）