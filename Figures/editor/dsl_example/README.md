# 图：stardis-input DSL 场景文件示例与文法产生式对应关系

## 图注

- **中文**：`stardis-input` DSL 场景文件示例与文法产生式对应关系
- **英文**：Example `stardis-input` DSL scene file with grammar production annotations
- **标签**：`fig:gui:dsl-example`
- **位置**：§5.2.1 文法概述末尾
- **当前占位**：`Figures/demo.png`，宽度 `0.85\textwidth`

## 设计意图

展示一个典型 `stardis-input` 场景文件的**完整文本**，同时用标注箭头/括号将每一行（或每组行）与 BNF 文法产生式对应起来，让读者直观看到"文本 ↔ 文法"的映射。

## 正文引用语境

> 图~\ref{fig:gui:dsl-example} 给出一个典型 `stardis-input` 场景文件示例，展示了介质体、边界条件和连接的完整声明结构。

## 建议内容

### 主体：一段完整的 stardis-input 场景文本（等宽字体）

```text
# 全局缩放
SCALE 0.001

# 背景辐射温度
TRAD 293.15

# 固体介质体
SOLID body0 1.5 2700.0 900.0 AUTO 300.0 UNKNOWN 0.0 BOTH body0.stl

# 流体介质体
FLUID air0 293.15

# Robin 型边界条件（对流 + 辐射）
H_BOUNDARY_FOR_SOLID hbc0 293.15 0.9 1.0 10.0 293.15 body0_top.stl

# Dirichlet 型边界条件（固定温度）
T_BOUNDARY_FOR_SOLID tbc0 350.0 body0_bottom.stl

# 固-流连接
SOLID_FLUID_CONNECTION conn0 body0 air0 body0_inner.stl
```

### 标注（右侧或括号连线）

对每行/每组行标注其对应的 BNF 产生式类别：

| 行 | 对应产生式 |
|----|-----------|
| `SCALE 0.001` | `⟨scaling⟩` |
| `TRAD 293.15` | `⟨rad-env⟩` |
| `SOLID body0 ...` | `⟨solid-const⟩ ∈ ⟨medium⟩` |
| `FLUID air0 293.15` | `⟨fluid⟩ ∈ ⟨medium⟩` |
| `H_BOUNDARY_FOR_SOLID hbc0 ...` | `⟨robin-solid-const⟩ ∈ ⟨boundary-condition⟩` |
| `T_BOUNDARY_FOR_SOLID tbc0 ...` | `⟨dirichlet-solid⟩ ∈ ⟨boundary-condition⟩` |
| `SOLID_FLUID_CONNECTION conn0 ...` | `⟨solid-fluid-connection⟩ ∈ ⟨connection⟩` |
| `# ...` | `⟨comment⟩` |

### SOLID 行参数展开标注（可选细节层）

对 `SOLID body0 1.5 2700.0 900.0 AUTO 300.0 UNKNOWN 0.0 BOTH body0.stl` 这一行做位置参数标注：

```
SOLID  body0  1.5   2700.0  900.0  AUTO  300.0  UNKNOWN  0.0   BOTH  body0.stl
  ↑     ↑      ↑      ↑      ↑      ↑      ↑      ↑       ↑      ↑      ↑
关键字 名称    λ      ρ     c_p    δ    T_init T_imposed P_vol  side  STL路径
```

## 相关 BNF 产生式（论文原文）

顶层结构：
```
⟨thermal-system⟩ ::= ⟨description-line⟩...
```

描述行：
```
⟨description-line⟩ ::= ⟨medium⟩ | ⟨connection⟩ | ⟨boundary-condition⟩
                      | ⟨scaling⟩ | ⟨program⟩ | ⟨comment⟩
```

固体介质：
```
⟨solid-const⟩ ::= SOLID ⟨medium-name⟩ ⟨λ⟩ ⟨ρ⟩ ⟨c_p⟩
                   ⟨δ⟩ ⟨T_init⟩ ⟨T_imposed⟩ ⟨P_vol⟩
                   ⟨triangle-sides⟩...
```

Robin 型边界条件：
```
⟨robin-solid-const⟩ ::= H_BOUNDARY_FOR_SOLID ⟨bound-name⟩
                         ⟨T_ref⟩ ⟨ε⟩ ⟨f_s⟩ ⟨h_c⟩ ⟨T_env⟩ ⟨triangles⟩...
```

## 制图建议

- 建议用代码框 + 右侧括号标注的形式（类似教科书代码解析图）
- 可用 TikZ `listings` + `tikzmark` 或直接绘制为 SVG/PDF
- 注释行（`#`）用灰色，关键字用粗体，参数值正常色
- 右侧标注使用与正文 BNF 公式一致的数学字体
