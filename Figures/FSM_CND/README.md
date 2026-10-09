# CND 模块状态转移图

**文件名**: `FSM_CND.pdf` (SVG → PDF)  
**放置位置**: §3.4.1.3 CND 子小节末尾  
**尺寸**: 0.7\textwidth  

## 内容描述

CND（固体传导）模块的 FSM 状态转移图，包含两种游走方案（δ-Sphere 和 WoS）。可绘制为左右并列或上下分区。

### δ-Sphere 方案（6 个状态）

1. **CND_DS_SAMPLE**：采样均匀球面方向 Ω
2. **CND_DS_RT**：沿 ±Ω 双向射线查询 → **[RT 查询]**
3. **CND_DS_STEP**：计算 δ̃ = min(δ, s⁺, s⁻)，跳跃至新位置
4. **CND_DS_ENC**：ENC 查询获取新位置腔体归属 → **[ENC 查询]**（单出口，纯查询）
5. **CND_DS_CHECK**：ε-壳层判定（决策节点，δ̃ < δ ?）
6. **CND_DS_TIME**：瞬态时间回溯采样

转移：
- CND_DS_SAMPLE → CND_DS_RT [RT] → CND_DS_STEP → CND_DS_ENC [ENC] → CND_DS_CHECK
- CND_DS_CHECK → **BND 入口**（δ̃ < δ，进入 ε-壳层，吸附至边界）
- CND_DS_CHECK → CND_DS_TIME（δ̃ = δ，仍在固体内部）
- CND_DS_TIME → CND_DS_SAMPLE（继续游走）
- CND_DS_TIME → Done(Time)（时间倒退至 t_I）

### WoS 方案（8 个状态）

1. **CND_WOS_CP1**：CP 查询获取最近面距离 → **[CP 查询]**
2. **CND_WOS_CHECK**：检查是否进入 ε-壳层
3. **CND_WOS_SAMPLE**：在 d_wos 半径球面采样方向
4. **CND_WOS_JUMP**：跳跃至新位置
5. **CND_WOS_CP2**：第二次 CP 查询验证位置 → **[CP 查询]**
6. **CND_WOS_VALID**：位置合法性检查
7. **CND_WOS_RT**：回退 RT 射线修正（条件性）→ **[RT 查询]**（可选）
8. **CND_WOS_TIME**：瞬态时间回溯采样

转移：
- CND_WOS_CP1 [CP] → CND_WOS_CHECK
- CND_WOS_CHECK → **BND 入口**（d_wos ≤ ε_shell，吸附至边界）
- CND_WOS_CHECK → CND_WOS_SAMPLE → CND_WOS_JUMP → CND_WOS_CP2 [CP] → CND_WOS_VALID
- CND_WOS_VALID → CND_WOS_TIME（验证通过）
- CND_WOS_VALID → CND_WOS_RT [RT]（验证失败）→ CND_WOS_TIME
- CND_WOS_TIME → CND_WOS_CP1（继续游走）
- CND_WOS_TIME → Done(Time)

### 作图规范

本图遵循 FSM 系列统一作图语言：

| 图元 | 含义 |
|------|------|
| **圆圈节点 ○/◎** | 状态链起止点，转移到/自其他状态机或模块（如 ◎ BND 入口、◎ Done(Time)） |
| **方形节点 □** | 不引入分支的线性状态（如 CND_DS_STEP、CND_DS_TIME、CND_WOS_SAMPLE、CND_WOS_JUMP） |
| **红色边框方形节点** | 含几何查询的挂起点（Wavefront 挂起/恢复边界），标注查询类型 [RT]/[CP]/[ENC] |
| **菱形节点 ◇** | 分支和决策状态（如 CND_DS_CHECK 的 ε-壳层判定、CND_WOS_VALID 的位置合法性检查） |
| **状态转移箭头 →** | 标注转移条件（概率值、判定结果等） |
| **虚线方框** | 物理或蒙特卡洛子过程分组（如 δ-Sphere 方案 / WoS 方案） |

#### 本图节点映射

**δ-Sphere 方案**：

| 节点 | 图元类型 | 说明 |
|------|----------|------|
| CND_DS_SAMPLE | 方形 | 线性：采样均匀球面方向 |
| CND_DS_RT | 红色边框方形 | 含 RT 查询（±Ω 双向射线），挂起点 |
| CND_DS_STEP | 方形 | 线性：计算 δ̃，跳跃至新位置 |
| CND_DS_ENC | 红色边框方形 | 含 ENC 查询（腔体归属验证），挂起点 |
| CND_DS_CHECK | 菱形 | 分支：ε-壳层判定（δ̃ < δ？） |
| CND_DS_TIME | 方形 | 线性：瞬态时间回溯 |

**WoS 方案**：

| 节点 | 图元类型 | 说明 |
|------|----------|------|
| CND_WOS_CP1 | 红色边框方形 | 含 CP 查询（最近面距离），挂起点 |
| CND_WOS_CHECK | 菱形 | 分支：ε-壳层判定 |
| CND_WOS_SAMPLE | 方形 | 线性：球面采样方向 |
| CND_WOS_JUMP | 方形 | 线性：跳跃至新位置 |
| CND_WOS_CP2 | 红色边框方形 | 含 CP 查询（位置验证），挂起点 |
| CND_WOS_VALID | 菱形 | 分支：位置合法性检查 |
| CND_WOS_RT | 红色边框方形 | 含 RT 查询（回退射线修正，条件性），挂起点 |
| CND_WOS_TIME | 方形 | 线性：瞬态时间回溯 |

### 图注

- 中文：CND 固体传导模块的状态转移图，左侧为 δ-球面游走方案（5 个状态），右侧为经典 WoS 游走方案（8 个状态）。圆圈节点为模块入口/出口及终止条件，红色边框方形为含几何查询的挂起点（RT/CP/ENC），方形为线性计算状态，菱形为分支决策状态。虚线方框分别包围两种游走方案。
- 英文：FSM of the CND solid conduction module. Left: Walk-on-δ-Sphere (5 states); Right: Walk-on-Sphere (8 states). Circle nodes denote module entry/exit and termination; red-bordered rectangles indicate geometric query suspension points (RT/CP/ENC); rectangles are linear states; diamonds represent branching decisions. Dashed boxes group each walking scheme.
