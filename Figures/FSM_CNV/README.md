# CNV 模块状态转移图

**文件名**: `FSM_CNV.pdf` (SVG → PDF)  
**放置位置**: §3.4.1.4 CNV 子小节末尾  
**尺寸**: 0.4\textwidth  

## 内容描述

CNV（对流换热）模块的 FSM 状态转移图。CNV 是最简洁的模块，仅 4 个状态、1 个查询。

### 状态节点

1. **CNV_PROBE**：发射腔体边界探针射线 → **[RT 查询]**
2. **CNV_TIME**：瞬态时间回溯采样（指数分布 τ_conv）
3. **CNV_SAMPLE**：在壁面上按 h(x) 采样位置 X_S
4. **CNV_CHECK**：检查 X_S 处温度是否已知

### 转移边

- **BND 出口** → CNV_PROBE [RT] → CNV_TIME
- CNV_TIME → Done(Time)（时间倒退至 t_I，以初始流体温度终止）
- CNV_TIME → CNV_SAMPLE → CNV_CHECK
- CNV_CHECK → Done(Dissipation)（温度已知，对流终止）
- CNV_CHECK → **BND 入口**（温度未知，重新触发界面耦合）

### 作图规范

本图遵循 FSM 系列统一作图语言：

| 图元 | 含义 |
|------|------|
| **圆圈节点 ○/◎** | 状态链起止点，转移到/自其他状态机或模块（如 ◎ BND 入口、◎ Done(*)） |
| **方形节点 □** | 不引入分支的线性状态（如 CNV_TIME、CNV_SAMPLE） |
| **红色边框方形节点** | 含几何查询的挂起点（Wavefront 挂起/恢复边界） |
| **菱形节点 ◇** | 分支和决策状态（如 CNV_CHECK 的温度已知/未知判定） |
| **状态转移箭头 →** | 标注转移条件（概率值、判定结果等） |
| **虚线方框** | 物理或蒙特卡洛子过程分组 |

#### 本图节点映射

| 节点 | 图元类型 | 说明 |
|------|----------|------|
| CNV_PROBE | 红色边框方形 | 含 RT 查询（腔体边界探针射线），挂起点 |
| CNV_TIME | 方形 | 线性状态：瞬态时间回溯采样 |
| CNV_SAMPLE | 方形 | 线性状态：壁面位置采样 |
| CNV_CHECK | 菱形 | 分支：温度已知/未知 |
| ◎ BND 入口 | 圆圈 | 转移至 BND 模块 |
| ◎ Done(Time) | 圆圈 | 终止：时间回溯至 t_I |
| ◎ Done(Dissipation) | 圆圈 | 终止：对流耗散 |

### 图注

- 中文：CNV 对流换热模块的状态转移图（4 个状态，1 个 RT 查询）。圆圈节点为模块入口/出口及终止条件，红色边框方形为含 RT 查询的挂起点，方形为线性计算状态，菱形为分支决策状态。
- 英文：FSM of the CNV convective heat transfer module (4 states, 1 RT query). Circle nodes denote module entry/exit and termination; red-bordered rectangles indicate RT query suspension points; rectangles are linear states; diamonds represent branching decisions.
