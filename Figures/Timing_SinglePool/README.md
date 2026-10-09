# 单池时序图

**文件名**: `Timing_SinglePool.pdf` (SVG → PDF)  
**放置位置**: §3.3.3.2 单池时序瓶颈与双池 Ping-Pong 调度  
**尺寸**: 0.9\textwidth，横向  
**标签**: `fig:timing-single-pool`

## 内容描述

展示单路径池架构下角色 A（CPU）与角色 B（GPU 后端）的时序关系——两角色\textbf{严格串行}，存在大量空闲间隙。

---

## 布局

Gantt 风格双行时间轴，水平方向为时间。

### 上行：角色 A（CPU）

| 时间段 | 内容 | 颜色 |
|--------|------|------|
| Round $i$ | Phase 1–5（distribute→advance→harvest→refill→collect） | 填充色（如蓝色） |
| Round $i$ sync | 空闲等待 sync() | 灰色斜线填充 |
| Round $i+1$ | Phase 1–5 | 填充色 |
| Round $i+1$ sync | 空闲等待 sync() | 灰色斜线填充 |

### 下行：角色 B（GPU 后端）

| 时间段 | 内容 | 颜色 |
|--------|------|------|
| Round $i$ idle | 空闲等待 submit | 灰色斜线填充 |
| Round $i$ | submit → H2D → kernel → D2H | 填充色（如橙色） |
| Round $i+1$ idle | 空闲等待 submit | 灰色斜线填充 |
| Round $i+1$ | submit → H2D → kernel → D2H | 填充色 |

### 关键标注

- 大括号标注每轮墙钟时间 $T_A + T_B$
- $T_A$ 标注在角色 A 的工作段上方
- $T_B$ 标注在角色 B 的工作段上方
- 灰色段标注 "idle"
- 虚线箭头连接 collect→submit（角色 A 提交至角色 B）和 sync→distribute（角色 B 结果回传至角色 A）

---

## 配色方案

- 角色 A 工作段：蓝色 (#4472C4)
- 角色 B 工作段：橙色 (#ED7D31)
- 空闲等待段：灰色斜线填充 (#D9D9D9)
- 背景：白色
- 标注文字：黑色

## 要点

- 强调两角色\textbf{从不同时工作}——完全串行
- 每轮总时间 = $T_A + T_B$（标注）
- 与图 `fig:pingpong-timing` 形成对比
