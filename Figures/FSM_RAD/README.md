# RAD 模块状态转移图

**文件名**: `FSM_RAD.pdf` (SVG → PDF)  
**放置位置**: §3.4.1.2 RAD 子小节末尾  
**尺寸**: 0.5\textwidth  

## 内容描述

RAD（辐射传播）模块的 FSM 状态转移图。RAD 是最简洁的模块，仅 2 个状态。

### 状态节点

1. **RAD_EMIT**（初始状态）：采样余弦方向，构造射线
2. **RAD_BOUNCE**：处理命中结果 → ε 吸收 / (1-ε) 反射

### 转移边

- RAD_EMIT → **[RT 查询]** → RAD_BOUNCE：射线追踪查询
- RAD_BOUNCE → RAD_EMIT：(1-ε) 概率漫反射，回到发射状态
- RAD_BOUNCE → **BND 入口**：ε 概率吸收，转入界面耦合模块
- RAD_BOUNCE → **Done(Escape)**：射线逃逸场景（未命中任何面）
- RAD_BOUNCE → **Done(RR)**：俄罗斯轮盘赌截断

### 作图规范

本图遵循 FSM 系列统一作图语言：

| 图元 | 含义 |
|------|------|
| **圆圈节点 ○/◎** | 状态链起止点，转移到/自其他状态机或模块（如 ◎ BND 入口、◎ Done(Escape)） |
| **方形节点 □** | 不引入分支的线性状态（如 RAD_EMIT） |
| **红色边框方形节点** | 含几何查询的挂起点（Wavefront 挂起/恢复边界） |
| **菱形节点 ◇** | 分支和决策状态（如 RAD_BOUNCE 的 ε/1-ε/Miss 判定） |
| **状态转移箭头 →** | 标注转移条件（概率值、判定结果等） |
| **虚线方框** | 物理或蒙特卡洛子过程分组 |

#### 本图节点映射

| 节点 | 图元类型 | 说明 |
|------|----------|------|
| RAD_EMIT | 红色边框方形 | 含 RT 查询（射线最近命中），挂起点 |
| RAD_BOUNCE | 菱形 | ε-吸收 / (1-ε)-反射 / Miss / RR 四路分支 |
| ◎ BND 入口 | 圆圈 | 转移至 BND 模块 |
| ◎ Done(Escape) | 圆圈 | 终止：射线逃逸 |
| ◎ Done(RR) | 圆圈 | 终止：俄罗斯轮盘赌截断 |
| ◎ 探测器/BND 入口 | 圆圈 | 模块入口 |

### 图注

- 中文：RAD 辐射传播模块的状态转移图。圆圈节点为模块入口/出口及终止条件，红色边框方形为含 RT 查询的挂起点，菱形为分支决策状态。
- 英文：FSM of the RAD radiative transport module. Circle nodes denote module entry/exit points and termination conditions; red-bordered rectangles indicate geometric query suspension points; diamonds represent branching decisions.
