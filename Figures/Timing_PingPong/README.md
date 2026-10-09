# Ping-Pong 双池时序图

**文件名**: `Timing_PingPong.pdf` (SVG → PDF)  
**放置位置**: §3.3.3.2 单池时序瓶颈与双池 Ping-Pong 调度  
**尺寸**: 0.9\textwidth，横向  
**标签**: `fig:timing-pingpong`

## 内容描述

展示双路径池 Ping-Pong 调度下角色 A（CPU）与角色 B（GPU 后端）的时序关系——两角色在不同 View 上**交替重叠**执行，消除空闲间隙。

---

## 布局

Gantt 风格双行时间轴，水平方向为时间。使用 α/β 两色区分两个 View（路径池）。

### 上行：角色 A（CPU）

| 时间段 | 内容 | 颜色 |
|--------|------|------|
| Round $i$ | Phase 1–5 on View α | 蓝色实心 |
| Round $i+1$ | Phase 1–5 on View β | 蓝色条纹（区分 α/β） |
| Round $i+2$ | Phase 1–5 on View α | 蓝色实心 |
| Round $i+3$ | Phase 1–5 on View β | 蓝色条纹 |

### 下行：角色 B（GPU 后端）

| 时间段 | 内容 | 颜色 |
|--------|------|------|
| Round $i$ | submit(α) → kernel(α) → retrieve(α) | 橙色实心 |
| Round $i+1$ | submit(β) → kernel(β) → retrieve(β) | 橙色条纹 |
| Round $i+2$ | submit(α) → kernel(α) → retrieve(α) | 橙色实心 |
| Round $i+3$ | submit(β) → kernel(β) → retrieve(β) | 橙色条纹 |

### 关键时序关系

- 角色 A 处理 View β 的同时，角色 B 处理 View α（交错）
- 角色 B 的 submit(α) 发生在角色 A 完成 View α 的 collect 之后
- 角色 A 的 distribute(α) 发生在角色 B 完成 View α 的 retrieve 之后（sync 点）
- 虚线箭头表示依赖关系（同 View 跨角色依赖）

### 关键标注

- 大括号标注每轮墙钟时间 $\max(T_A, T_B)$
- α/β 标注在每个工作段内
- "overlap" 标注在两角色同时工作的时间段
- 与单池图对比：无灰色空闲段

---

## 配色方案

- View α 工作段：实心填充
- View β 工作段：条纹填充（区分两个 View）
- 角色 A：蓝色系 (#4472C4)
- 角色 B：橙色系 (#ED7D31)
- 依赖箭头：虚线黑色
- 背景：白色

## 要点

- 强调两角色**同时工作**——流水线重叠
- 每轮总时间 = $\max(T_A, T_B)$（标注）
- 与图 `fig:timing-single-pool` 形成对比
- 稳态条件：$T_A \approx T_B$ 时利用率最高
