# 硕士学位论文项目指南

**论文题目**: 基于路径追踪的混合架构耦合热输运红外仿真算法  
**英文题目**: Hybrid Architecture Coupled Thermal Transport Path Tracing Infrared Simulation Algorithm  
**作者**: 蒲昱岐  
**培养单位**: 四川大学计算机学院  
**学科方向**: 计算机技术 / 计算机图形学  
**答辩时间**: 二〇二六年五月  

---

## 技术栈

| 技术 | 用途 |
|------|------|
| **LaTeX (XeLaTeX)** | 论文排版 |
| **BibTeX (gbt7714)** | 参考文献管理（国标 GB/T 7714 格式） |
| **latexmk** | 自动化编译 |
| **四川大学 scuthesis2020 模板** | 论文样式 (`./Template/scuthesis2020.cls`) |

---

## 关联项目

本论文围绕两个软件项目展开，各对应独立的代码仓库和 AGENTS.md：

### 1. Stardis-GPU — GPU 加速辐射传输求解器
- **路径**: `D:\Works\Projects\Stardis-GPU`
- **技术栈**: C/C++/CUDA + OptiX
- **核心内容**: 蒙特卡洛耦合热输运求解器，从逐路径递归求解架构迁移到 CPU-GPU 混合 Wavefront 架构
- **论文对应章节**: 第三章（Wavefront 求解器）、第四章（OptiX 光追后端）
- **关键子目录**:
  - `stardis-cpu/` — 原始 CPU 求解器（对照组 / Baseline），含 28 个内部库
  - `stardis-oxs3d-merge-phase/` — Hybrid 架构版本（Ours），含 OptiX 光追后端 + 并行化求解器
  - `guide/` — 迁移指南、架构分析、并行化设计文档

### 2. StardisEditor — 场景编辑器
- **路径**: `D:\Works\PythonProjects\StardisEditor`
- **技术栈**: Python 3 + PyQt5 + VTK
- **核心内容**: 为 Stardis 求解器（仅命令行）提供 GUI 场景编辑、可视化和任务管理能力
- **论文对应章节**: 第五章（GUI 编辑器）
- **关键功能**: 场景文件解析/编辑/写出、STL 3D 渲染、边界条件画笔标注、任务队列调度

---

## 论文结构

```
MainBody.tex                    # 主文件，包含文档设置与章节引用
Chapters/
├── 0_0_Abstract.tex            # 中英文摘要
├── 0_1_Abbreviations.tex       # 缩略词表
├── 0_2_Symbols.tex             # 符号表
├── 1_Introduction.tex          # 第一章：绪论（背景、意义、文献综述、研究方案）
├── 2_Research.tex              # 第二章：理论基础与相关技术
│                               #   - 热输运理论
│                               #   - 蒙特卡洛热输运求解方法
│                               #   - 光线追踪与几何查询加速技术
│                               #   - Wavefront 执行模型
├── 3_ParallelizedSolver.tex    # 第三章：Wavefront 耦合热输运求解器
│                               #   - 原始递归求解框架及其局限性
│                               #   - 耦合热输运求解的状态机抽象
│                               #   - Wavefront 求解器实现（CPU-GPU 混合架构）
│                               #   - 结果与性能评估（物理一致性 + 性能分析）
├── 4_RTBackend.tex             # 第四章：基于 OptiX 的 GPU 硬件光追查询后端
│                               #   - OptiX 查询加速原理（执行模型 + RT Core）
│                               #   - 面向批量查询的 OptiX 后端管线设计
│                               #   - 面向求解器接口设计
│                               #   - 性能分析
├── 5_GUI.tex                   # 第五章：求解任务 GUI 编辑器设计与实现
│                               #   - 设计需求分析
│                               #   - 系统架构设计
│                               #   - 功能模块设计与实现
│                               #   - 用户界面设计
│                               #   - 案例分析
├── 6_Conclusion.tex            # 第六章：结论与展望
├── Achievements.tex            # 在读期间科研成果
├── Thanks.tex                  # 致谢
├── Statement.tex               # 声明
└── CopyrightAuthorization.tex  # 版权授权
```

---

## 章节与项目对应关系

| 章节 | 内容 | 对应项目/目录 |
|------|------|---------------|
| **第一章：绪论** | 背景、意义、文献综述 | — |
| **第二章：理论基础** | 热输运理论、蒙特卡洛方法、光追加速、Wavefront 模型 | — |
| **第三章：Wavefront 求解器** | 递归求解器→状态机→Wavefront 并行化改造 | Stardis-GPU: `stardis-cpu/`（原始递归求解器）→ `stardis-oxs3d-merge-phase/stardis-solver/`（Wavefront） |
| **第四章：OptiX 光追后端** | OptiX 执行模型、批量光追/投影/包壳查询管线 | Stardis-GPU: `stardis-oxs3d-merge-phase/oxstar-3d/` |
| **第五章：GUI 编辑器** | 场景编辑、可视化、任务管理 | StardisEditor: `src/` |
| **第六章：结论** | 总结与展望 | — |

---

## 核心研究内容概要

### 方法论
- **蒙特卡洛耦合热输运**: 基于 Bati 等人的单路径空间框架\[SIGGRAPH 2023\]，在同一路径空间中同时求解辐射、传导、对流耦合传热
- **Wavefront 并行化**: 将原始递归求解框架抽象为细粒度状态机，实现 Wavefront 批处理调度，适配 GPU 并行执行模型
- **GPU 硬件光追加速**: 基于 NVIDIA OptiX + RT Core 实现批量光追查询、最近面投影查询、Enclosure 关系查询
- **CPU-GPU 混合架构**: 状态机调度在 CPU，光追查询批量卸载到 GPU，双流 ping-pong 隐藏传输延迟

### 对照实验设计
- **Baseline（对照组）**: `stardis-cpu/` — 原始 CPU 递归求解器 + Embree 光追
- **Ours（实验组）**: `stardis-oxs3d-merge-phase//` — Wavefront 求解器 + OptiX GPU 光追后端
- **验证标准**: 物理一致性（GPU/CPU 结果逐像素对比，容差 1e-6）+ 性能加速比

---

## 编译命令

```bash
# 使用 latexmk 编译（推荐，自动处理多轮编译和参考文献）
latexmk MainBody.tex

# 使用 compile.bat（Windows）
compile.bat

# 使用 Makefile 编译
make pdf

# 清理临时文件
make clean

# 完全清理（含 PDF）
make cleanall

# 统计字数
make wordcount
```

### 编译环境
- **引擎**: XeLaTeX（通过 latexmk 的 `$pdf_mode = 5` 配置）
- **字体**: 依赖系统中文字体（默认 fandol，可通过 `kfont=windows` 等选项切换）
- **文献格式**: gbt7714 国标数字引用格式（`gbt7714-numerical.bst`）
- **文献数据**: `ReferenceBase.bib`

---

## 查找位置

| 任务 | 位置 |
|------|------|
| **修改论文元信息**（标题、作者、日期等） | `MainBody.tex` 前 50 行 |
| **编辑各章节内容** | `Chapters/*.tex` |
| **管理参考文献** | `ReferenceBase.bib` |
| **调整文档样式/模板** | `./Template/` 子模块 |
| **插入图表** | `Figures/` 目录 |
| **修改编译配置** | `.latexmkrc` |
| **查看文献引用格式** | `gbt7714-numerical.bst`、`gbt7714.sty` |

---

## 写作惯例

- **文件编码**: UTF-8
- **每章独立文件**: 每章一个 `.tex` 文件，通过 `\include{}` 引入
- **文件头声明**: 每个章节文件首行含 `%!TEX root = ../MainBody.tex`
- **引用格式**: 使用 `\cite{}` 命令引用 BibTeX 条目
- **图表引用**: 使用 `\ref{}` 交叉引用
- **中文排版**: 使用 XeLaTeX + ctex 宏包处理中英文混排
- **章节命名**: 文件名前缀数字表示章序（`1_`、`2_`、...），`0_` 前缀为前置部分
- **代码块**: 使用英文作为代码块语言，不含中文，不含全角标点。
- **正文**： 避免使用段内\textbf{}或\emph{}、\textit{}等强调命令。

---

## 注意事项

- 模板来自 [scu_thesis_2020](https://github.com/kevinleeex/scu_thesis_2020)（GPL 协议），`./Template/` 为 git 子模块
- 摘要（`0_0_Abstract.tex`）和部分章节目前仍为模板示例文本，需替换为实际内容
- 缩略词表（`0_1_Abbreviations.tex`）和符号表（`0_2_Symbols.tex`）为占位内容，需补充
- 第六章（结论）目前为模板指导文字，需替换
- `MainBody.pdf` / `MainBody.xdv` 为编译产物，已纳入仓库但随编译更新
- 论文关键词: 红外仿真、路径追踪、蒙特卡洛

---

## Zotero 参考文献集成

论文参考文献存储在 Zotero 中，通过三个通道访问。核心集合为 **EOIR**（Key: `MJF343F7`），含 11 个子集合（用户预分类）。

### 通道概览

| 通道 | 端口 | 用途 | 输出格式 |
|------|------|------|----------|
| **Zotero MCP** | 23120 | 语义搜索、元数据查询、集合浏览 | JSON 元数据 |
| **Zotero 本地 API** | 23119 | 按集合/条目批量导出 BibTeX | BibTeX (原生) |
| **Better BibTeX JSON-RPC** | 23119 | 按 citation key 精确导出 | BibTeX (BBT 格式，**推荐**) |

### 通道 1: Zotero MCP (端口 23120)

MCP 协议工具服务器，通过 JSON-RPC 调用 `tools/call`。适合集合浏览和元数据查询。

```javascript
// 调用方式: POST http://127.0.0.1:23120/mcp
{ "jsonrpc": "2.0", "id": 1, "method": "tools/call",
  "params": { "name": "<tool_name>", "arguments": { ... } } }
```

**常用工具**:
- `search_collections` — 搜索集合（如 `{ q: "EOIR" }`）
- `get_collection_items` — 获取集合下论文列表（如 `{ collectionKey: "MJF343F7", mode: "preview" }`）
- `get_subcollections` — 获取子集合结构（如 `{ collectionKey: "MJF343F7" }`）
- `get_item_details` — 获取单条论文详细元数据（如 `{ itemKey: "KGIZIQ54", mode: "complete" }`）
- `search_library` — 按关键词搜索全库（如 `{ q: "路径追踪", mode: "preview", limit: 10 }`）
- `semantic_search` — AI 语义搜索
- `search_fulltext` — 全文内容搜索

**返回格式**: JSON，含 `data` 数组（title, creators, date, DOI, tags, attachments 等）。

### 通道 2: Zotero 本地 API (端口 23119)

Zotero 内置 HTTP API，支持 `?format=bibtex` 直接导出。适合按集合批量导出。

```bash
# 导出指定集合所有论文的 BibTeX
GET http://127.0.0.1:23119/api/users/0/collections/{collectionKey}/items?format=bibtex

# 按 itemKey 导出单条/多条
GET http://127.0.0.1:23119/api/users/0/items?itemKey={key1},{key2}&format=bibtex

# 获取集合列表 (JSON)
GET http://127.0.0.1:23119/api/users/0/collections

# 获取子集合 (JSON)
GET http://127.0.0.1:23119/api/users/0/collections/{collectionKey}/collections

# 获取集合下论文 (JSON, 排除附件)
GET http://127.0.0.1:23119/api/users/0/collections/{collectionKey}/items?format=json&itemType=-attachment
```

**注意**: 原生导出的中文论文 citation key 质量较差（如 `__2025`），建议仅用于批量获取或使用 BBT 通道。

### 通道 3: Better BibTeX JSON-RPC (端口 23119，推荐)

BBT 插件的 JSON-RPC 接口，导出格式与现有 `ReferenceBase.bib` 风格一致。

```javascript
// 调用方式: POST http://127.0.0.1:23119/better-bibtex/json-rpc
// 按 citation key 导出（key 可从 Zotero 或 MCP 获取后对应）
{ "jsonrpc": "2.0", "id": 1,
  "method": "item.export",
  "params": [["kajiyaRenderingEquation1986", "zhuRTNNAcceleratingNeighbor2022"], "betterbibtex"] }

// 搜索全库条目（返回 CSL-JSON，含 citekey 字段）
{ "jsonrpc": "2.0", "id": 2,
  "method": "item.search",
  "params": [""] }

// HTTP GET 全库导出
GET http://127.0.0.1:23119/better-bibtex/export/library?/1/library.bibtex
```

**重要**: BBT 使用 **citation key**（如 `kajiyaRenderingEquation1986`），而非 Zotero item key（如 `2XPKWNLA`）。

### EOIR 子集合结构

| 子集合 | Key | 篇数 | 论文对应章节 |
|--------|-----|------|-------------|
| 蒙卡热输运方法 | `GLN8YZG3` | 16 | 第二章、第三章 |
| 经验半经验与第一性方法 | `HFGRFYUY` | 28 | 第一章（文献综述：对比方法） |
| 集成系统 | `YDX3ET5E` | 19 | 第一章（系统概览）、第五章 |
| Wavefront | `4DD8IT8H` | 8 | 第三章 |
| 光追实现 | `3YKPYUFJ` | 5 | 第四章 |
| 应用 | `VLXCEIT9` | 5 | 第一章（应用场景） |
| 质量评估 | `W8LNS3M7` | 2 | 第三章（验证） |
| optix | `GKQIN25N` | 1 | 第四章 |
| embree | `ZY524LFB` | 2 | 第三/四章（Baseline） |
| 热输运理论 | `ML2FZRUN` | 0 | 第二章（待补充） |
| 材质处理 | `NJCNBTFL` | 0 | （待补充） |

### 推荐工作流

```
1. MCP get_subcollections → 浏览 EOIR 子集合结构
2. Zotero API /collections/{key}/items?format=json&itemType=-attachment → 获取论文列表
3. BBT item.export(citekeys, 'betterbibtex') → 按 citation key 导出高质量 BibTeX
4. 合并到 ReferenceBase.bib
```

---

*文档创建: 2026-03-11*
