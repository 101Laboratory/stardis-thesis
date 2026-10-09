# 第四章写作思路汇总

**章节标题**：基于 OptiX 的 GPU 硬件光追查询后端  
**文件**：`4_RTBackend.tex`

---

## 学术化写作说明

> 本章是第三章 Wavefront 求解器的查询后端实现，二者合称本文第二个核心贡献。第三章在架构层面证明了批量查询的必要性并规约了三类查询需求（RT/CP/ENC）；本章提出满足这些需求的一种具体 GPU 实现方案——基于 NVIDIA OptiX 的统一批量查询后端。"OptiX" 仅是实现载体，核心学术贡献在于：对三类异构几何查询的 GPU 映射设计，尤其是 CP 查询的 AABB 代理等价重构与正确性论证，以及 ENC 查询的 Jordan–Brouwer 分解方案。
>
> **写作时须持续保持的两个学术视角**：
> - **问题视角先于方案**：每类查询先形式化问题（查询的输入/输出/正确性条件），再提出 GPU 映射，再论证映射正确性，最后给出代价分析。不要先描述"怎么实现"再倒推"为什么"。
> - **设计决策显式化**：每个非平凡设计选择（如 RTNN 的 AABB 代理、ENC 的分解方式、统一 Pipeline）均须说明备选方案及选择理由，不可只呈现最终方案。

---

## 全章概要

本章逻辑主线：  
**需求形式化**（三类查询的形式化定义与 GPU 映射约束）→ **技术背景**（OptiX 执行模型 + RT Core）→ **三类查询 GPU 映射**（本章核心贡献）→ **统一架构实现**（映射的工程整合）→ **实验验证**

| 节 | 内容 | 承接关系 |
|----|------|---------|
| §4.1 引言 | 批量查询需求形式化 + 三类查询定义 + 本章目标 + 章节导读 | 接第三章 §3.2 规约结论 |
| §4.2 OptiX 查询加速原理 | 执行模型（pipeline/SBT/AS）+ RT Core 硬件原理 | 为 §4.3 映射方案提供技术前提 |
| §4.3 三类几何查询的 GPU 映射方案 | 映射框架形式化 + RT（平凡映射）/ CP（查询重构）/ ENC（分解论证）| **本章核心贡献** |
| §4.4 统一查询后端架构 | 单 Pipeline 整合三类映射的架构决策与代价分析 | 映射方案到系统实现的过渡 |
| §4.5 性能评估 | 吞吐量分析 + GPU 利用率 + 端到端加速比 | 验证 §4.3 方案的工程有效性 |
| §4.6 小结 | 总结本章贡献，与第三章共同构成完整 GPU 加速求解系统 | — |

**对应项目代码**：

| 角色 | 路径 | 技术栈 |
|------|------|-------|
| Baseline（对照组） | `stardis-cpu/star-3d/` | CPU + Embree |
| Ours（实验组） | `stardis-oxs3d-merge-phase/oxstar-3d/0.10/` | GPU OptiX + CUDA |

**oxstar-3d 核心源文件速查**：

| 文件 | 内容 |
|------|------|
| `src/unified_tracer.h/.cpp` | 统一管线主类 `UnifiedTracer`，封装三类查询 |
| `src/nn_query.h/.cpp` | 独立 NN/CP pipeline（早期独立版本，当前 solver 路径通过 `UnifiedTracer`） |
| `device/programs.cu` | RT 管线设备程序（raygen/closest-hit/any-hit/miss）|
| `device/nn_programs.cu` | CP 管线设备程序（zero-length ray + AABB 自定义求交）|
| `include/ray_types.h` | Ray / HitResult / MultiHitResult / FilterPerRayData |
| `include/nn_types.h` | CPQuery / CPResult / EnclosureQuery / EnclosureResult |
| `s3d_wrapper/s3d.h` | 对外统一 C API（与 Embree 后端接口完全兼容） |
| `s3d_wrapper/ox_s3d_scene_view.cpp` | `trace_ray` / `trace_rays` / `closest_point` 适配层 |

---

> ⚠️ **撰写前必读源码**：与第三章相同，本大纲提供写作框架，所有具体函数名、结构体字段、数值参数须以实际源码为准。撰写各小节前，须先通读对应源文件。

---

## §4.1 引言

**篇幅**：约 500 字  
**写作思路**：

1. **衔接第三章**：§3.2 规约分析从算法层面定义了三类几何查询（RT / CP / ENC）的语义与调用模式；§3.4 的 Wavefront 架构则在执行层面将这些查询从逐路径发出改造为每轮批量提交。本章的起点正是这两个结论的交汇点：**批量查询请求已具备，其 GPU 高效执行所需的映射方案尚未确定。**

2. **三类查询的 GPU 映射难度不均等**：
   - **RT 查询**：射线-三角网格求交是 GPU 硬件光追的原生操作，直接由 OptiX RT Core 支持，映射是平凡的。其 GPU 执行的学术问题是**批量规模与硬件吞吐量的关系**。
   - **CP 查询（最近面投影）**：在三角网格上求查询点到最近面的投影距离，**不是射线查询**，无法直接映射到光追硬件。需要将近接查询**重构为等价的光追问题**——这是本章非平凡的方法贡献之一。
   - **ENC 查询（包壳关系）**：判断空间点所属封闭腔体（多腔体 MC 热输运特有的物理分支条件，见 §3.2）。该查询可分解为 CP + 射线侧面判定两个子问题，**分解的正确性依赖几何拓扑论证**——这是本章另一个有实质内容的方法贡献。

3. **为何使用 OptiX 作为实现载体**：OptiX 与 CUDA 共享设备上下文和内存，无需跨进程数据传输；RT Core 固定功能单元直接加速 BVH 遍历与三角形求交；而 OptiX 的**自定义图元求交程序**（Custom Intersection Program）机制为 CP 查询的重构提供了必要的扩展点——在同一 BVH 加速结构下以用户定义逻辑代替三角形求交。

4. **本章目标**：针对三类查询分别给出 GPU 映射方案，并整合到基于 OptiX 的统一批量查询后端，通过性能实验验证方案的有效性。

5. **章节组织**：§4.2 介绍 OptiX 执行模型与 RT Core 硬件加速原理；§4.3 为核心，逐类给出查询 GPU 映射方案，层次由浅入深；§4.4 说明三类映射的统一架构整合决策；§4.5 报告性能实验结果；§4.6 总结。

---

## §4.2 OptiX 查询加速原理

### §4.2.1 OptiX 执行模型

**篇幅**：约 600 字  
**写作思路**：

1. **NVIDIA OptiX 概述**：OptiX 是 NVIDIA 针对光线追踪场景的高性能 GPU 编程框架（本文使用 OptiX 7+ / 9.x 低级 API），基于 CUDA 上下文运行，与 CUDA kernel 共享 GPU 内存和同步原语，无需跨进程数据传输。

2. **核心编程模型**（须通读 OptiX 7+ Programming Guide 确认版本细节）：
   - **PTX 模块（Module）**：设备端光追程序以 PTX 形式加载，OptiX 在 JIT 编译时内联到 pipeline。本文后端使用两个 PTX 模块：`programs.cu`（RT 程序）和 `nn_programs.cu`（CP 程序），统一链接到同一 Pipeline（`UnifiedTracer`）。
   - **程序类型（Program Groups）**：RayGen、Miss、Closest-Hit、Any-Hit、Intersection。本文涉及全部五类——RT 查询用 RayGen/Closest-Hit/Miss，Multi-Hit 查询用 RayGen/Any-Hit，CP 查询用 RayGen/Intersection/Miss（自定义 AABB 求交）。
   - **加速结构（GAS / IAS）**：GAS（Geometry Acceleration Structure）对单组几何体建立 BVH；IAS（Instance Acceleration Structure）组合多组 GAS 实现实例化多几何场景。本文后端采用 Multi-GAS + IAS 架构（E6 扩展），支持动态增删几何体而无需重建全局 BVH。
   - **Shader Binding Table（SBT）**：将 RayGen/Miss/HitGroup 程序与几何绑定。本文统一 Pipeline 包含三套 SBT：`SBT_RT`（单交点查询）、`SBT_MH`（多交点查询）、`SBT_NN`（CP/NN 查询），每次 `optixLaunch` 切换 SBT 以路由到对应程序。

3. **执行流程**：调用 `optixLaunch(pipeline, stream, params, sizeof(params), &sbt, nx, ny, nz)` 后，GPU 以 `nx×ny×nz` 线程并行执行 RayGen 程序；每个 RayGen 线程调用 `optixTrace()`，触发 BVH 遍历，根据命中情况调用 Closest-Hit 或 Miss；结果通过 payload registers 传回 RayGen，写入结果缓冲区。

4. **与 CUDA 协作**：`optixLaunch` 是异步的，在指定 CUDA stream 上排队，可与 CUDA kernel 流水线化执行。本文后端利用这一特性实现双流 ping-pong（见 §4.4），查询提交期间重叠 CPU 端路径状态推进（第三章 §3.4 的 Wavefront 主循环）。

**图表需求**：OptiX 执行模型流程图（optixLaunch → 线程展开 → RayGen → Traversal → Hit/Miss → payload 回写）  
**引用需求**：`\cite{parkerOptiXGeneralPurpose2010}`（OptiX 原始论文）；NVIDIA OptiX 7 Programming Guide（技术报告引用）

---

### §4.2.2 NVIDIA RT Core

**篇幅**：约 400 字  
**写作思路**：

1. **RT Core 在 GPU 中的角色**：RT Core 是 NVIDIA Turing 架构引入的固定功能硬件单元，专用于 BVH 节点遍历与光线-三角形求交两步操作，可以与 SM（CUDA Core）并行运行——即当 SM 执行着色程序时，RT Core 同步执行 BVH 遍历，绑定时延大幅降低。

2. **硬件演进**（通览已知数据后填写实际性能数字）：
   - Turing（RTX 20 系）：第 1 代 RT Core
   - Ampere（RTX 30 系）：第 2 代，BVH 遍历吞吐量约 2×（与 Turing 相比）
   - Ada Lovelace（RTX 40 系）：第 3 代，进一步提升

3. **对比 Embree（CPU 光追）**：
   - Embree 使用 ISPC SIMD 向量化，单 CPU 线程 `rtcIntersect4/8/16()` packet 接口；
   - RT Core 的 BVH 遍历对每条射线并行执行，峰值吞吐量（GRay/s）远超 CPU；
   - 实际加速比依赖 batch size（§4.5 性能分析），batch size 越大 GPU 利用率越高，差距越大。

4. **自定义图元支持**：当几何体不是三角网格（如本文 CP 查询中的 AABB 代理包围盒）时，OptiX 支持自定义 Intersection Program，用用户代码替换三角形求交——RT Core 仍做 BVH 节点遍历，求交由 SM 执行，失去部分 RT Core 加速但依然受益于 BVH 加速结构（这是 §4.3.3 RTNN 方案的基础）。

**图表需求**：RT Core 与 SM 并行关系示意图（SM 做着色 / RT Core 做遍历+求交，二者流水）  
**引用需求**：NVIDIA Turing/Ampere/Ada 架构白皮书（按实际使用 GPU 型号选取）

---

## §4.3 三类几何查询的 GPU 映射方案

### §4.3.0 映射问题的统一框架（章首过渡段，不单独成小节，约 200 字）

**写作思路**：

在进入各查询的具体设计之前，明确**查询映射**的形式化含义和三类查询的层次差异。一个几何查询的 GPU 映射须满足三个条件：
1. **语义等价**：GPU 实现的输入输出与原始查询定义（§3.2）完全相同；
2. **批量接口**：接受 $n$ 条查询的连续数组作为输入，单次 `optixLaunch` 处理全部，输出结果数组；
3. **上下文兼容**：与 CUDA 设备上下文共享，查询结果无需跨进程传输即可被下游路径状态恢复逻辑访问。

三类查询在此框架下的**映射复杂度不同**：RT 查询有现成的直接硬件映射，**映射平凡**；CP 查询不是射线查询，需**重构**为等价的光追问题，**映射非平凡**；ENC 查询依赖 CP 与 RT 的组合，**映射需要正确性论证**。以下三节按此层次递进展开。

---

### §4.3.1 RT 查询：直接硬件映射与 GPU 吞吐量特性

**篇幅**：约 500 字  
**写作思路**：

**本节核心**：RT 查询映射是平凡的，学术内容在于分析批量化的吞吐量收益，为 §4.5 实验提供理论预期。

1. **直接映射**：RT 查询（射线-网格最近/任意命中）直接由 OptiX 的 `optixTrace()` + Closest-Hit Program 实现，BVH 遍历与三角形求交完全在 RT Core 上执行，SM 仅负责写回 payload。从求解器批量射线数组到 `optixLaunch` 的 1D dispatch，映射关系是 1 对 1 的线性变换，没有算法设计空间。

2. **两条 solver 级查询路径及对应 SBT**（须对照 `programs.cu` 确认实际程序名）：
   - **GPU Filter 模式（L4）**：使用 `m_sbt_mhf`（SBT_MHF）。Raygen 在 GPU 端内联执行自相交过滤（跳过出发面）+ ε 近距过滤 + Enclosure 腔体过滤，输出单命中 `HitResult[]`，无需 CPU 重追踪。过滤参数（出发面几何 ID、ε、当前腔体 ID）以 `FilterPerRayData`（16 字节对齐）随每条射线传入；per-prim 腔体 ID（`enc_front[] / enc_back[]`）在场景构建阶段上传至显存，Any-Hit 直接索引——整个过滤过程无 CPU-GPU 往返。
   - **非 Filter 模式**：使用 `m_sbt_mh`（SBT_MH）。Raygen 收集前 $K=2$ 命中至 `MultiHitResult[]`，D2H 后 CPU 端 post-process 过滤，必要时按需重追踪。

   **注意**：`m_sbt_rt`（SBT_RT，单命中）不面向 solver 直接暴露；它被 `traceBatch()` 调用，仅在 ENC 查询内部的第二步（+X 侧判定射线）中使用（见 §4.3.3）。

3. **GPU 吞吐量特性分析**：RT Core 的性能瓶颈在于 GPU 的 wave 填满程度。关键变量是**批量规模 $n$**：当 $n$ 小于 SM 数 × 每 SM 最大活跃 warp 数时，大量 SM 空闲；当 $n$ 趋于饱和时，RT Core 达到峰值吞吐（GRay/s）。这一分析为 §4.5 中 batch size vs 吞吐量实验提供理论预期，同时印证第三章 Wavefront 架构在每轮积累足够大批量查询的必要性。

**图表需求**：吞吐量 vs batch size 定性示意曲线（欠饱和 / 趋于峰值，实测数据见 §4.5）

---

### §4.3.2 CP 查询：近接查询到光追问题的等价重构

**篇幅**：约 900 字  
**写作思路**：

**本节核心**：将一个本质上是"在三角网格上找最近点"的近接查询，等价重构为一个光追问题，并严格论证等价性。

1. **问题的困难所在**：CP 查询（§3.2 中 WoS 传导段 [A] 挂起点）的形式化定义为：给定查询点 $\mathbf{q}$，在三角网格 $\mathcal{M}$ 上求
$$
(\mathbf{p}^*, f^*) = \arg\min_{\mathbf{p} \in \mathcal{M}} \|\mathbf{p} - \mathbf{q}\|
$$
返回最近点坐标 $\mathbf{p}^*$、对应图元 $f^*$、法线和重心坐标。这不是一个射线查询：`optixTrace()` 的输入是射线（起点 + 方向），返回的是射线与三角形的**交点**；而 CP 查询需要的是查询点到三角形的**投影点**，它并不在任何特定方向射线上。因此，无法通过标准三角形图元的光追直接映射到 GPU。

2. **重构方案：AABB 代理 + 零长度射线**：

   利用 OptiX 的**自定义图元（Custom Primitive）**机制——以用户定义的 AABB 作为 BVH 叶节点，BVH 命中时触发自定义 Intersection Program——将 CP 查询等价重构为以下光追问题：

   - **代理几何**：对网格每个三角形 $f_i$，计算其紧包围盒膨胀 $r_{\text{search}}$ 后的 AABB $B_i$，以此构建独立的自定义图元 GAS（区别于 RT 查询所用的三角形 GAS）。
   - **零长度查询射线**：以查询点 $\mathbf{q}$ 为起点，$t_{\max} = \varepsilon_{\text{zero}}$ 极小，发射零长度射线。该射线实质上是一个点，BVH 遍历将访问所有包含 $\mathbf{q}$ 的 AABB $B_i$。
   - **自定义求交**：Intersection Program 被触发时精确计算 $\text{dist}(\mathbf{q}, f_i)$，通过 payload 全程维护当前最近候选 $(d^*, f^*)$；通过 `optixIgnoreIntersection()` 继续遍历（Any-Hit 语义），直到所有被访问的候选均被评估，payload 持有全局最优。

3. **等价性论证**：
   - **完备性**：设 $f^*$ 是真实最近图元，则 $\mathbf{q}$ 到 $f^*$ 的距离小于等于 $\mathbf{q}$ 到 $B^*$（$f^*$ 的 AABB 膨胀前）的距离——后者为零（$\mathbf{q}$ 落在未膨胀 AABB 内时）或负数皆不可能，实则此时 $\mathbf{q}$ 必落在膨胀后的 $B^*$ 内（由膨胀半径 $r_{\text{search}}$ 的定义保证）。故 $B^*$ 一定被零长度射线遍历命中，$f^*$ 一定被评估。
   - **正确性**：每个被评估的 $f_i$ 均计算精确的点到三角形最近点距离（双精度 `closestPointOnTriangle`，须通读 `nn_programs.cu` 确认实现），无近似。
   - **有限搜索半径**：超过 $r_{\text{search}}$ 的图元其膨胀 AABB 不包含 $\mathbf{q}$，不被访问。实践中 $r_{\text{search}}$ 设为足以覆盖最远潜在最近图元的场景相关常数。

4. **双 GAS 架构**：RT 查询和 CP 查询使用两套独立 GAS——RT 用三角形 GAS（RT Core 硬件三角形求交），CP 用 AABB 代理 GAS（BVH 遍历由 RT Core 加速，自定义求交在 SM 执行）。两套 GAS 共享相同顶点/法线显存（`d_vertices / d_indices`），无冗余。

**图表需求**：
- CP 查询重构原理图：三角形 → 膨胀 AABB → 零长度射线命中含 $\mathbf{q}$ 的 AABB → 自定义求交计算精确最近点
- 完备性示意图：$\mathbf{q}$ 落在膨胀后 AABB 内 → 真实 $f^*$ 必被评估（几何关系）

---

### §4.3.3 ENC 查询：基于拓扑分解的正确性论证

**篇幅**：约 700 字  
**写作思路**：

**本节核心**：ENC 查询是点-多面体包含关系（Point-in-Polyhedron）判定，将其分解为 CP + 单射线的理论依据来自拓扑，需给出正确性论证，而非仅描述实现步骤。

1. **问题定义**：ENC 查询（§3.2 ENC 类挂起点）的语义是：给定查询点 $\mathbf{q}$ 和多腔体场景中的封闭多面体集合 $\{\Omega_k\}$，判断 $\mathbf{q}$ 属于哪个 $\Omega_k$（腔体编号），同时返回最近面信息。这等价于对多个封闭多面体做的 Point-in-Polyhedron 判定。

2. **Baseline 方法的缺陷**：原始求解器（`star-3d` / Embree）对 ENC 查询采用多射线投票法——从 $\mathbf{q}$ 沿多个坐标轴方向发射射线，统计命中法线方向确定内外。每次 ENC 查询消耗多条射线，且 ENC 查询在每次 BND 界面事件均需执行，成为求解器的首要性能瓶颈（须以实测时间比例填写）。多射线冗余的根本原因是：依赖多方向聚合结果来避免单射线方向退化，而实际仿真中退化概率极低。

3. **CP + 单射线分解方案与正确性论证**：

   本文将 ENC 查询分解为两个已有批量实现的子查询：

   - **第一步（CP 查询）**：调用 §4.3.2 的批量 CP 方案，找到 $\mathbf{q}$ 的最近面图元 $f^*$ 及其到 $\mathbf{q}$ 的距离 $d^*$。CP 查询的**主要输出**是 $f^*$（prim\_id）——solver 随后通过 prim\_props 表由 prim\_id 解析出所属 enc\_id，这是 ENC 查询最终结果的核心。若 $d^* < \varepsilon_{\text{degen}}$（退化阈值，$10^{-8}$），标记为退化情形（$\text{side} = -1$），跳过第二步。

   - **第二步（射线侧判定）**：从 $\mathbf{q}$ 沿固定方向（本文取 $+X$ 轴）发射一条 RT 批量查询射线，取最近命中面的几何法线 $\mathbf{n}'$（首命中）。**关键**：第二步的输入（射线起点 + 固定方向）在 H2D 上传时就已全部准备好，不依赖第一步的 CP 输出，因此两个 GPU kernel 可在同一 compute\_stream 上**背靠背排队，无需中间同步**；结果合并发生在 CPU 侧 D2H 完成后。

   **正确性（Jordan–Brouwer 分离定理）**：对三维空间中的封闭多面体，从其内部任意点出发沿任意一般方向发射射线，该射线穿越多面体边界奇数次；从外部点出发则穿越偶数次。仅需首命中面的法线方向即可判断穿越方向：
   $$
   \text{side} = \begin{cases}
   0\ (\text{外部}) & \langle \hat{x},\ \mathbf{n}' \rangle < 0\ \text{（射线从外向内穿入）或射线未命中} \\
   1\ (\text{内部}) & \langle \hat{x},\ \mathbf{n}' \rangle > 0\ \text{（射线从内向外穿出）}
   \end{cases}
   $$
   两步职责明确：CP 提供面标识（prim\_id）与退化保护；RT 提供内外侧判定。

4. **从多射线到双查询的代价变化**：Baseline 每次 ENC 查询发射多条射线；本方案每次 ENC 查询等效于 $1 \times \text{CP} + 1 \times \text{RT}$，且两者均批量执行，等效单次代价大幅降低（§4.5 定量）。

**图表需求**：
- 内外判断原理图（+X 射线 + 命中法线方向 → front/back，标注 Jordan–Brouwer 几何直觉）
- ENC 查询执行时序图（H2D 并发上传 CP+RT 两路输入 → CP kernel 入队 → RT kernel 背靠背入队（无中间 sync）→ cudaStreamSynchronize → D2H 双路下载 → CPU 合并 → EnclosureResult）

---

## §4.4 统一查询后端架构

**篇幅**：约 500 字  
**写作思路**：

本节说明三类查询映射在单一 OptiX Pipeline 内的架构整合，重点阐明**整合决策的取舍理由**，而非罗列工程细节。

1. **单 Pipeline 整合的动机**：若将三类查询分别维护为独立 Pipeline，则：各 Pipeline 独立持有加速结构（GAS/IAS），几何数据存在多份冗余；一次 Wavefront 轮次中需多次 Pipeline 上下文切换；ENC 分解的第二步（RT）需消费第一步（CP）产出的最近面信息，独立 Pipeline 间无法共享 GPU 端中间结果，须额外 CPU 往返。以上三项代价均可通过单 Pipeline 整合消除。

2. **SBT 切换机制**：统一 Pipeline 包含两个 PTX 模块（RT 程序 + CP 程序），**四套 SBT**（`m_sbt_rt`、`m_sbt_mh`、`m_sbt_mhf`、`m_sbt_cp`）。每次 `optixLaunch` 切换 SBT 指针而不重建 Pipeline，切换代价仅为一次 CPU 端指针赋值。四套 SBT 的路由关系为：solver 端非 filter RT → `m_sbt_mh`；GPU filter RT（L4）→ `m_sbt_mhf`；solver 端 CP → `m_sbt_cp`；ENC 内部侧判定 RT → `m_sbt_rt`。所有查询的程序路由完全由 SBT 决定，Pipeline 本身不变。

3. **双 GAS 设计**：RT 查询用三角形 GAS（§4.3.1），CP 查询用 AABB 代理 GAS（§4.3.2），两者共享同一份顶点/法线显存，各自构建 BVH。ENC 查询复用二者（第一步 CP batch，第二步 RT batch），无独立加速结构。

4. **接口兼容性说明（一段）**：为使对照实验（Baseline Embree vs Ours OptiX）能通过编译时后端切换实现，`oxstar-3d` 提供与 Embree 后端（`star-3d`）相同签名的 C API（`s3d.h`）。这是**实验有效性**的工程保障，不属于本章方法贡献。

**图表需求**：统一后端架构图（两个 PTX 模块 + 三套 SBT + 双 GAS → 三类查询路由示意）

---

## §4.5 性能评估

**篇幅**：约 800 字 + 图表  
**写作思路**：

### (1) 单类查询吞吐量对比

分别对三类查询（RT / CP / ENC），以不同 batch size（从 1 到 $2^{18}$）测量 Ours（OptiX GPU）vs Baseline（Embree CPU）的吞吐量（单位：MRay/s 或 MQuery/s）：

- **RT 查询**：展示 batch size vs 吞吐量曲线，印证 §4.3.1 的理论预期（小 batch 欠饱和 / 大 batch 趋于峰值），给出典型工作 batch size 下的加速比（须以实测数据填写）。
- **CP 查询**：同样的 batch size vs 吞吐量曲线；自定义求交（SM 执行，非 RT Core）导致峰值吞吐低于 RT，但相比 CPU 逐查询仍有明显加速（须以实测数据填写）。
- **ENC 查询**：每次 ENC 等效 $1\times\text{CP} + 1\times\text{RT}$，计算等效 ENC Query/s；重点展示原首要瓶颈消除后的加速比。

### (2) 端到端性能

配合第三章 Wavefront 调度的总体墙钟时间对比（Baseline 递归求解器 + Embree vs Ours Wavefront求解器 + OptiX）：

- 对比场景：须与第三章一致，以实际仿真场景数据填写。
- 热点分解：报告 solver 状态推进 + RT query + CP query + ENC query 各自时间占比。
- 给出端到端加速比（须以实测数据填写）。

### (3) GPU 利用率分析

- Nsight Systems / Nsight Compute 关键数据：SM 利用率（%）、RT Core 利用率（%）、DRAM 带宽占用。
- Host-Device 传输带宽占总时间的比例（pinned memory 优化效果）。

**图表需求**：
- Batch size vs 吞吐量曲线（RT / CP 两条，印证 §4.3.1 理论）
- 各类查询加速比柱状图（Embree vs OptiX，分 RT / CP / ENC）
- 端到端性能对比表（Baseline vs Ours）

**数据需求**：实测吞吐量数值（不得使用占位数据），须在正式撰写前完成对应实验。

---

## §4.6 小结

**篇幅**：约 300 字  
**写作思路**：

1. **回顾本章贡献**：
   - 设计并实现了基于 OptiX 的统一批量几何查询后端 `oxstar-3d`，在单一 Pipeline 下支持三类异构几何查询（RT / CP / ENC）。
   - 针对 CP 查询（最近面投影），提出基于 OptiX 自定义图元机制的 AABB 代理 + 零长度射线等价重构方案，并给出映射的完备性与正确性论证；该方案无需额外 CPU BVH 库，与 RT 查询共享同一加速结构管理。
   - 针对 ENC 查询（Enclosure 关系判定），提出 CP + 单射线二步分解方案，依据 Jordan–Brouwer 定理证明单次有向射线求交对凸包分解的充分性，相比多射线投票法大幅降低每次查询等效射线数。
   - 对外提供与 Embree 100% 兼容的 s3d C API，实现求解器与光追后端的透明切换，保证对照实验的控制变量有效性。

2. **性能总结**（待实验数据填写具体数值）：
   - RT 查询吞吐量 vs Embree：~XX×；
   - CP 查询吞吐量 vs Embree：~XX×；
   - ENC 查询加速比（端到端，原性能瓶颈）：~XX×；
   - 端到端仿真加速比：~XX×。

3. **与第三章的关系**：第三章在架构层面论证了批量查询的必要性，并将三类查询需求规约为 Wavefront 求解器的接口契约；本章提出并验证了满足该契约的 GPU 高通量实现。二者共同构成完整的 GPU 加速耦合热输运仿真后端。

---

*大纲创建日期：2026-03-20*
