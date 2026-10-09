# BND 模块状态转移图

**文件名**: `FSM_BND.pdf` (SVG → PDF)  
**放置位置**: §3.4.1.5 BND 子小节末尾  
**尺寸**: 0.9\textwidth，横向  

## 内容描述

BND（界面耦合）模块的分层 FSM 状态转移图。BND 是整个求解器中最复杂的模块，包含 5 个子模块、25+ 状态节点。采用分层布局：外层为界面类型分发与 ENC 前置查询，内层展开各子模块细节。SFN 子模块为双层嵌套循环结构（外层 null-collision、内层 CONTINUE 精化），含 6 个状态节点 + 显式递归栈。

---

### 外层：界面分发 + ENC 前置查询（3 个节点）

#### 状态节点

1. **BND_DISPATCH**（入口）：根据界面类型分流
2. **BND_ENC**：腔体归属查询 → **[ENC 查询]**
3. **BND_ENC_CHECK**（决策◇）：picard_order 判定 + 界面类型路由

#### 转移边

- **RAD/CND/CNV 出口** → BND_DISPATCH
- BND_DISPATCH →(S-F / S-S)→ BND_ENC [ENC]
- BND_DISPATCH →(Outer Env)→ EXT_DIRECT（EXT 不需要 ENC 前置）
- BND_ENC → BND_ENC_CHECK
  - S-F, picard_order = 1 → **SF_REINJECT**
  - S-F, picard_order > 1 → **SFN_DISPATCH**
  - S-S → **SS_REINJECT**

#### 关于 ENC

ENC 是 SF/SFN/SS 的**共享前置查询**，用于确定当前路径点所属的腔体（Enclosure）。在多腔体场景中，同一三角面片可能属于不同腔体（不同 ε、k、h 参数），因此必须在物理计算前确认归属。

ENC 是**后端化的 GPU 批量查询**（与 RT/CP 同级）。CPU 侧提交查询位置 `pos`，GPU 侧返回 `enc_id`（腔体编号），中间的多步几何推理（BVH 定位、轴对齐投票、歧义仲裁）完全封装在后端内部，不暴露给状态机。

> **设计决策**：ENC 后端内部仍分多个 GPU 往返步骤（详见第四章），但从 Wavefront 调度器视角，ENC 与 RT/CP 具有相同的接口语义——一次挂起、一次恢复、一个结果，因此在 FSM 中建模为**单个挂起节点**。将后端实现细节泄露到状态机会破坏查询类型无关性（query-type-agnostic）设计。

---

### 子模块 1：SF（固-流界面 Picard-1，4 个状态）

SF 处理固-流界面的一阶 Picard 迭代。路径在界面处依据能量平衡方程分支为传导/对流/辐射三个模式。

#### 状态节点

1. **SF_REINJECT**（入口）：沿固体法向 δ-偏移发射重注入射线 → **[RT 查询]**
   - 计算 x − δn̂ 处的注入候选位置，用于传导项的 δ-球近似
   - 同时读取 ENC 前置结果验证 δ-偏移未跨越腔体边界
2. **SF_PROB_DISPATCH**（决策◇）：计算 P_cond / P_conv / P_rad，Russian Roulette 选择分支
3. **SF_NULL_TRACE**：使用上界概率 P_rad^ub = ĥ_R/(…) 发射辐射射线 → **[RT 查询]**
4. **SF_NULL_CHECK**（决策◇）：null-collision accept/reject 判定（h_R/ĥ_R 与随机数比较）

#### 转移边

```
BND_ENC_CHECK →(S-F, picard=1)→ SF_REINJECT [RT]
                                     │
                                     ▼
                            SF_PROB_DISPATCH ◇
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
             ◎ CND 入口       ◎ CNV 入口      SF_NULL_TRACE [RT]
             (P_cond)          (P_conv)              │
                                                     ▼
                                              SF_NULL_CHECK ◇
                                               │           │
                                            (accept)    (reject)
                                               ▼           │
                                          ◎ RAD 入口       │
                                         （尾递归）         │
                                                            │
                        ┌───────────────────────────────────┘
                        ▼
              SF_PROB_DISPATCH  ← null-collision 回边（红色虚线）
```

#### 关键说明

- **采样计算内聚于查询节点**：图中 [RT] 查询节点（如 SF_REINJECT）在内部包含为查询准备参数的采样计算步骤（δ-偏移方向、射线原点等）。从 wavefront FSM 看，采样与查询提交在同一阶段处理——恢复状态 → 计算射线参数 → 提交查询 → 挂起——不构成独立挂起点。源码中每个 `path_phase` 对应一个挂起/恢复周期，因此 SAMPLE 不拆分为独立节点。
- **尾递归优化**：SF_NULL_CHECK accept 后，SF 无后续上下文（不需要收集子路径结果），因此直接将路径状态转移至 RAD_EMIT，栈展平（tail call）。P_rad 命中时逻辑上发起辐射子路径，但 Wavefront 架构在此已无需继续进行的 SF 上下文，路径成为 RAD 引导的子路径。与 SFN 不同，SF 不推栈。
- **null-collision 回边**：reject 时将 phase 设回 SF_PROB_DISPATCH，下一轮 wavefront 迭代重新采样。这是 FSM 层面的状态循环（非 while 循环）。
- **ENC 验证折叠**：源码中 `SF_REINJECT_ENC` 状态（读取 enc_id 验证腔体归属）不产生查询也不产生分支，已折叠进 SF_REINJECT 节点。

---

### 子模块 2：SFN（PicardN 高阶迭代，6 个状态）

SFN 在温差较大场景中替代 SF，通过 null-collision + 渐进式 h_R 精化求解界面温度。与 SF 的区别在于：SF 发射单条辐射子路径后做 accept/reject，SFN 逐步采样最多 6 条子路径（T₀–T₅），每采一条就缩紧 h_R 的上下界，尝试提前做出 accept/reject 判定。

**入口条件**：BND_ENC_CHECK 判定 picard_order > 1 时进入 SFN（而非 SF）。

#### 物理原理：渐进式 h_R 精化

界面辐射传递系数 $h_R = 4\sigma\varepsilon\theta^3$ 依赖于未知温度 $\theta$。SFN 将 $\theta^3$ 展开为对称乘积项，按 $T_0 \cdots T_5$ 逐步替换 $T_\min / \hat{T}$ 占位：

| 已知子路径 | $h_{R,\min}$ 中展开项 | $h_{R,\max}$ 中展开项 | 精度 |
|-----------|----------------------|----------------------|------|
| i=1 (T₀) | $T_\min^3 + 3T_\min^2 T_0$ | $\hat{T}^3 + 3\hat{T}^2 T_0$ | 粗 |
| i=2 (T₀,T₁) | $T_\min^3 + T_\min^2 T_0 + 2T_\min T_0 T_1$ | 对应 $\hat{T}$ 替换 | ↓ |
| i=3 (T₀–T₂) | $T_\min^3 + T_\min^2 T_0 + T_\min T_0 T_1 + T_0 T_1 T_2$ | 对应 $\hat{T}$ 替换 | ↓ |
| i=4 (T₀–T₃) | $T_\min^2 T_3 + T_\min T_0 T_3 + T_0 T_1 T_3 + T_0 T_1 T_2$ | 对应 $\hat{T}$ 替换 | ↓ |
| i=5 (T₀–T₄) | $T_\min T_3 T_4 + T_0 T_3 T_4 + T_0 T_1 T_3 + T_0 T_1 T_2$ | 对应 $\hat{T}$ 替换 | ↓ |
| i=6 (T₀–T₅) | $T_3 T_4 T_5 + T_0 T_3 T_4 + T_0 T_1 T_3 + T_0 T_1 T_2$ | **= min（精确）** | 精确 |

每步计算 $P_{rad,\min} = h_{R,\min} \varepsilon / \hat{h}_R$ 和 $P_{rad,\max} = h_{R,\max} \varepsilon / \hat{h}_R$，与随机数 $r$ 比较：
- $r < P_{conv} + P_{cond} + P_{rad,\min}$ → **Early Accept**（$r$ 必在辐射带内）
- $r > P_{conv} + P_{cond} + P_{rad,\max}$ → **Early Reject / Null Collision**（$r$ 必在 null zone）
- 否则 → **Continue**（不确定，需更多 Ti 缩紧区间）

i=6 时 min == max，精确判定 accept 或 null collision（不再有 CONTINUE 可能）。

#### 递归栈设计

- 显式预分配栈 `path_sfn_data.stack[MAX_PICARD_DEPTH]`（`MAX_PICARD_DEPTH = 3`，~3.7 KB/path）
- 替代 DFS 递归的函数调用栈，每层记录：`T_values[6]`、`T_count`、`r`、`p_conv`、`p_cond`、`h_hat`、`rwalk_saved`、`T_saved`、`bnd_sf_backup`
- 存储在 path_state 的**冷数据块**中（SoA 布局，仅 SFN 路径加载，不影响热路径性能）
- 栈深度计数器 `sfn_arr[slot].depth`，depth > 0 表示路径当前处于 SFN 子路径递归中

#### 双层嵌套循环结构

SFN 包含两层语义不同的循环：

- **内循环（CONTINUE）**：`SFN_CHECK` → `SFN_COMPUTE_Ti` — i<6 且 [min, max] 区间含 r，采集下一个 Ti 缩紧界
- **外循环（NULL_COLLISION）**：`SFN_CHECK` → `SFN_PROB_DISPATCH` — r 确定性落在 null zone，恢复快照，重抽 r，整轮重来

#### 状态节点

1. **SFN_PROB_DISPATCH**（SFN 入口 / 外循环重入点）：
   - 首次进入：初始化 h_hat、保存 rwalk/T 快照（`rwalk_snapshot`、`T_snapshot`）、抽随机数 r、计算 P_conv/P_cond，将 r 落入 conv/cond/rad band
   - Null-collision 重入：h_hat 保持不变（`sfn_null_collision()` 不重置），恢复快照，重抽 r
   - 若 r 落入 conv → ◎ CND 入口
   - 若 r 落入 cond → ◎ CNV 入口
   - 若 r 落入 rad band → 发射辐射射线，转 SFN_RAD_TRACE

2. **SFN_RAD_TRACE**：辐射子路径射线发射 → **[RT 查询]**

3. **SFN_RAD_DONE**：处理射线返回结果，转入 SFN_COMPUTE_Ti

4. **SFN_COMPUTE_Ti**（非查询，内含两级决策）：
   - **CHECK_T**：子路径采样源温度已知（`T.done`）？
     - **是（Temperature Known）**：直接记录 `T_values[i++]`，跳转 SFN_CHECK（**不经过 RESUME，不涉及栈操作**）
     - **否**：需要完整子路径求解 → 进入 CHECK_STACK
   - **CHECK_STACK**：递归栈深度检查（`depth < MAX_PICARD_DEPTH`）？
     - **OK, depth+1**：push 当前层上下文到栈，depth++，将路径 phase 设为子路径入口（等效于递归调用 `sample_coupled_path()`），子路径复用主 FSM 全部状态集
     - **Overflow**：栈溢出回退 → 以 SF（Picard-1）方式同步求解（当前实现为 sync DFS fallback，保证 CPU/GPU bit-exact 一致性）

5. **SFN_COMPUTE_Ti_RESUME**（cascade 唤起点）：
   - 子路径完成并返回温度后，由 cascade 拦截 PATH_DONE（条件：`sfn_arr[slot].depth > 0`），将 phase 改写为 COMPUTE_Ti_RESUME
   - 执行 pop 栈层：`depth--`，恢复父层 SFN 上下文（`bnd_sf_backup`、`rwalk_saved`、`T_saved`）
   - 记录返回温度到 `T_values[i++]`
   - 转入 SFN_CHECK

6. **SFN_CHECK**（决策◇，即 `CHECK_PMIN_PMAX`）：
   - 根据已收集的 T_count 个温度计算 h_R 上下界
   - **ACCEPT**（$r < P_{conv} + P_{cond} + P_{rad,\min}$）→ ◎ RAD 入口（`sfn_switch_in_radiative()`，切换到辐射端点 rwalk_s）
   - **NULL_COLLISION**（i=6 精确判定，或 i<6 且 $r > P_{conv} + P_{cond} + P_{rad,\max}$）→ SFN_PROB_DISPATCH（`sfn_null_collision()`，恢复快照，外循环重来）
   - **CONTINUE**（i<6，区间含 r）→ SFN_COMPUTE_Ti（内循环，采集下一个 Ti）

#### 转移边

```
┌──────────────── NULL_COLLISION（外循环）─────────────────────────┐
│                                                                  │
▼                                                                  │
SFN_PROB_DISPATCH ──→ SFN_RAD_TRACE [RT] ──→ SFN_RAD_DONE        │
 │    │                                            │               │
 │    ├→ ◎ CND (P_cond)                    SFN_COMPUTE_Ti         │
 │    └→ ◎ CNV (P_conv)                      │           │        │
 │                                      ◇ CHECK_T        │        │
 │                                    ╱          ╲        │        │
 │                             Temp Known     Not Known   │        │
 │                                 │              │       │        │
 │                                 │        ◇ CHECK_STACK │        │
 │                                 │       ╱            ╲ │        │
 │                                 │   OK depth+1   Overflow       │
 │                                 │      │             │          │
 │                                 │    ◉ FSM      ◉ FSM_SF       │
 │                                 │   (子路径)    (SF 回退)       │
 │                                 │      │             │          │
 │                                 │  [cascade 拦截 PATH_DONE]     │
 │                                 │      │             │          │
 │                                 │  SFN_COMPUTE_Ti_RESUME        │
 │                                 │      │                        │
 │                                 └──┬───┘                        │
 │                                    ▼                            │
 │                              SFN_CHECK ◇ ─── CONTINUE ──→ SFN_COMPUTE_Ti
 │                               │       │                    （内循环）
 │                            ACCEPT  NULL_COLLISION ──────────────┘
 │                               │
 │                               ▼
 │                          ◎ RAD 入口
 │                        （sfn_switch_in_radiative）
```

#### 关键说明

- **两层循环嵌套**：外循环（null-collision）包住整个内循环（CONTINUE）。外循环是概率空间固有的 null-collision 重采样（r 命中虚拟区间，整轮作废）；内循环是渐进精化（i<6 且界限不确定，再采一个 Ti）。两者语义完全不同。
- **i=6 时仍可能 NULL_COLLISION**：6 条子路径全部采完后 h_R 精确（min == max），但 r 仍可能落在 null zone（$P_{conv} + P_{cond} + P_{rad,exact} < r < 1$）。这不是"对 h_R 不确定的重试"，而是 r 确定性地命中了用 $\hat{h}_R$ 膨胀概率空间时引入的虚拟吸收截面。
- **Temperature Known 快捷路径**：SFN_COMPUTE_Ti 内 CHECK_T 判定 `T.done` 时（子路径采样源已有已知温度），直接记录 T_values[i] 并跳到 SFN_CHECK，**不经过 CHECK_STACK、不推栈、不进入子路径 FSM、不经过 RESUME**。这是最常见的快速路径。
- **子路径复用主 FSM**：push 栈后子路径共享同一 path_state 的 phase 字段，遍历完整的 RAD/BND/CND/CNV 状态集。子路径返回（PATH_DONE）时由 cascade 拦截，条件为 `sfn_arr[slot_idx].depth > 0`（三处检查点：`advance_path_to_first_ray()`、`compact_active_paths()`、主 cascade 循环），改写 phase 为 COMPUTE_Ti_RESUME。
- **步函数 SFN 无感知**：除 `compute_Ti`（push）和 `compute_Ti_resume`（pop）外，所有其他步函数（包括所有正常模块的 PATH_DONE 设置）完全不知道 SFN 递归的存在。SFN 复杂度被隔离在 2 个步函数 + cascade 的一行 depth 检查中。
- **Null-collision 快照恢复**：`sfn_null_collision()` 恢复 `rwalk_snapshot`、`T_snapshot`、`hvtx_saved`，并重置 green_path limit。h_hat 保持不变（上界不随循环改变），因此 PROB_DISPATCH 重入时跳过初始化直接重抽 r。
- **SF 回退（栈溢出）**：当前实现在 depth == MAX_PICARD_DEPTH 时回退为同步 DFS 调用（`sync_DFS_fallback`），目的是保证 CPU/GPU bit-exact 一致性以便验证。理论上以 SF（Picard-1 null-collision）方式回退同样统计无偏且更适合 wavefront 架构（避免同步阻塞），但会牺牲 bit 可重复性。

---

### 子模块 3：SS（固-固界面，2 个状态）

SS 处理两个固体接触面的热传导耦合。两侧必须满足热流连续性条件，路径按导热比选择一侧继续传导游走。

#### 状态节点

1. **SS_REINJECT**（入口）：双侧 δ-注入射线 → **[RT 查询 ×4]**
   - 固体 1：法向射线 + 偏移校正射线 → 候选位置 x − δ₁n̂
   - 固体 2：反法向射线 + 偏移校正射线 → 候选位置 x + δ₂n̂
   - 4 条射线打包为单次 RT 批量提交
   - 同时读取 ENC 前置结果验证两侧 δ-偏移未跨越腔体边界
2. **SS_SELECT**（决策◇）：按导热比概率选侧
   - P_side1 = (k₁/δ₁) / (k₁/δ₁ + k₂/δ₂)
   - P_side2 = 1 − P_side1

#### 转移边

```
BND_ENC_CHECK →(S-S)→ SS_REINJECT [RT ×4]
                            │
                            ▼
                       SS_SELECT ◇
                      │              │
                (选固体 1)       (选固体 2)
                 P_side1          P_side2
                      │              │
                      ▼              ▼
               ◎ CND 入口       ◎ CND 入口
              （x − δ₁n̂）     （x + δ₂n̂）
```

#### 关键说明

- SS 只产生传导分支（两侧均为固体，无辐射/对流），始终退出到 CND。
- **ENC 验证折叠**：源码中 `SS_REINJECT_ENC` 状态已折叠进 SS_REINJECT 节点（同 SF 的处理方式）。

---

### 子模块 4：EXT（外部环境，4 个状态）

EXT 处理路径到达场景外部边界时的净辐射通量计算。包含太阳直射、天空漫射两个辐射源，各需独立的遮挡检测。三次 RT 查询存在**严格顺序依赖**（前一步结果决定后一步采样方向/权重），不可合并。

每个 RT 查询节点内聚了前置采样计算（射线参数准备）和后置结果评估为一体，遵循"一个挂起点 = 一个节点"原则。

#### 状态节点

1. **EXT_DIRECT**：太阳直射通道 → **[RT 查询]**
   - 含：外部边界参数初始化 + 太阳方向阴影射线 + 直射贡献评估
2. **EXT_DIFFUSE**：天空漫射通道 → **[RT 查询]**
   - 含：天空半球方向采样 + 漫射射线 + 漫射命中处理
3. **EXT_SHADOW**：漫射遮挡验证通道 → **[RT 查询]**
   - 含：遮挡方向计算 + 阴影射线 + 遮挡确认
4. **EXT_COMBINE**：汇总直射 + 漫射 → 净辐射通量

#### 转移边

```
BND_DISPATCH →(Outer Env)→ EXT_DIRECT [RT]
                                │
                                ▼
                          EXT_DIFFUSE [RT]
                                │
                                ▼
                          EXT_SHADOW [RT]
                                │
                                ▼
                          EXT_COMBINE
                                │
                                ▼
                          ◎ PATH_DONE（路径终止）
```

#### 关键说明

- **严格顺序链**：3 个 RT 查询必须顺序执行（每步结果用于下步参数），EXT_COMBINE 在三步全部完成后汇总。
- **布局选择**：图中可采用双列布局（直射列 / 漫射列）以节省纵向空间，但逻辑上仍为单链顺序推进。
- **状态压缩**：源码中 8 个 `path_phase` 状态（CHECK + 3×TRACE + 3×RESULT + FINALIZE）压缩为 4 个图节点。每个查询节点内聚了 SAMPLE→RT→EVAL 三阶段。

---

### 节点命名对照表

| 图中名称 | 源码 path_phase | 节点类型 | 说明 |
|----------|----------------|----------|------|
| BND_DISPATCH | — | 计算 | 界面类型路由 |
| BND_ENC | PATH_ENC_* | **查询 [ENC]** | 腔体归属（3 个内部挂起点合并） |
| BND_ENC_CHECK | — | 决策 ◇ | picard_order + 界面类型路由 |
| SF_REINJECT | PATH_BND_SF_REINJECT_SAMPLE | **查询 [RT]** | 含折叠的 SF_REINJECT_ENC |
| SF_PROB_DISPATCH | PATH_BND_SF_PROB_DISPATCH | 决策 ◇ | P_cond/P_conv/P_rad 概率分支 |
| SF_NULL_TRACE | PATH_BND_SF_NULLCOLL_RAD_TRACE | **查询 [RT]** | null-collision 辐射射线 |
| SF_NULL_CHECK | PATH_BND_SF_NULLCOLL_DECIDE | 决策 ◇ | accept/reject |
| SFN_PROB_DISPATCH | PATH_BND_SFN_PROB_DISPATCH | 计算/决策 | P_conv/P_cond/P_rad 概率 + 模式分支 + null-collision 重入 |
| SFN_RAD_TRACE | PATH_BND_SFN_RAD_TRACE | **查询 [RT]** | 辐射子路径射线发射 |
| SFN_RAD_DONE | — | 计算 | 射线结果处理 → COMPUTE_Ti |
| SFN_COMPUTE_Ti | — | 决策 ◇ | CHECK_T（直接记录）/ CHECK_STACK（push 栈 / SF 回退） |
| SFN_COMPUTE_Ti_RESUME | — | 计算 | cascade 唤起，pop 栈恢复父层上下文 |
| SFN_CHECK | PATH_BND_SFN_CHECK_PMIN_PMAX | 决策 ◇ | ACCEPT / NULL_COLLISION / CONTINUE 三出口 |
| SS_REINJECT | PATH_BND_SS_REINJECT_SAMPLE | **查询 [RT ×4]** | 含折叠的 SS_REINJECT_ENC |
| SS_SELECT | PATH_BND_SS_REINJECT_DECIDE | 决策 ◇ | 导热比选侧 |
| EXT_DIRECT | EXT_CHECK + EXT_DIRECT_TRACE + EXT_DIRECT_RESULT | **查询 [RT]** | 初始化 + 太阳阴影 + 直射评估 |
| EXT_DIFFUSE | EXT_DIFFUSE_TRACE + EXT_DIFFUSE_RESULT | **查询 [RT]** | 天空漫射 + 命中处理 |
| EXT_SHADOW | EXT_DIFFUSE_SHADOW_TRACE + SHADOW_RESULT | **查询 [RT]** | 遮挡验证 + 确认 |
| EXT_COMBINE | PATH_BND_EXT_FINALIZE | 计算 | 汇总输出 |

> **遗留状态**：源码中存在 `PATH_COUPLED_BOUNDARY_REINJECT_SAMPLE`（未带 BND_ 前缀的旧命名），与 BND_DISPATCH 功能重叠，不在图中体现。

---

### 作图规范

本图遵循 FSM 系列统一作图语言：

| 图元 | 含义 |
|------|------|
| **圆圈节点 ○/◎** | 状态链起止点，转移到/自其他状态机或模块（如 ◎ CND 入口、◎ RAD 入口、◎ PATH_DONE） |
| **方形节点 □** | 不引入分支的线性状态（如 SFN_RAD_DONE、SFN_COMPUTE_Ti_RESUME、EXT_COMBINE） |
| **红色边框方形节点** | 含几何查询的挂起点（Wavefront 挂起/恢复边界），标注查询类型 [RT]/[ENC] |
| **菱形节点 ◇** | 分支和决策状态（如 BND_ENC_CHECK、SF_PROB_DISPATCH、SF_NULL_CHECK、SFN_CHECK、SS_SELECT） |
| **状态转移箭头 →** | 标注转移条件（概率值、判定结果等） |
| **虚线方框** | 物理或蒙特卡洛子过程分组（ENC / SF / SFN / SS / EXT 五个子模块） |

**补充视觉标记**：
- null-collision 回边（SF_NULL_CHECK → SF_PROB_DISPATCH、SFN_CHECK → SFN_PROB_DISPATCH）：**红色虚线箭头**，标注 "reject (null collision)"
- SFN 内循环回边（SFN_CHECK → SFN_COMPUTE_Ti）：**蓝色虚线箭头**，标注 "i<6, need more Ti"
- SFN 子路径递归（SFN_COMPUTE_Ti → ◉ FSM 主状态集）：**蓝色虚线**，标注 "push stack, depth++"
- cascade 返回（◉ FSM → SFN_COMPUTE_Ti_RESUME）：**蓝色虚线**，标注 "intercept PATH_DONE, depth>0"

#### 本图节点映射

| 图中名称 | 源码 path_phase | 图元类型 | 说明 |
|----------|----------------|----------|------|
| BND_DISPATCH | — | 菱形 | 界面类型路由（S-F/S-S/Outer Env） |
| BND_ENC | PATH_ENC_* | **红色边框方形 [ENC]** | 腔体归属（3 个内部挂起点合并） |
| BND_ENC_CHECK | — | 菱形 | picard_order + 界面类型路由 |
| SF_REINJECT | PATH_BND_SF_REINJECT_SAMPLE | **红色边框方形 [RT]** | 含折叠的 SF_REINJECT_ENC |
| SF_PROB_DISPATCH | PATH_BND_SF_PROB_DISPATCH | 菱形 | P_cond/P_conv/P_rad 概率分支 |
| SF_NULL_TRACE | PATH_BND_SF_NULLCOLL_RAD_TRACE | **红色边框方形 [RT]** | null-collision 辐射射线 |
| SF_NULL_CHECK | PATH_BND_SF_NULLCOLL_DECIDE | 菱形 | accept/reject |
| SFN_PROB_DISPATCH | PATH_BND_SFN_PROB_DISPATCH | 菱形 | 概率计算 + 模式分支 + null-collision 重入 |
| SFN_RAD_TRACE | PATH_BND_SFN_RAD_TRACE | **红色边框方形 [RT]** | 辐射子路径射线发射 |
| SFN_RAD_DONE | — | 方形 | 射线结果处理 |
| SFN_COMPUTE_Ti | — | 菱形 | CHECK_T / CHECK_STACK 两级决策 |
| SFN_COMPUTE_Ti_RESUME | — | 方形 | cascade pop 恢复父层上下文 |
| SFN_CHECK | PATH_BND_SFN_CHECK_PMIN_PMAX | 菱形 | ACCEPT / NULL_COLLISION / CONTINUE 三出口 |
| SS_REINJECT | PATH_BND_SS_REINJECT_SAMPLE | **红色边框方形 [RT ×4]** | 含折叠的 SS_REINJECT_ENC |
| SS_SELECT | PATH_BND_SS_REINJECT_DECIDE | 菱形 | 导热比选侧 |
| EXT_DIRECT | EXT_CHECK + EXT_DIRECT_* | **红色边框方形 [RT]** | 太阳直射阴影 + 评估 |
| EXT_DIFFUSE | EXT_DIFFUSE_* | **红色边框方形 [RT]** | 天空漫射 + 命中处理 |
| EXT_SHADOW | EXT_DIFFUSE_SHADOW_* | **红色边框方形 [RT]** | 遮挡验证 + 确认 |
| EXT_COMBINE | PATH_BND_EXT_FINALIZE | 方形 | 汇总输出 |

> **遗留状态**：源码中存在 `PATH_COUPLED_BOUNDARY_REINJECT_SAMPLE`（未带 BND_ 前缀的旧命名），与 BND_DISPATCH 功能重叠，不在图中体现。

### 图注

- 中文：BND 界面耦合模块的分层状态转移图，含 ENC(腔体归属)、SF(固-流界面)、SFN(PicardN 高阶迭代)、SS(固-固界面)和 EXT(外部环境)五个子模块，虚线方框包围各子模块。圆圈节点为模块入口/出口及终止条件，红色边框方形为含几何查询的挂起点（RT/ENC），方形为线性计算状态，菱形为分支决策状态。红色虚线回边标记 null-collision 循环，蓝色虚线标记 SFN 子路径迭代与栈递归。
- 英文：Hierarchical FSM of the BND interface coupling module with five sub-modules: ENC, SF, SFN, SS, and EXT, each enclosed in a dashed box. Circle nodes denote module entry/exit and termination; red-bordered rectangles indicate geometric query suspension points (RT/ENC); rectangles are linear states; diamonds represent branching decisions. Red dashed back-edges mark null-collision loops; blue dashed edges mark SFN sub-path iteration and stack recursion.
