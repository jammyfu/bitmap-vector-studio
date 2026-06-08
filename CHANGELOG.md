# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned

- 插件系统与自定义后处理
- 预设市场与在线分享
- Docker 镜像与包管理器发布
- AI 辅助重绘与 OCR

## [0.3.0] - 2025-06-08

### Added

- **智能背景透明**：自动检测 Logo 类图片的背景色并移除，生成透明 PNG 后进入矢量化。支持边缘颜色聚类分析和非矩形背景检测。
- **图像增强**：纯 Pillow 实现，无需 OpenCV。包含边缘增强（`edge_enhance`）、扫描件去噪（`scan_denoise`）、自适应对比度（`auto_contrast`）、智能锐化（`sharpen`）和自动类型判断（`adaptive_enhance`）。
- **智能预设推荐**：分析图片颜色数量、边缘密度、宽高比、对称性等特征，自动推荐最佳预设（bw / logo / pixel_art / photo / poster / scan），并给出置信度和推荐理由。
- **SVG 深度优化**：新增 `svg_optimizer` 模块，支持路径合并（`merge_same_color_paths`）、相似颜色合并（`merge_similar_colors`）、路径简化（`simplify_path_data`）和综合优化（`optimize_svg_comprehensive`）。
- **SVG 质量评分**：从文件大小、路径效率、复杂度、颜色效率四个维度计算 SVG 综合质量分（0-100）。
- **参数搜索**：`search` CLI 命令支持多参数批量试跑，自动挑选最优结果。支持完整网格搜索（`search_best_params`）和快速预设搜索（`quick_search`）。
- **批量任务队列**：`TaskQueue` 支持异步并发转换、进度跟踪、失败重试、暂停恢复。`batch` 命令新增 `--workers` 和 `--retry` 选项。
- **队列 CLI 子命令**：新增 `vector-studio queue add/status/start/report` 命令组，支持任务队列管理。
- **优化级别控制**：`trace` 和 `batch` 命令新增 `--optimize-level` 选项（none / basic / comprehensive / aggressive），精细控制 SVG 优化深度。
- **质量评分输出**：`trace` 和 `batch` 命令新增 `--score` 选项，转换后输出 SVG 质量评分。
- **智能 CLI 选项**：`trace` 命令新增 `--smart-remove-bg`（背景透明）、`--enhance`（图像增强）、`--recommend`（预设推荐）。
- **NumPy 可选依赖**：智能分析和背景透明功能推荐安装 NumPy，通过 `pip install -e ".[smart]"` 安装。
- **完整测试覆盖**：新增 `test_smart_background.py`、`test_smart_recommend.py`、`test_enhance.py`、`test_svg_optimizer.py`、`test_param_search.py`、`test_task_queue.py` 等测试模块。

### Changed

- **CLI 增强**：`trace` 命令支持 `--recommend` 模式，仅分析图片并输出推荐预设，不执行转换。
- **批量转换增强**：`batch` 命令当 `--workers > 1` 或 `--retry > 0` 时，自动使用 `TaskQueue` 并发处理。
- **SVG 优化升级**：`optimize_svg_text` 和 `optimize_svg_file` 保留原有功能，`svg_optimizer` 提供更深度的优化能力。
- **依赖调整**：核心依赖保持纯 Pillow，智能功能通过可选依赖 NumPy 增强。

### Fixed

- 批量转换在大文件夹下的内存占用优化（TaskQueue 流式处理）。
- SVG 路径合并时保留命名空间和 viewBox 的稳定性修复。
- 参数搜索在极端参数组合下的异常处理增强。

## [0.2.0] - 2025-06-08

### Added

- **自定义预设管理**：支持保存、加载、删除、导入、导出用户自定义预设（JSON 格式），内置预设与用户预设分组显示。
- **任务历史记录**：自动记录每次转换任务的参数、统计信息和耗时，支持从历史任务一键复用参数到当前面板。
- **历史报告导出**：支持将最近任务历史导出为 CSV 或 Markdown 表格格式。
- **外部编辑器集成**：自动检测并一键打开 Adobe Illustrator、Inkscape、Affinity Designer、Figma、CorelDRAW、Vectr、Boxy SVG 等矢量编辑器。
- **GUI 并排对比模式**：原图与 SVG 结果左右并排显示，同步缩放查看。
- **GUI 叠加对比滑块**：拖动滑块或点击画面查看原图与矢量化结果的差异对比。
- **预设分组选择器**：内置预设（🏭）与用户自定义预设（👤）在 GUI 中分组展示，带图标区分。
- **最近任务历史面板**：侧边栏显示最近 5 条任务记录，支持一键加载参数。
- **SVG 结构分析**：转换完成后可查看路径数、多边形数、矩形数、圆形数、组数、viewBox 和文件大小。
- **SVG 图层列表**：按 `<g>` 元素提取图层，显示 ID 和颜色预览（Inkscape 兼容）。
- **参数分组折叠面板**：侧边栏参数按「核心参数」「高级参数」「预处理」「导出选项」分组折叠，界面更整洁。
- **SVG 图层命名**：CLI 和 GUI 支持 `--name-layers` 选项，按颜色或顺序自动命名 SVG 图层。
- **颜色面板提取**：SVG 结构分析中显示各图层的填充颜色。
- **CLI 编辑器打开选项**：`--open` 参数支持指定编辑器名称或系统默认程序打开结果。
- **批量转换后打开**：`batch` 命令支持 `--open` 选项，转换完成后在默认编辑器中打开每个结果。

### Changed

- **GUI 布局重构**：侧边栏改为参数控制区，主区域用于图片预览和结果展示，空间利用率更高。
- **预设系统增强**：`options_from_preset()` 支持 `custom` 预设名称，从默认参数开始自定义。
- **滑块控件优化**：所有数值滑块带实时数值显示，交互更直观。
- **错误处理改进**：历史记录和外部编辑器失败不再阻断主转换流程，以警告形式提示。

### Fixed

- 用户预设与内置预设名称冲突时的覆盖逻辑明确化（用户预设优先）。
- 历史记录文件自动修剪，防止无限增长（默认保留最近 100 条）。

## [0.1.0] - 2025-05-20

### Added

- **核心矢量化引擎**：基于 VTracer 的位图转 SVG 封装，支持 PNG / JPG / WEBP / BMP / TIFF 输入。
- **6 种内置预设**：`bw`（黑白线稿）、`poster`（海报插画）、`photo`（高保真照片）、`logo`（Logo/图标）、`pixel_art`（像素艺术）、`scan`（扫描图）。
- **Streamlit GUI**：可交互的参数面板、图片上传、预设选择、SVG 下载。
- **Typer CLI**：`trace` 单图转换、`batch` 批量转换、`presets` 预设列表命令。
- **参数系统**：`TraceOptions` 数据类封装 12+ 项 VTracer 参数，带完整校验逻辑。
- **SVG 优化与统计**：转换后自动清理 SVG，输出路径数、节点数、文件大小等统计信息。
- **多格式导出**：支持通过 CairoSVG 导出 PDF 和 PNG 预览，预留 Inkscape CLI 导出 EPS。
- **预处理**：Pillow 图像预处理（降噪、限制输入边长、Posterize 颜色量化）。
- **项目骨架**：完整的 Python 包结构、pytest 测试套件、ruff 代码风格配置。
