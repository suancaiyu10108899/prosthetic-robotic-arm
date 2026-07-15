# 多设备同步数据采集

> **状态**：🔵 设备打通 → 同步框架开发
> **目标**：一次实验四设备同时采集，统合输出

---

## 终态架构

```
一次实验 = 四设备同时采集:
  ┌─ D435i 相机      → RGB .mp4 + 帧索引 CSV
  ├─ SparQi 手环 x2   → 9ch EMG 1000Hz + IMU CSV
  ├─ TouchGlove 手套  → 5×32×32×3 force+disp .npy
  └─ NOKOV 动捕      → 7 markers 3D 坐标 CSV
```

## 设备打通进度

| 设备 | 日期 | 状态 |
|:--|:--:|:--:|
| D435i | 7/10 | ✅ 四路流 + 内参 |
| SparQi #1 (Band3BA) | 7/13 | ✅ ACK超时待回归 |
| SparQi #2 (Band794) | 7/14 | ✅ 全链路通过 |
| TouchGlove | 7/13 | ✅ USB→WSL2→GUI |
| NOKOV | — | 🟡 SDK已归档 |

## 关联代码仓库

| 项目 | GitHub | 路径 |
|------|--------|------|
| SparQi Workbench | PRIVATE | `D:\Dev\sparmqi-workbench\` |
| TouchGlove 管线 | 本地 | `D:\Dev\data-collection\` |

## 文档导航

| 文档 | 用途 |
|------|------|
| `CLAUDE.md` | 🤖 AI 入口 |
| `任务看板.md` | TODO/DONE 看板 |
| `问题追踪.md` | 🔴🟡✅ 问题清单 |
| `架构设计/` | 终态架构 + 同步方案 |
| `设备打通记录/` | 每个设备的详细打通日志 |
| `日总结/` | 每日推进记录 |