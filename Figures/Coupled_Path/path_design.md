# 嵌套腔体耦合热输运路径示意图设计文档（v3）

**对应图签**: `fig:coupled_path`  
**源文件**: `Figures/CoupledPath.svg`（编译时需导出为 `Figures/CoupledPath.pdf`）  
**对应章节**: 第三章 §3.2（耦合热输运路径追踪算法规约）  
**插入位置**: `3_ParallelizedSolver.tex` §3.2 首段之后、挂起点分析之前  
**创建日期**: 2026-03-23  
**更新**: v3 — 5 区域 / 6 BND / 扇形分支 / 基于实际绘图定稿

---

## 一、嵌套几何场景

### 1.1 拓扑

```
FLUID A  (外部无穷大环境, Enc A: ε_A, h_A, θ_{F,A})
  └── SOLID A  (外壳多边形, λ_A)
        ├── FLUID B  (封闭腔体, Enc B: ε_B, h_B, θ_{F,B})
        └── SOLID B  (内嵌固体, λ_B)
```

Fluid B 与 Solid B **同级**，均被 Solid A 内壁直接包裹。

### 1.2 截面示意

```
┌──────────────────────────────────────────────────────────────┐
│                      FLUID A  (Enc A)                        │
│  Det ──RAD①──▶                                               │
│                    ╔══════════════════════════╗               │
│                    ║       SOLID A  (λ_A)     ║               │
│                    ║  ┌────────────────────┐  ║               │
│                    ║  │   FLUID B (Enc B)  │  ║               │
│                    ║  │   ┌────────────┐   │  ║               │
│                    ║  │   │  SOLID B   │   │  ║               │
│                    ║  │   │   (λ_B)    │   │  ║               │
│                    ║  │   └────────────┘   │  ║               │
│                    ║  └────────────────────┘  ║               │
│                    ╚══════════════════════════╝               │
└──────────────────────────────────────────────────────────────┘
```

### 1.3 界面清单

| 界面 | 类型 | 两侧区域 | ENC 结果 |
|------|------|----------|---------|
| Solid A 外表面 | **SF** | Fluid A ↔ Solid A | Enc A |
| Solid A 内表面 (面向 Fluid B) | **SF** | Solid A ↔ Fluid B | Enc B |
| Solid B 表面 (面向 Fluid B) | **SF** | Fluid B ↔ Solid B | Enc B |
| Solid A ↔ Solid B 接触面 | **SS** | Solid A ↔ Solid B | 跨 Enc |

### 1.4 各区域物理参数

| 区域 | 参数 | 含义 |
|------|------|------|
| Fluid A (Enc A) | $\varepsilon_A,\; h_A,\; \theta_{F,A}$ | 外部发射率、对流系数、流体温度 |
| Solid A | $\lambda_A$ | 外壳导热系数 |
| Fluid B (Enc B) | $\varepsilon_B,\; h_B,\; \theta_{F,B}$ | 腔体发射率、对流系数、流体温度 |
| Solid B | $\lambda_B$ | 内体导热系数 |

---

## 二、耦合情况去重枚举

三种物理过程（RAD / CND / CNV）通过两类界面事件（BND\_SF / BND\_SS）耦合。
**同一种入段→出段转换不论发生在哪条界面上，物理机制相同，仅枚举一次。**

### 2.1 固-流界面 (BND\_SF)：6 种唯一转换

| 编号 | 入段 → 出段 | 描述 | 概率因子 |
|------|------------|------|---------|
| **SF-1** | RAD → CND | 辐射命中固体表面 → $\delta$-重注入渗入固体 | $P_\mathrm{cond}$ |
| **SF-2** | RAD → RAD | 辐射命中固体表面 → 漫反射回同一流体 | $P_\mathrm{rad}$ |
| **SF-3** | RAD → CNV 终止 | 辐射命中 → 对流温度终止 | $P_\mathrm{conv}$ |
| **SF-4** | CND → RAD | 传导游走到达壁面 → 辐射再发射进入流体 | $P_\mathrm{rad}$ |
| **SF-5** | CND → CND | 传导到达壁面 → $\delta$-重注入返回同一固体 | $P_\mathrm{cond}$ |
| **SF-6** | CND → CNV 终止 | 传导到达壁面 → 对流温度终止 | $P_\mathrm{conv}$ |

> - SF-1 / SF-4 互为方向对偶（流体→固体 vs 固体→流体）
> - SF-2 / SF-5 均为"留在当前介质"，属路径未切换机制的平凡分支
> - SF-3 / SF-6 均为对流终止
> - null-collision 循环嵌套在 $P_\mathrm{rad}$ 分支内部，是 SF-2/SF-4 的实现细节

### 2.2 固-固界面 (BND\_SS)：1 种唯一转换

| 编号 | 入段 → 出段 | 描述 | 概率因子 |
|------|------------|------|---------|
| **SS-1** | CND → CND (跨固体) | 传导到达固-固接触面 → 按 $k/\delta$ 比选择注入侧 | $P_{\mathrm{cond},1}$ vs $P_{\mathrm{cond},2}$ |

> 二元概率：$P_{\mathrm{cond},A} = \frac{\lambda_A/\delta_A}{\lambda_A/\delta_A + \lambda_B/\delta_B}$

### 2.3 终止条件：4 种

| 编号 | 情形 | 描述 |
|------|------|------|
| **T1** | RAD miss | 辐射逃逸至无穷远 → 环境温度 $\theta_\mathrm{amb}$ |
| **T2** | Dirichlet BC | 界面温度已知 → 直接读值终止 |
| **T3** | 俄罗斯轮盘赌 | 路径权重过低 → 概率截断（无偏） |
| **T4** | 时间回溯 | 瞬态模式 $t \leq t_I$ → 读取初始温度场 |

### 2.4 四类核心耦合模式

从 7 种唯一转换中提炼示意图必须各展示一次的核心模式：

| 模式 | 转换 | 关键特征 | 图中对应 |
|------|------|----------|---------|
| **I. 跨介质渗透** | SF-1 | RAD → BND\_SF → CND，辐射穿入固体 | BND① |
| **II. 固-固跨壁传导** | SS-1 | CND → BND\_SS → CND，两固体直接导热耦合 | BND② |
| **III. 边界再发射** | SF-4 | CND → BND\_SF → RAD，传导到达壁面后辐射发射回流体（**跨 Enc**） | BND③ |
| **IV. 对流终止** | SF-3/SF-6 | → BND\_SF → CNV，任何入段均可终止为对流 | BND④ |

> SF-2（漫反射）和 SF-5（重注入）为"留在当前介质"的平凡分支，图中以虚线副分支标注。

---

## 三、主路径设计

### 3.1 主干路径

一笔贯穿全部四种介质，4 个 BND 各展示一种核心模式：

```
Det ───RAD①───▶ Solid A 外表面
                    │ BND①  [模式 I: 跨介质渗透]
                    │ ENC → Enc A;  SF-1: RAD → CND
                    │ P_cond: δ-重注入进入 Solid A
                    ▼
               CND① (Solid A 内, Walk-on-δ-Sphere, 2步)
                    │ x₀ → x₁ → x₂, 游走至 Solid A ↔ Solid B 接触面
                    ▼
               Solid A ↔ Solid B 接触面
                    │ BND②  [模式 II: 固-固跨壁传导]
                    │ SS-1: CND(A) → CND(B), 按 λ/δ 比选侧
                    │ P_{cond,B}: 注入 Solid B 侧
                    ▼
               CND② (Solid B 内, Walk-on-δ-Sphere, 2步)
                    │ y₀ → y₁ → y₂, 游走至 Solid B 面向 Fluid B 的表面
                    ▼
               Solid B 表面 (面向 Fluid B)
                    │ BND③  [模式 III: 边界再发射]
                    │ ENC → Enc B;  SF-4: CND → RAD
                    │ P_rad: 再发射进入 Fluid B
                    ▼
          ───RAD②───▶ Solid A 内表面 (面向 Fluid B)
                    │ BND④  [模式 IV: 对流终止]
                    │ ENC → Enc B;  SF-6: CND/RAD → CNV
                    │ P_conv: 对流温度终止
                    ▼
                CNV: θ_{F,B}  ← 路径终止
```

### 3.2 各 BND 副分支（虚线绘制）

| BND | 副分支 | 绘法 |
|-----|--------|------|
| BND① | SF-2: $P_\mathrm{rad}$ 漫反射回 Fluid A | 蓝色虚线，左上折返 |
| BND① | SF-3: $P_\mathrm{conv}$ 对流终止 $\theta_{F,A}$ | 红色短箭头↓ |
| BND② | SS-1 反向: $P_{\mathrm{cond},A}$ 注入回 Solid A 侧 | 橙色虚线，折返 |
| BND③ | SF-5: $P_\mathrm{cond}$ 重注入回 Solid B | 橙色虚线短箭头 |
| BND③ | SF-6: $P_\mathrm{conv}$ 对流终止 $\theta_{F,B}$ | 红色短箭头↓ |
| BND④ | SF-1: $P_\mathrm{cond}$ 渗入 Solid A | 橙色虚线短箭头 |
| BND④ | SF-2: $P_\mathrm{rad}$ 反射回 Fluid B（腔体弹射弧） | 蓝色点线弧 |

---

## 四、路径节点详表

| 节点 | 位置 | 事件 | 物理机制 | 几何查询 |
|------|------|------|----------|---------|
| **①** Det | Fluid A 左上 | 路径起点，反向发射 | 初始方向采样 | — |
| **②** | Fluid A → Solid A 外表面 | RAD① 辐射传播 | 透明介质直线传播 | **RT** |
| **③** BND① | Solid A 外表面 | 模式 I: 跨介质渗透 | ENC→Enc A; $(P_\mathrm{cond}, P_\mathrm{rad}, P_\mathrm{conv})$ | **ENC**, **RT×2** |
| **④** $\mathbf{x}_0$ | Solid A 内 | $\delta$-重注入起点 | CND① 启动 | — |
| **⑤** $\mathbf{x}_1, \mathbf{x}_2$ | Solid A 内 | WoδS 步进 | 双向射线+ENC验证 | **RT×2**, **ENC** (×2步) |
| **⑥** BND② | Solid A ↔ Solid B 接触面 | 模式 II: 固-固跨壁传导 | 读取 $\lambda_A,\lambda_B$; 按 $\lambda/\delta$ 比选侧 | **RT×4**, **ENC** |
| **⑦** $\mathbf{y}_0$ | Solid B 内 | 注入起点 | CND② 启动 | — |
| **⑧** $\mathbf{y}_1, \mathbf{y}_2$ | Solid B 内 | WoδS 步进, $\delta$-壳吸附 | 双向射线+ENC验证 | **RT×2**, **ENC** (×2步) |
| **⑨** BND③ | Solid B 表面 → Fluid B | 模式 III: 边界再发射 | ENC→Enc B; 三模态→$P_\mathrm{rad}$ | **ENC**, **RT×2** |
| **⑩** | Fluid B → Solid A 内表面 | RAD② 辐射传播 | 封闭腔体内 | **RT** |
| **⑪** BND④ | Solid A 内表面 (Fluid B 侧) | 模式 IV: 对流终止 | ENC→Enc B; →CNV | **ENC**, **RT×2** |
| **⑫** | (逻辑终止) | CNV: $\theta_{F,B}$ | 路径估计量返回 | — |

---

## 五、论文引图段落（基于实际绘制图的正文描述）

> **用途**：论文正文中引用 `fig:coupled_path` 时的配图说明段落。
> 基于实际绘制的 v3 版：5 区域 / 6 个 BND / 4 种终止 / 扇形分支结构。

---

图~\ref{fig:coupled\_path} 以一个多层嵌套场景为例，展示单一路径空间耦合热输运框架中蒙特卡洛路径的完整传播过程。图中场景为二维截面视图：外部开放环境 Fluid~A（白色背景）中放置一个不规则多边形外壳 Solid~A（$\lambda_A$，橙色填充），Solid~A 内部包含两个互不重叠的子区域——封闭流体腔 Fluid~B（$h_B$，蓝色填充）和内嵌固体 Solid~B（$\lambda_B$，绿色填充），Solid~B 内部进一步嵌套已知温度固体 Solid~C（浅黄色填充）。五个区域各自携带独立的物理参数集合。

路径自图左上方的探测器 Det 出发，以实线表示辐射传播段（RAD），斜向穿越 Fluid~A 后命中 Solid~A 外表面，触发\textbf{界面事件 BND~1}（Fluid~A → Solid~A）——\textbf{模式~I：跨介质渗透}（RAD → CND）。路径以 $P_\mathrm{cond}$ 概率经 $\delta$-重注入渗入 Solid~A 内部，启动传导随机游走（CND），以 Walk-on-$\delta$-Sphere 折线在 Solid~A 壁体中步进。

Solid~A 壁体中的传导随机游走构成图的中心枢纽。由于 Solid~A 外接 Fluid~A、内含 Fluid~B 和 Solid~B 三个不同毗邻区域，游走过程中的 $\delta$-球面吸附步可命中三种不同性质的界面，形成三条出射分支，各展示一种核心耦合模式：

\textbf{出射分支一}——CND 游走步到达 Solid~A 外表面，触发\textbf{BND~4}（Solid~A → Fluid~A）。此为固-流界面，概率分支中 $P_\mathrm{rad}$ 产生辐射反弹 RAD(Bounce)，以虚线射回 Fluid~A；若辐射射线未命中任何几何体则终止为 Done(Miss)，贡献环境温度 $\theta_\mathrm{amb}$。$P_\mathrm{conv}$ 分支则直接以对流耗散终止 Done(Dissipation)，贡献流体温度 $\theta_{F,A}$——\textbf{模式~IV：对流终止}。

\textbf{出射分支二}——CND 游走步到达 Solid~A 内壁面向 Fluid~B 的表面，触发\textbf{BND~2}（Solid~A → Fluid~B）——\textbf{模式~III：边界再发射}（CND → RAD）。路径以 $P_\mathrm{rad}$ 概率再发射进入封闭腔体，虚线标注 RAD(Re-emission) 斜穿 Fluid~B，命中对面 Solid~A 内壁面触发\textbf{BND~3}（Fluid~B → Solid~A），路径可在此终止为 Done(Time)（时间回溯终止，$t \leq t_I$ 时贡献初始温度场）。

\textbf{出射分支三}——CND 游走步到达 Solid~A 与 Solid~B 的直接接触面，触发\textbf{BND~5}（Solid~A → Solid~B）——\textbf{模式~II：固-固跨壁传导}（CND → CND）。此处为固-固界面，无辐射/对流模态，仅按两侧导热系数与步长之比 $\lambda/\delta$ 分配注入概率。路径进入 Solid~B 后继续传导游走，到达 Solid~B ↔ Solid~C 接触面触发\textbf{BND~6}（Solid~B → Solid~C）——再次遇到固-固界面——随后路径终止于 Solid~C 的已知温度条件 Done(Known Temperature)。

整幅图的视觉重心为 Solid~A 壁体内的传导游走过程：一条路径在固体中步进时可随机到达外壁、内壁或接触面，三种不同边界类型触发截然不同的耦合机制。同时图中展示了全部四种终止条件：辐射逃逸（Miss）、对流耗散（Dissipation）、时间回溯（Time）与已知温度（Known Temperature），完整呈现了单路径空间框架下辐射、传导与对流三种传热机制以概率分支统一拼接的特征。

---

## 六、图注文本

### 简版（推荐）

```latex
\caption{
  多层嵌套场景耦合热输运蒙特卡洛路径示意图。
  场景为二维截面：外部环境~Fluid~A 中放置固体外壳~Solid~A（$\lambda_A$，橙色），
  其内部包含封闭流体腔~Fluid~B（蓝色）和内嵌固体~Solid~B（$\lambda_B$，绿色），
  Solid~B 内进一步嵌套已知温度固体~Solid~C（浅黄色）。
  路径自探测器出发经辐射传播（RAD）命中 Solid~A 外表面（BND~1），
  渗透进入固体后执行传导随机游走（CND）。
  游走过程中的 $\delta$-球面吸附步可命中三类界面，分别展示：
  反射/对流出射至外部环境（BND~4）、
  再发射穿越封闭腔体（BND~2 $\to$ BND~3）、
  固-固跨壁传导进入相邻固体（BND~5 $\to$ BND~6）。
  图中同时展示全部四种终止条件：
  辐射逃逸（Miss）、对流耗散（Dissipation）、时间回溯（Time）和已知温度（Known Temperature）。
}
\label{fig:coupled_path}
```

### 详版

```latex
\caption{
  多层嵌套场景耦合热输运单路径空间蒙特卡洛路径传播示意图。
  场景为二维截面：外部环境~Fluid~A（白色）中放置不规则多边形固体外壳~Solid~A
  （$\lambda_A$，橙色），其内部包含封闭流体腔体~Fluid~B（$h_B$，蓝色）和
  内嵌固体~Solid~B（$\lambda_B$，绿色），Solid~B 内进一步嵌套已知温度固体~Solid~C（浅黄色）。
  %
  路径自探测器出发作辐射传播 RAD（实线），命中 Solid~A 外表面触发
  BND~1（Fluid~A $\to$ Solid~A，模式~I：跨介质渗透），
  以~$P_\mathrm{cond}$ 渗入固体启动 Walk-on-$\delta$-Sphere 传导随机游走 CND（折线），
  后续游走步命中不同界面形成三条出射分支：
  % 分支一
  （a）到达外表面触发 BND~4（Solid~A $\to$ Fluid~A），
  $P_\mathrm{rad}$ 辐射反弹 RAD(Bounce)（虚线）逃逸后终止为 Done(Miss)，
  $P_\mathrm{conv}$ 以对流耗散终止为 Done(Dissipation)（模式~IV）；
  % 分支二
  （b）到达面向 Fluid~B 的内壁面触发 BND~2（Solid~A $\to$ Fluid~B，模式~III：边界再发射），
  $P_\mathrm{rad}$ 再发射 RAD(Re-emission)（虚线）穿越封闭腔体，
  命中对侧壁面触发 BND~3（Fluid~B $\to$ Solid~A），终止为 Done(Time)；
  % 分支三
  （c）到达 Solid~A $\leftrightarrow$ Solid~B 接触面触发 BND~5（模式~II：固-固跨壁传导），
  按~$\lambda/\delta$ 比注入 Solid~B，继续 CND 至 BND~6（Solid~B $\to$ Solid~C），
  终止于已知温度 Done(Known Temperature)。
  %
  路径权重沿各分支逐事件递推，形成对探测辐亮度的无偏蒙特卡洛估计。
}
\label{fig:coupled_path}
```

---

## 七、绘图配色与视觉规范（基于实际绘图）

### 区域填充

| 区域 | 实际颜色 | 近似 TikZ |
|------|---------|----------|
| Fluid A | 白色（画布底色） | `white` |
| Solid A | 橙色/鲑鱼色 | `orange!30` |
| Fluid B | 天蓝色 | `cyan!40` |
| Solid B | 绿色 | `green!40` |
| Solid C | 浅黄/米色 | `yellow!25` |

### 路径线型

| 元素 | 颜色 | 线型 |
|------|------|------|
| RAD（入射） | 黑色 | 实线箭头 |
| RAD(Bounce) | 黑色 | 虚线箭头 |
| RAD(Re-emission) | 黑色 | 虚线箭头 |
| CND(delta-sphere) | 黑色 | 折线 + 箭头 |
| CNV | 黑色 | 虚线短箭头 |
| 终止标记 | 黑色 | ✱ 符号 |

---

## 八、路径结构总览（基于实际绘图）

6 个 BND + 5 个区域 + 4 种终止，扇形分支结构：

```
Det ──RAD(实线)──→ ●BND 1 (fluid A → solid A)  [模式 I: RAD→CND]
                        │ P_cond
                   CND (Walk-on-δ-Sphere 折线) in Solid A
                        │
           ┌────────────┼────────────────┐
           │            │                │
       ●BND 4       ●BND 2           ●BND 5
    (A → fluid A) (A → fluid B)    (A → solid B)  [模式 II: SS]
           │            │                │
     ┌─────┤      RAD(Re-em.)      CND in Solid B
     │     │      (虚线穿Fluid B)        │
 RAD(Bounce) CNV        │            ●BND 6
  (虚线)    │       ●BND 3         (B → solid C) [模式 II]
     │    Done     (B → solid A)        │
  Done   (Dissip.)      │            Done
  (Miss)  [模式IV]    Done(Time)   (Known Temp.)
```

> 核心视觉概念：Solid A 壁体中的 CND 游走是中心枢纽，
> 三个不同方向的 δ-球面吸附步分别命中外壁 / 内壁 / 接触面，
> 触发三种截然不同的后续物理过程。

CND 段保留若干步随机跳跃折线即可说明 Walk-on-$\delta$-Sphere。

---

## 九、LLM 绘图指令（精简版，基于实际绘图定稿）

> **目的**：以最低歧义描述已定稿图的结构，便于填色/精修/重绘时参考。

---

### 9.1 几何层（由外到内画，5 个区域）

1. **画布背景** = 白色，代表 Fluid A (Environment)。
2. **Solid A** = 不规则多边形，橙色 (`orange!30`) 填充，黑色轮廓。占画布中央约 60% 面积。
3. **Fluid B** = Solid A 内部偏左下的不规则多边形空腔，天蓝色 (`cyan!40`) 填充。标注 "encapsuled cavity"。
4. **Solid B** = Solid A 内部偏右的不规则多边形，绿色 (`green!40`) 填充，黑色轮廓。
5. **Solid C** = Solid B 内部的小多边形，浅黄色 (`yellow!25`) 填充，黑色轮廓。

**区域标签**（各区域中心）：

| 位置 | 标签 |
|------|------|
| 画布左侧空白 | Fluid A (Environment) |
| Solid A 上半 | Solid A |
| Fluid B 中心 | Fluid B (encapsuled cavity) |
| Solid B 右侧 | Solid B |
| Solid C 中心 | Solid C |

### 9.2 路径与箭头（按实际图关系）

#### 入射段
| 起点 | 终点 | 线型 | 标签 |
|------|------|------|------|
| Det (左上角相机图标) | Solid A 外表面左侧 (BND 1) | **实线箭头** | RAD |

#### CND 游走段（Solid A 内）
BND 1 进入后，CND(delta-sphere) 折线在 Solid A 壁体中随机游走（多步箭头折线），分三个方向出射。标注 `CND` 两次（两段明显折线段旁各标一次）。

#### 三条出射分支

**分支 A → 外部 (BND 4, solid A → fluid A)**：
| 元素 | 线型 | 终点 |
|------|------|------|
| BND 4 标注 | solid A → fluid A | — |
| RAD(Bounce) | 虚线箭头，向左上 | Done(Miss) ✱ |
| CNV | 虚线短箭头，向上 | Done(Dissipation) ✱ |

**分支 B → 腔体 (BND 2 → BND 3)**：
| 元素 | 线型 | 终点 |
|------|------|------|
| BND 2 标注 | solid A → fluid B | — |
| RAD(Re-emission) | 虚线箭头，斜穿 Fluid B 蓝色区 | BND 3 (fluid B → solid A) |
| BND 3 后 | 虚线短箭头 | Done(Time) ✱ |

**分支 C → 相邻固体 (BND 5 → BND 6)**：
| 元素 | 线型 | 终点 |
|------|------|------|
| BND 5 标注 | solid A → solid B | — |
| CND in Solid B | 短折线 | BND 6 (solid B → solid C) |
| BND 6 后 | — | Done(Known Temperature) |

### 9.3 BND 标记点（6 个）

| BND | 位置 | 界面类型 | 旁标签 |
|-----|------|---------|--------|
| BND 1 | Solid A 外表面左侧 | SF | `BND 1 fluid A -> solid A` |
| BND 2 | Solid A 内壁面向 Fluid B | SF | `BND 2 solid A -> fluid B` |
| BND 3 | Fluid B 对面 Solid A 内壁 | SF | `BND 3 fluid B -> solid A` |
| BND 4 | Solid A 外壁右上 | SF | `BND 4 solid A -> fluid A` |
| BND 5 | Solid A ↔ Solid B 接触面 | SS | `BND 5 solid A -> solid B` |
| BND 6 | Solid B ↔ Solid C 接触面 | SS | `BND 6 solid B -> solid C` |

### 9.4 终止标记（4 种，各用 ✱ 符号 + 文字）

| 标记 | 位置 | 文字 |
|------|------|------|
| ✱ | RAD(Bounce) 末端（左上方） | Done(Miss) |
| ✱ | CNV 末端（上方） | Done(Dissipation) |
| ✱ | BND 3 后（下方） | Done(Time) |
| — | Solid C 内部 | Done (Known Temperature) |

### 9.5 图内文字汇总

| 类别 | 文字 |
|------|------|
| 区域名 | Fluid A (Environment), Solid A, Fluid B (encapsuled cavity), Solid B, Solid C |
| 过程标签 | RAD, CND (×2), CND(delta-sphere), RAD(Bounce), RAD(Re-emission), CNV |
| BND 标签 | BND 1–6 各带界面方向说明 |
| 终止 | Done(Miss), Done(Dissipation), Done(Time), Done(Known Temperature) |
