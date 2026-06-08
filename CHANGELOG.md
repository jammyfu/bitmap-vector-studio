# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned

- 自动背景透明处理
- OpenCV 边缘增强与扫描件去噪
- SVG 路径合并和颜色合并优化
- 智能预设推荐
- 批量任务队列与进度可视化

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
