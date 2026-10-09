# 基于路径追踪的混合架构耦合热输运红外仿真算法

蒲昱岐，四川大学计算机学院，2026 年硕士毕业论文的完整 LaTeX 源工程。

[完整成果入口](https://github.com/101Laboratory/stardis-research) · [OptiX 后端与求解器](https://github.com/101Laboratory/stardis-oxs3d) · [场景编辑器](https://github.com/101Laboratory/stardis-editor)

原始 Stardis 是法国 Meso-Star 团队的基座工作；论文研究涉及 Windows 构建迁移、OptiX s3d 后端、混合 Wavefront 求解器及场景编辑器。

## 获取与编译

使用带中文支持的 TeX Live、XeLaTeX、BibTeX 和 latexmk：

```powershell
latexmk -xelatex -interaction=nonstopmode MainBody.tex
```

`.latexmkrc`、模板、参考文献样式、章节、BibTeX、必要图片和图源均随工程提供。2026-10-09 在隔离目录编译成功；存在原有重复 page destination 警告，未在本次改写论文排版。

本仓库不包含整篇论文生成 PDF、XDV、编译日志/辅助文件或虚拟环境。必要插图中的 PDF/PNG 是输入资源。研究笔记、评审、答辩和实验材料在核心仓库的 `thesis-materials/`。

## 源码来源

源自当前本地论文工作目录：HEAD `72306b4be707ecfd5e92c26b1a51b57524e7f68a` 加本地最终修改。新建源码发布历史以避免继承整篇 PDF/XDV；原论文历史仍在原仓库保留。

`Template/` 从 https://github.com/salomelly/scu_thesis_template.git 的 `7429516a52d7a086d3842831f5af7943c406a168` 导出，包含本地参考文献样式修改，作为普通源码 vendor 保存。保留原模板作者、版权和 License；模板源自四川大学论文模板项目，许可不自动覆盖论文正文和外来图片。

章节对应：第三章求解器与实验；第四章 OptiX 查询后端；第五章编辑器。论文版本与代码版本由总入口仓库的子模块提交共同固定。
