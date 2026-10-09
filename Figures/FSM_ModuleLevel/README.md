# 模块级路径生命周期状态转移图

**文件名**: `FSM_ModuleLevel.pdf` (SVG → PDF)  
**放置位置**: §3.4.1.6 FSM 综合子小节  
**尺寸**: 0.65\textwidth  

## 内容描述

将 RAD、BND、CND、CNV 四个物理模块抽象为粗粒度节点，用概率标注的转移边展示模块间跳转关系，展示路径在耦合热输运过程中的全局流转结构。

### 模块节点

1. **RAD**（辐射传播）：椭圆/圆角矩形，红色调
2. **BND**（界面耦合）：八角形或大圆角矩形，灰色/深色调（枢纽节点）
3. **CND**（固体传导）：椭圆/圆角矩形，蓝色调
4. **CNV**（对流换热）：椭圆/圆角矩形，橙色调

### 转移边

- **Detector → RAD**：路径起始（从探测器发射）
- **RAD → BND**：ε 概率吸收（标注"ε-absorb"）
- **RAD → Done(Escape)**：射线逃逸
- **RAD → Done(RR)**：俄罗斯轮盘赌截断
- **BND → CND**：P_cond 概率（标注"P_cond"）
- **BND → CNV**：P_conv 概率（标注"P_conv"）
- **BND → RAD**：P_rad 概率漫反射（标注"P_rad"）
- **CND → BND**：游走到达边界
- **CNV → BND**：采样位置温度未知
- **CNV → Done(Dissipation)**：温度已知
- **CND → Done(Time)**：时间倒退至 t_I
- **CNV → Done(Time)**：时间倒退至 t_I
- **BND → Done(Known T)**：已知温度边界

### 终止节点

- Done(Escape)、Done(RR)、Done(Time)、Done(Dissipation)、Done(Known T)
- 用双圈或填充矩形表示

### 作图规范

本图遵循 FSM 系列统一作图语言：

| 图元 | 含义 |
|------|------|
| **圆圈节点 ○/◎** | 状态链起止点，转移到/自其他状态机或模块（如 ◎ Detector 起点、◎ Done(*) 终止） |
| **方形节点 □** | 不引入分支的线性状态 |
| **红色边框方形节点** | 含几何查询的挂起点（本图为模块级抽象，不展示挂起点细节） |
| **菱形节点 ◇** | 分支和决策状态（本图中 BND 充当概率分发枢纽） |
| **状态转移箭头 →** | 标注转移条件（概率值 $P_\text{cond}$、$P_\text{conv}$、$P_\text{rad}$ 等） |
| **虚线方框** | 物理或蒙特卡洛子过程分组 |

#### 本图节点映射

| 节点 | 图元类型 | 说明 |
|------|----------|------|
| RAD | 方形（红色调） | 辐射传播模块 |
| BND | 菱形（灰色/深色调，尺寸最大） | 界面耦合枢纽，概率分发 |
| CND | 方形（蓝色调） | 固体传导模块 |
| CNV | 方形（橙色调） | 对流换热模块 |
| ◎ Detector | 圆圈 | 起点：路径从探测器发射 |
| ◎ Done(Escape) | 圆圈 | 终止：射线逃逸 |
| ◎ Done(RR) | 圆圈 | 终止：俄罗斯轮盘赌截断 |
| ◎ Done(Time) | 圆圈 | 终止：时间回溯 |
| ◎ Done(Dissipation) | 圆圈 | 终止：对流耗散 |
| ◎ Done(Known T) | 圆圈 | 终止：已知温度 |

### 图注

- 中文：耦合热输运路径的模块级生命周期示意图。方形节点为物理传输模块（RAD/CND/CNV），菱形为 BND 界面耦合枢纽（按概率 $P_\text{cond}$、$P_\text{conv}$、$P_\text{rad}$ 分发路径），圆圈节点为路径起点与终止条件。
- 英文：Module-level lifecycle diagram of coupled thermal transport paths. Rectangles denote physical transport modules (RAD/CND/CNV); the diamond represents the BND interface coupling hub dispatching paths with probabilities $P_\text{cond}$, $P_\text{conv}$, $P_\text{rad}$; circle nodes mark path origin and termination conditions.
