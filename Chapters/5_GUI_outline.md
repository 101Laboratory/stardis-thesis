# 第五章写作思路汇总

**章节标题**：热输运场景仿真任务 GUI 编辑器设计与实现  
**文件**：`5_GUI.tex`

---

## 全章概要

本章是论文工程应用贡献。逻辑主线：  
**痛点诊断**（Stardis 仅命令行接口）→ **需求分析**（功能 / 非功能 / 用例）→ **架构设计**（Model-View 分层）→ **模块实现**（解析/渲染/画笔/树面板/任务引擎）→ **应用案例**（仿真场景功能演示）

| 节 | 内容 | 承接关系 |
|----|------|---------|
| §5.1 引言 | 使用痛点 + 本章目标 + 章节导读 | 接第三章求解器功能验证 |
| §5.2 设计需求分析 | 功能/非功能需求 + 用例分析 | 为 §5.3 架构设计提供约束 |
| §5.3 系统架构设计 | Model-View 架构 + 模块划分 + 数据流 | 为 §5.4 各模块提供框架 |
| §5.4 功能模块设计与实现 | 五大功能模块详述 | 本章核心技术内容 |
| §5.5 用户界面设计 | 整体布局 + 交互设计原则 | §5.4 的可视化呈现 |
| §5.6 应用案例 | 两个仿真场景的功能演示与输出 | 验证各模块协同运作 |
| §5.7 小结 | 总结 + 承上启下 | 接第六章结论 |

**对应项目代码**：

| 角色 | 路径 | 技术栈 |
|------|------|--------|
| v1 控制面板（对照/历史参考） | `src/StardisControlPanel.py`、`src/main.py` | PyQt5 |
| v2 Scene Editor（本文贡献） | `src/scene_editor.py`、`src/models/`、`src/parsers/`、`src/panels/`、`src/viewport/`、`src/task_runner/` | Python 3 + PyQt5 + VTK |

---

> ⚠️ **撰写前必读源码**：本章各节的枚举项、参数列表、数据类字段均为**概念性骨架**，实际实现细节以源码为准。**撰写各节前，必须先阅读对应源文件**，确认接口名称、参数名称、枚举值与实际代码一致，不得凭印象描述。本大纲提供的是**写作框架和分析方法**。
> - **§5.2 需求分析**：需求来源于 `design/StardisEditor_v2_Requirements.md`（完整规格）及 `AGENTS.md`，须以设计文档为准。
> - **§5.3 架构设计**、**§5.4 模块实现**：须通读 `src/models/`、`src/parsers/`、`src/panels/`、`src/viewport/`、`src/task_runner/` 各文件，以实际类名、方法名、信号名为准。
> - **§5.5 界面设计**：须结合程序截图撰写，不得凭文字臆测界面布局。
> - **§5.6 案例分析**：须以实际操作截图/录屏为依据，数据以真实仿真运行结果为准。

---

## §5.1 引言

**篇幅**：约 500 字  
**写作思路**：

1. **衔接第三、四章**：经过前两章的工作，Stardis 求解器已具备 Wavefront 并行化和 OptiX GPU 硬件光追加速能力，在算法与性能上达到论文预期目标。然而求解器本身仅提供命令行接口，场景配置、几何管理、任务执行均需手动操作，存在若干工程使用痛点。

2. **使用痛点（五个方面，对应 §5.2 的功能需求）**：
   - (a) **场景文件手工编辑**：`.txt` 关键字驱动格式（SOLID/FLUID/T_BOUNDARY/H_BOUNDARY 等）可读性差，参数项繁多（固体介质含 8 个字段），手动编辑极易出错、调试困难。
   - (b) **几何缺乏可视化预览**：STL 几何体无法在配置阶段预览，边界条件与表面区域的空间分布完全凭文本内容推断，几何错误只能在仿真运行后才能发现。
   - (c) **边界条件与表面手工对应**：每条边界条件需手动指定对应的 STL 文件或表面区域；复杂场景（如城市建筑热分析）中，批量标注数十个表面区域的边界条件效率极低。
   - (d) **仿真任务参数组装繁琐**：Stardis CLI 参数达数十项（`-M/-V/-R/-p/-P/-t/-F/-s/-S` 等），多任务批量执行需手动拼接命令，缺乏参数合法性验证和标准化模板管理。
   - (e) **多任务批量执行缺乏自动化**：多组参数实验（如多帧时序渲染、探针+场渲染组合）需顺序执行，手动监控进度、处理中断和错误恢复代价高。

3. **本章目标**：设计并实现 GUI 场景编辑器，提供场景文件可视化编辑、3D 几何预览、交互式画笔标注、任务队列调度等能力，显著降低求解器使用门槛。

4. **章节组织**：§5.2 分析功能与非功能需求；§5.3 提出系统架构设计；§5.4 详述五大功能模块的设计与实现；§5.5 介绍用户界面设计；§5.6 通过案例展示完整工作流；§5.7 总结。

---

## §5.2 设计需求分析

**篇幅**：约 800 字  
**写作思路**：

本节为软件工程标准三段式：功能需求 → 非功能需求 → 用户角色/用例，为后续架构设计提供约束依据。

---

### (1) 功能需求

以"FR-N"编号，与后续架构模块一一对应：

| 编号 | 功能需求 | 对应模块（§5.4 子节） |
|------|---------|---------------------|
| FR-1 | 场景文件解析与写出：解析 `.txt` 到内存模型，修改后回写并保留注释 | §5.4.1 |
| FR-2 | 3D 场景可视化：加载 STL、支持旋转/平移/缩放、法线可视化 | §5.4.2 |
| FR-3 | 边界条件编辑：通过属性面板配置温度/对流/热流/组合边界条件，实时参数验证 | §5.4.4 |
| FR-4 | 表面区域画笔标注：在 3D 视口以画笔/橡皮擦工具标注网格单元的边界区域归属，支持撤销/重做 | §5.4.3 |
| FR-5 | 任务配置与执行：配置 Stardis/HTPP 任务参数，队列调度，QProcess 子进程管理，错误处理 | §5.4.5 |
| FR-6 | 场景树浏览：层级化展示 Body → SurfaceZone → BC，支持右键快捷操作 | §5.4.4 |
| FR-7 | 工程文件管理：`.stardis_project.json` 持久化场景模型与任务队列，最近工程、偏好设置 | §5.3 |
| FR-8 | 场景有效性验证：调用 `stardis -d` 执行几何与属性一致性检查，结果展示在日志面板 | §5.4.5 |

**证据来源**：`design/StardisEditor_v2_Requirements.md` §1–§2，`AGENTS.md` TaskRunner 章节。

---

### (2) 非功能需求

| 编号 | 非功能需求 | 设计响应 |
|------|-----------|---------|
| NFR-1 | 跨平台兼容 | Python 3 + PyQt5 + VTK，纯 Python 依赖，Windows/Linux/macOS 均可运行 |
| NFR-2 | 3D 视口响应性流畅 | VTK GPU 渲染管线；画笔模式下 `vtkHardwareSelector` 单元拾取 |
| NFR-3 | 可扩展性 | 模块化 Model-View 架构；PropertyPanel 使用 `QStackedWidget` 动态切换，新 BC 类型只需添加子编辑器 |
| NFR-4 | 数据一致性 | PyQt5 信号/槽机制确保 SceneModel 更新后 SceneTree / SceneViewport / PropertyPanel 同步刷新 |
| NFR-5 | 版本兼容 | v2 首次启动自动从 v1 `user_settings.json` 迁移设置（`EditorPreferences.migrate_from_v1()`） |

---

### (3) 用户角色与典型用例

**用户角色**：仿真工程师（配置场景 → 设置参数 → 运行仿真 → 查看结果）

典型用例链（对应 §5.6 案例分析）：

```
打开/新建工程
  → 导入/编辑场景文件 (.txt + STL)
  → 3D 预览几何 → 画笔标注边界区域
  → 编辑边界条件参数 → 验证场景 (stardis -d)
  → 配置仿真任务 (探针/IR 渲染/HTPP)
  → 一键执行任务队列 → 查看日志与结果
  → 保存工程 (.stardis_project.json)
```

**[图表需求]** 用例图（Use Case Diagram），覆盖 FR-1 ~ FR-8。

---

## §5.3 系统架构设计

**篇幅**：约 1200 字  
**写作思路**：

本节阐明系统整体设计，重点回答：**为何选型 Model-View + 信号/槽**（而非直接耦合展示与数据），模块如何划分，数据如何流动。

---

### (1) 架构选型：Model-View + 信号/槽解耦

**问题**：3D 视口（VTK）、场景树（QTreeWidget）、属性面板（QStackedWidget）三个展示组件均需对同一份数据（`SceneModel`）做读取和写入，同时要求 **任一组件修改数据后，其余组件自动同步更新**。

**解法**：采用 Model-View 模式 + PyQt5 信号/槽：
- `SceneModel` 作为单一数据源（单一真实源原则），不持有任何 UI 引用；
- 各展示组件持有 `SceneModel` 引用，监听其数据变更信号；
- `SceneEditor` 主窗口作为组件编排器，连接各组件间信号/槽，但不介入具体业务逻辑。

**对比其他选项**：
- 若直接将数据嵌入 UI 组件（如直接操作 `QTreeWidgetItem` 存储数据），则数据散落在 UI 状态中，解析/写出时需从 UI 反向提取，易与展示逻辑混淆；
- Observer 模式可行但 PyQt5 信号/槽在同一进程内已是成熟的 Observer 实现，无需额外抽象。

---

### (2) 模块划分

按层次划分为五层：

| 层次 | 模块 | 文件路径 | 职责 |
|------|------|---------|------|
| 数据模型层 | `SceneModel`、`TaskQueue`、`EditorPreferences` | `src/models/` | 数据类定义、业务逻辑（验证/序列化） |
| 解析器层 | `SceneParser`、`SceneWriter` | `src/parsers/` | `.txt` ↔ `SceneModel` 双向转换 |
| 编排层 | `SceneEditor` | `src/scene_editor.py` | 主窗口、组件拼装、菜单/快捷键 |
| 展示层 | `SceneTreePanel`、`PropertyPanel`、`PreferencesDialog` | `src/panels/` | 层级树、属性编辑、偏好设置 |
| 视口层 | `SceneViewport`、`SurfacePainter` | `src/viewport/` | VTK 3D 渲染、画笔标注 |
| 任务层 | `CommandBuilder`、`TaskRunner` | `src/task_runner/` | CLI 参数构建、QProcess 调度 |

---

### (3) 数据流

完整数据流从文件 → 内存模型 → 多视图 → 用户编辑 → 写回文件 → 执行任务：

```
scene.txt ──[SceneParser]──▶ SceneModel ──┬──▶ SceneTreePanel (层级树)
                                           ├──▶ PropertyPanel   (属性编辑)
                                           └──▶ SceneViewport   (3D 渲染)
                                                      │
                                             SurfacePainter (画笔标注)
                                                      │
                              SceneModel ◀────────────┘
                                    │
                             [SceneWriter]
                                    │
                         scene.txt + STL + .stardis_project.json
                                    │
                             [TaskRunner] ← CommandBuilder ← SceneModel.task_queue
                                    │
                          QProcess (stardis / htpp) → 日志面板
```

**数据流中的关键信号路径**（须读 `scene_editor.py` 确认实际信号名称）：
- `PropertyPanel` 编辑完成 → `SceneModel` 更新 → `SceneViewport.refresh_scene()` 重绘
- `SurfacePainter` 画笔提交 → `SurfaceZone.cell_ids` 更新 → `SceneTreePanel` 计数刷新
- `TaskRunner.task_finished` → `PropertyPanel` 任务队列编辑器状态更新

**[图表需求]** 系统架构图（分层模块图，含信号/槽箭头）  
**[图表需求]** 数据流图（区分数据流 / 控制流 / 信号流，从 `.txt` 文件到 QProcess 的完整链路）

---

### (4) 工程文件格式（.stardis_project.json）

编辑器使用独立工程文件持久化完整状态（场景路径 + 任务队列），与 `.txt` 场景文件分离管理：

- `scene_path`：场景文件路径（相对或绝对）
- `task_queue`：`TaskQueue` 序列化（含所有任务配置、错误策略、环境变量）
- `editor_version`：版本号，用于格式迁移

---

## §5.4 功能模块设计与实现

**篇幅**：约 3500 字  
**写作思路**：逐一介绍五大功能模块，每个模块遵循统一范式（参考徐振道 §6.3 三段式）：

> **功能说明**（此模块实现什么，与其他模块的接口边界）→ **设计要点**（关键技术选型或方案取舍的依据）→ **实现方法**（关键算法/数据结构/协议，以源码为准）→ **图表需求**

**范式说明**："功能说明"面向读者建立认知，"设计要点"阐述非显而易见的技术决策（这是学术论文区别于软件手册的核心），"实现方法"给出可复现的技术细节。截图/图表作为每节的收尾，展示功能的视觉效果。

---

### §5.4.1 场景文件解析与写出模块

**对应文件**：`src/parsers/scene_parser.py`、`src/parsers/scene_writer.py`、`src/models/scene_model.py`  
**篇幅**：约 700字

#### 功能说明

本模块实现 Stardis `.txt` 场景文件与内存数据模型（`SceneModel`）之间的双向转换：`SceneParser` 将文件解析为带类型的 Python dataclass 层级，`SceneWriter` 将修改后的模型回写为求解器可直接读取的文件，同时保留原始注释和列对齐格式。场景文件采用关键字驱动格式（`SOLID`/`FLUID`/`T_BOUNDARY_FOR_SOLID`/`H_BOUNDARY_FOR_SOLID`/`F_BOUNDARY_FOR_SOLID`/`HF_BOUNDARY_FOR_SOLID` 等），每行含空格分隔的位置参数，顺序固定、无可选字段标签。本模块是其余所有模块（3D 视口、属性面板、任务引擎）的数据基础。

#### 设计要点：数据模型选型

采用 Python `dataclasses` 定义数据类（`Body`, `SurfaceZone`, `BoundaryCondition` 及其子类），而非嵌套 `dict`：
- `dataclasses` 提供类型注解、默认值、`__eq__`、`__repr__` 自动生成，便于序列化比较和调试；
- 各边界条件类型（`TemperatureBC`、`ConvectionBC`、`FluxBC`、`CombinedBC`）继承自公共基类，PropertyPanel 中多态分发属性编辑器时只需 `isinstance` 判断，无需手动 `dict` key 检查。

**数据模型层级**（须读 `scene_model.py` 确认实际字段名）：

```
SceneModel
├── global_settings: GlobalSettings (T_ambient, T_reference, scale)
├── bodies: List[Body]
│   ├── SolidBody (name, λ, ρ, cp, δ, T_init, T_imposed, power, side, stl_files)
│   └── FluidBody (name, ρ, cp, T_init, T_imposed, side, stl_files)
├── surface_zones: List[SurfaceZone] (name, bc_ref, cell_ids, stl_file)
├── boundaries: List[BoundaryCondition]
│   ├── TemperatureBC, ConvectionBC, FluxBC, CombinedBC
├── connections: List[Connection]
│   ├── SolidFluidConnection, SolidSolidConnection
└── cameras: List[IRCamera] / probes: List[Probe]
```

**实现方法**

**解析器（`SceneParser`）关键逻辑**：

1. **逐行分词**：跳过空行和 `#` 注释行；
2. **关键字分发**：按首 token 分发到对应解析函数（`_parse_solid()`、`_parse_fluid()`、`_parse_t_boundary()`……）；
3. **注释保留**：将注释行及其位置记录到 `SceneModel.comments`，写出时按行号原位还原；
4. **路径处理**：STL 路径相对于场景文件目录展开为绝对路径，写出时转回相对路径；
5. **容错**：未知关键字记录警告不中断，解析报告附在 `SceneModel.parse_warnings` 中。

**写出器（`SceneWriter`）关键逻辑**：

- 输出顺序：`TRAD` → `SCALE` → 分节注释 → `SOLID`/`FLUID` → 边界条件 → 连接；
- 列对齐：同类关键字段用空格填充至统一宽度，保持可读性；
- 完整性校验：写出前验证至少一个介质、STL 文件存在性、物理量范围合理性。

**[图表需求]** `.txt` 场景文件格式示例（展示 SOLID + H_BOUNDARY 片段）  
**[图表需求]** 解析器状态机示意图（逐行 → 分词 → 关键字分发 → 数据模型）

---

### §5.4.2 3D 可视化与交互模块

**对应文件**：`src/viewport/scene_viewport.py`  
**篇幅**：约 700 字

#### 功能说明

本模块基于 VTK 渲染引擎实现仿真场景的 3D 可视化与鼠标交互。支持加载并渲染多个 STL 几何体（固体/流体/边界面），提供旋转/平移/缩放导航，以及用于表面区域标注的画笔交互模式。通过法线可视化功能，可检查几何体的面法线朝向是否符合求解器约定（决定固-流界面侧 FRONT/BACK/BOTH 的正确配置）。`IRCamera` 和 `Probe` 以标注 Actor（球体/锥体）在视口中显示位置与方向，点击跳转属性编辑。

#### 设计要点：渲染管线与交互模式分离

视口支持两种互斥的交互模式，通过工具栏按钮切换：
- **导航模式**（默认）：`vtkInteractorStyleTrackballCamera`，支持旋转/平移/缩放；
- **画笔模式**：重写 `OnLeftButtonDown` / `OnMouseMove`，拦截鼠标事件用于单元拾取，传入 `SurfacePainter`。

**实现方法**

**分项 Actor 管理**：每个 `Body` 对应一组 `(vtkSTLReader, vtkPolyDataMapper, vtkActor)`，独立控制可见性、颜色、透明度。法线可视化通过 `vtkPolyDataNormals` + 附加 Actor 实现，可按需开关。

**VTK 渲染管线**（须读 `scene_viewport.py` 确认实际管线）：
```
STL 文件 ──[vtkSTLReader]──▶ vtkPolyData
                              │
                         [vtkPolyDataNormals]  ← 法线计算（可选）
                              │
                         [vtkPolyDataMapper]
                              │
                         vtkActor ──▶ vtkRenderer ──▶ QVTKRenderWindowInteractor
```

**单元拾取（画笔模式）**：使用 `vtkHardwareSelector`，在拾取 pass 中渲染场景，通过拾取缓冲区颜色编码获取命中 Actor 和 Cell ID；拾取结果传入 `SurfacePainter.paint(cell_id)`。硬件选择器相比 `vtkCellPicker` 性能更优，在密集三角网格上拾取延迟低。

**探针显示**：`IRCamera` 和 `Probe` 以球体/椎体标注 Actor 在视口中显示其位置与方向，点击可在 PropertyPanel 中跳转编辑。

**[图表需求]** VTK 渲染管线图（从 STL 到 QWidget 嵌入）  
**[图表需求]** 3D 视口截图（展示多 Body 场景 + 法线可视化 + 画笔标注状态）

---

### §5.4.3 边界条件画笔标注模块

**对应文件**：`src/viewport/surface_painter.py`  
**篇幅**：约 500 字

#### 功能说明

本模块实现在 3D 视口中交互式地将三角面片归属到指定 `SurfaceZone`（表面区域），进而关联不同的边界条件。提供画笔和橡皮擦两种操作，支持点击单面片和拖拽涂抹；支持最多 50 步撤销/重做。标注结果持久化到 `.stardis_project.json`，写出场景文件时自动将各区域的 `cell_ids` 重建为独立 STL 文件。

#### 设计要点：命令模式支持撤销/重做

每次画笔操作（涂抹一组 cell_id 到某 `SurfaceZone`）封装为一个 `PaintCommand`：
- 持有受影响的 `(cell_id → old_zone, new_zone)` 映射；
- `execute()` 正向应用，`undo()` 反向恢复；
- 命令栈最大深度 50，超出时丢弃最旧条目。

**实现方法**

**标注数据结构**：对每个 `Body` 对应的 `vtkPolyData`，添加 `vtkIntArray`（字段名 `BoundaryLabel`）记录每个 Cell 的区域编号；`SurfaceZone` 持有其 `cell_ids` 集合（`Set[int]`）作为权威数据源，渲染时将 `cell_ids` 映射到 `BoundaryLabel` 数组并触发 VTK 重绘（按区域着色）。

**画笔/橡皮擦操作**（须读 `surface_painter.py` 确认实际实现）：
- 画笔：将拾取 Cell ID 赋给当前选中 `SurfaceZone`（移除其他 zone 中的该 ID）；
- 橡皮擦：从所有 `SurfaceZone` 中清除拾取 Cell ID；
- 拖拽涂抹：在 `OnMouseMove` 中每隔 N 像素触发一次拾取，积累到当前 stroke 后提交为单个 `PaintCommand`。

**序列化**：`SurfaceZone.cell_ids` 在 `.stardis_project.json` 中以 list of int 存储；写出 `.txt` 时，按 cell_ids 重建对应的 STL 面片子集并导出为独立 STL 文件引用。

**[图表需求]** 撤销/重做命令栈示意图  
**[图表需求]** 画笔标注截图（同一固体表面的不同区域用不同颜色标注）

---

### §5.4.4 场景树与属性编辑模块

**对应文件**：`src/panels/scene_tree_panel.py`、`src/panels/property_panel.py`、`src/panels/task_editors.py`  
**篇幅**：约 700 字

#### 功能说明

本模块提供场景数据的层级浏览（`SceneTreePanel`）与上下文感知属性编辑（`PropertyPanel`）。`SceneTreePanel` 以 `QTreeWidget` 展示 `SceneModel → Body → SurfaceZone → BC` 层级，并将任务队列集成为顶层节点；`PropertyPanel` 使用 `QStackedWidget` 根据选中节点类型动态切换对应编辑器（`BodyEditor`、`SurfaceZoneEditor`、`TaskEditor` 等）。边界条件节点按类型着色（温度/对流/热流/组合），支持右键快捷操作（如 Camera 节点右键直接创建 IR 渲染任务组）。

#### 设计要点：场景树与任务树集成（A3 方案）

任务队列作为场景树顶层的"Tasks"分组节点，与 Solids/Fluids/Boundaries/Probes/Cameras 并列，而非独立的第二个树组件：
- 优点：场景对象（Camera、Probe）和任务队列在同一视图中管理，右键 Camera 可直接创建对应渲染任务，操作链路更短；
- 设计文档：`design/scene_editor/` 中记录了 A1（分离面板）、A2（标签页）、A3（集成树）的方案对比与选型依据。

**实现方法**

**`SceneTreePanel`**（须读 `scene_tree_panel.py`）：
- `QTreeWidget`，节点类型通过自定义 `UserRole` data 区分（Body / SurfaceZone / BC / Camera / Probe / Task）；
- 按边界条件类型着色：温度边界（红色）、对流边界（橙色）、热流边界（黄色）、组合边界（紫色）；
- 右键菜单上下文感知：Camera 节点右键 → 创建 Stardis IR + HTPP 任务组；Probe 节点右键 → 创建探针计算任务；
- 选中信号 `currentItemChanged` → `PropertyPanel.switch_editor(item_type, item_data)`。

**`PropertyPanel`**（须读 `property_panel.py`）：
- `QStackedWidget`，包含子编辑器：`GlobalSettingsEditor`、`BodyEditor`（Solid/Fluid 各一版本）、`SurfaceZoneEditor`、`TaskQueueEditor`、`TaskEditor`；
- 选中节点类型 → 切换对应子编辑器页；
- 属性修改 → 验证 → `SceneModel` 更新 → 发出 `model_changed` 信号。

**`TaskEditor` 参数体系**（须读 `task_editors.py` 和 `task_model.py`）：
- Stardis 参数：`-M`（场景文件）、`-V`（探针模式）、`-R`（IR 渲染模式）、`-p/-P`（探针名称）、`-f`（相机名称）、`-m/-s/-S`（采样参数）、`-t`（线程数）等；
- HTPP 参数：`-i`（IMAGE 模式：exposure/white）、`-m`（MAP 模式：pixcpnt/palette/range/gnuplot）、`-t`（线程数）、`-f`（覆盖）、`-o`（输出文件）；
- **参数序列化**：仅非默认值生成 CLI 参数（默认值不产生多余 flag）；参数类型包含下拉预设（调色板、像素分量）+ 自动/手动切换（白色缩放、范围），联动禁用/启用对应输入框。

**[图表需求]** 场景树截图（展示完整层级：Solids/Fluids/Boundaries/Tasks）  
**[图表需求]** 属性面板截图（展示 BodyEditor 和 TaskEditor 各一张）

---

### §5.4.5 任务配置与执行模块

**对应文件**：`src/task_runner/command_builder.py`、`src/task_runner/task_runner.py`、`src/models/task_model.py`  
**篇幅**：约 700 字

#### 功能说明

本模块实现 Stardis/HTPP 仿真任务的参数配置、CLI 命令构建与队列化执行。`CommandBuilder` 将 `TaskModel`（`StardisParams`/`HtppParams`）转换为可执行的 CLI 参数列表；`TaskRunner` 以 `QProcess` 管理子进程生命周期，顺序执行队列中的任务，实时捕获 stdout/stderr 并流式刷新到日志面板，支持重试/跳过/暂停/取消四种错误处理策略。任务通过名称引用场景中的 Camera/Probe 对象，在执行前统一求值锁定为实际路径（引用语义）。

#### 设计要点：QProcess 非阻塞执行 + 引用语义

- **QProcess vs subprocess**：`QProcess` 自带 `readyReadStandardOutput` / `readyReadStandardError` 信号，无需额外线程轮询输出，直接在主线程事件循环中接收 stdout/stderr，日志面板实时刷新；
- **引用语义（Reference Semantics）**：任务通过名称（Camera 名称、Probe 名称）引用场景对象，而非硬编码路径；`TaskRunner.resolve_all()` 在启动队列时将名称引用求值为实际路径，确保任务配置与场景重命名同步。

**实现方法**

**`CommandBuilder`**（须读 `command_builder.py`）：
- 接受 `Task`（含 `StardisParams` 或 `HtppParams`），输出 `List[str]` CLI 参数列表；
- 仅生成非默认值参数（默认值由 Stardis/HTPP CLI 处理，不显式传入）；
- 特殊逻辑：`-i`/`-m` 参数聚合为引号包裹的字符串（如 `"-i exposure=2.0 white=auto"`）。

**`TaskRunner` 队列调度**（须读 `task_runner.py`）：
- 状态机：`IDLE → RUNNING → PAUSED / ERROR → IDLE`；
- 错误处理策略（`ErrorAction` 枚举）：`RETRY_ONCE`（自动重试一次）、`SKIP`（跳过失败任务继续执行）、`PAUSE`（暂停等待用户介入）、`CANCEL`（中止全部后续任务）；
- HTPP 自动前置：若 HTPP 任务的输入文件尚不存在（依赖 Stardis IR 生成），`resolve_all()` 自动在任务队列中插入对应 Stardis IR 任务为前置依赖。

**日志流式展示**：`QProcess.readyReadStandardOutput` 信号 → `TaskRunner` 发出 `log_line` 信号 → `TaskQueueEditor` 中的 `QTextEdit` 追加输出（ANSI 转义码过滤）。

**[图表需求]** 任务执行状态机图（IDLE / RUNNING / PAUSED / ERROR / DONE 及转移条件）  
**[图表需求]** 任务队列 UI 截图（展示执行进度和日志输出）

---

## §5.5 用户界面设计

**篇幅**：约 600 字  
**写作思路**：

本节从界面层面整合 §5.4 各模块的用户感知，重点描述整体布局、交互设计原则和偏好设置机制，不重复 §5.4 中的实现细节。

---

### (1) 整体布局

三栏设计，对应三个核心交互区域：

```
┌───────────────┬────────────────────────────┬───────────────┐
│  场景树        │       3D 视口               │  属性面板      │
│  (SceneTree   │    (SceneViewport)          │  (Property    │
│   Panel)      │                             │   Panel)      │
│  ─────────    │  [导航] [画笔] [橡皮]        │               │
│  • Solids     │  [法线] [重置] [渲染]        │  当前选中对象   │
│  • Fluids     │                             │  的属性编辑器   │
│  • Boundaries │                             │               │
│  • Cameras    │                             │               │
│  • Probes     │                             │               │
│  • Tasks      │                             │               │
└───────────────┴────────────────────────────┴───────────────┘
                           工具栏
```

三栏通过 `QSplitter` 自由调整宽度；视口在画笔模式下工具栏高亮提示当前激活区域；底部状态栏展示当前工程路径和最后操作信息。

### (2) 交互设计原则

- **所见即所得**：编辑属性面板中的参数后，3D 视口立即刷新（颜色/透明度/法线变化）；
- **右键上下文菜单**：不同节点类型有不同操作（Camera → 创建渲染任务、Body → 添加 SurfaceZone、任务 → 运行/删除/上移/下移）；
- **键盘快捷键**：Ctrl+Z/Y 撤销/重做（画笔操作）、Ctrl+S 保存工程、F5 运行任务队列、Delete 删除选中节点；
- **工具提示（Tooltip）**：HTPP 参数每项附带说明 htpp C 源码行为的 tooltip，降低学习成本。

### (3) 偏好设置（`EditorPreferences`）

通过 `PreferencesDialog`（三标签页）管理：
- **常规**：搜索目录（用于快速找到 STL）、最近工程列表、启动行为；
- **可执行文件标签**：将多个 Stardis/HTPP 可执行文件路径命名为标签（如 `"CPU-Release"`, `"GPU-Release"`），任务配置时通过标签引用（而非硬编码路径）；
- **最近工程**：最近 N 个工程文件，双击快速打开。

首次启动自动检测 `user_settings.json`（v1 偏好），调用 `EditorPreferences.migrate_from_v1()` 迁移至新格式，零配置平滑升级。

**[图表需求]** 完整主界面截图（标注三栏区域名称和工具栏功能）  
**[图表需求]** 偏好设置对话框截图（展示可执行文件标签页）

---

## §5.6 应用案例

**篇幅**：约 1000 字  
**写作思路**：

通过两个仿真场景展示编辑器各功能模块的协同运作，以仿真输出效果（3D 标注截图、IR 渲染结果图）为核心证据。重点在于展示系统**实现了什么功能**，写法参考徐振道 §6.4：场景描述 → 关键功能点说明 → 输出效果图。

**[实验需求]** 准备两个案例场景的完整截图（含 3D 视口画笔标注状态、场景树层级、最终 IR 渲染图）。

---

### (1) 案例 1：多孔介质红外渲染

**场景来源**：`config_examples/` 中的多孔介质配置（须确认实际路径）

**功能演示重点**：

- **场景解析与可视化**：加载多孔介质 STL，3D 视口渲染多个固体 Body（孔隙骨架 + 流体域），法线可视化确认固-流界面朝向；
- **画笔分区标注**：在画笔模式下将孔隙内壁三角面片逐区归属到对应 `SurfaceZone`，视口按区域着色实时反馈标注结果；对流边界条件（Tref/ε/hc 参数）通过属性面板填写后与各 `SurfaceZone` 关联；
- **场景验证**：调用 `stardis -d` 确认几何定义和边界条件无错误；
- **任务执行与后处理**：配置 IR 渲染任务，执行后 HTPP 模块对输出图像进行调色板映射。

**[图表需求]** 多孔介质 3D 视口截图（画笔标注结果，区域着色）  
**[图表需求]** 场景树截图（展示 Body → SurfaceZone → BC 层级关系）  
**[图表需求]** IR 渲染输出（HTPP 调色板映射结果图）

---

### (2) 案例 2：城市建筑热分析

**场景来源**：`config_examples/` 中的城市场景配置（须确认实际路径）

**功能演示重点**：

- **多 Body 复杂场景管理**：场景含多栋建筑，每栋各有屋顶/南墙/北墙等多个表面区域；场景树层级清晰展示所有 Body 及其区域划分；
- **多区域差异化边界条件**：不同朝向的建筑表面设置不同发射率（ε）和对流换热系数（hc），属性面板逐一配置并实时写入 `SceneModel`；
- **多时刻任务队列**：为若干仿真时刻各配置一组 Stardis IR + HTPP 任务，`TaskRunner` 顺序执行，日志面板逐任务输出，HTPP 任务在对应 Stardis 任务完成后自动触发；
- **可执行文件标签切换**：偏好设置中配置 CPU-Release 和 GPU-Release 两个标签，任务配置时通过标签引用，演示与第三/四章实验对应的求解器版本切换。

**[图表需求]** 城市建筑 3D 视口截图（多 Body + 多 SurfaceZone 着色）  
**[图表需求]** 任务队列截图（展示多时刻任务执行进度与日志）  
**[图表需求]** 多时刻 IR 渲染结果图（如正午与傍晚时刻对比）

---

## §5.7 小结

**篇幅**：约 300 字  
**写作思路**：

1. **系统能力总结**：本章设计并实现了 GUI 场景编辑器 StardisEditor，实现了 Stardis 场景文件的完整读写闭环（解析 → 可视化 → 交互式编辑 → 写出）；交互式画笔标注将三角面片分区与边界条件关联直接体现在 3D 视口中；队列化任务调度实现多任务顺序自动化执行；工程文件格式（`.stardis_project.json`）统一管理场景与任务配置；
2. **关键技术要点**：Model-View + 信号/槽架构保证多面板间数据一致性；`vtkHardwareSelector` 实现高性能交互式单元拾取；命令模式支持无限深度撤销/重做；`QProcess` 非阻塞执行与信号驱动日志实时流式输出；
3. **引出第六章**：至此，论文完成了 Wavefront 求解器（第三章）、OptiX 光追后端（第四章）和 GUI 编辑器（本章）三个核心贡献的阐述，第六章将对全文工作进行总结与展望。

---

*大纲创建：2026-03-20*
