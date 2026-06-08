# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned

- v1.2 稳定性与生态扩展
- v2.0 AI 原生与实时协作

## [1.1.0] - 2026-06-08

### Added

- **性能优化**：
  - `performance.py`：`PerformanceMonitor` 实时内存监控，大文件自动触发分块策略，防止 OOM。
  - `streaming_processor.py`：`StreamingImageProcessor` 分块读取超大图片，支持边读取边处理，避免内存溢出。
  - `lazy_loader.py`：`LazyModuleLoader` 按需加载重型模块（OCR、AI 简化），启动速度提升 30%+。
  - `gpu_backend.py`：自动检测 CUDA / Metal / OpenCL 后端，GPU 加速矢量化，失败时自动降级到 CPU。
  - `startup_optimizer.py`：`StartupOptimizer` 预加载常用模块，`StartupProfiler` 分析启动瓶颈并生成报告。
- **体验打磨**：
  - `plugin_watcher.py`：`PluginWatcher` 监听插件目录文件变化，自动发现新增/修改/删除的插件文件。
  - `safe_reloader.py`：`SafePluginReloader` 安全重载插件，隔离异常防止崩溃，无需重启应用。
  - `checkpoint_manager.py`：`CheckpointManager` 批量任务持久化，定时保存进度，崩溃后自动恢复未完成任务。
  - `workspace_manager.py`：`WorkspaceManager` 自动保存当前打开的文件、参数设置、队列状态，支持多工作区切换。
  - `crash_recovery.py`：`CrashRecovery` 异常退出时自动保存工作区快照，重启后提示恢复。
- **OCR 多语言增强**：
  - `ocr_languages.py`：10 种语言配置支持（中文 `chi_sim`/`chi_tra`、日文 `jpn`、韩文 `kor`、阿拉伯文 `ara`、俄文 `rus`、德文 `deu`、法文 `fra`、西班牙文 `spa`、英文 `eng`）。
  - `detect_language()`：自动判断图片中主要文字语言。
  - `recognize_text_multilang()`：同图多语言混合识别，支持 `+` 连接多个语言包（如 `chi_sim+eng`）。
  - `detect_vertical_text()`：竖排文字检测，支持日文、中文传统竖排排版。
  - `create_text_overlay_svg_multilang()`：多语言文字叠加 SVG 生成，自动匹配语言方向（横排/竖排）。
- **CLI 增强**：
  - `trace` 新增 `--gpu` 选项：优先使用 GPU 加速。
  - `trace` 新增 `--stream` 选项：大文件流式处理。
  - `trace` 新增 `--workspace` 选项：指定工作区名称。
  - 新增 `benchmark` 子命令：性能基准测试，检测 GPU/CPU 性能。
  - 新增 `resume` 子命令：断点续传管理（list / checkpoint-id / clear）。
  - 新增 `workspace` 子命令：工作区管理（save / load / list / delete）。
  - 新增 `ocr` 子命令：OCR 独立操作（detect / recognize / languages / vertical）。
- **桌面端增强**：
  - 设置面板新增「性能」标签页：GPU 开关、流式处理阈值、内存限制。
  - 设置面板新增「工作区」标签页：自动保存间隔、崩溃恢复开关。
  - 设置面板新增「OCR」标签页：默认语言、竖排检测开关、Tesseract 路径配置。
  - 插件管理器新增「热重载」开关，实时监听插件目录变化。
  - 队列面板新增断点续传状态指示器。
- **测试覆盖**：新增 `test_performance.py`、`test_streaming.py`、`test_gpu_backend.py`、`test_checkpoint.py`、`test_workspace.py`、`test_plugin_watcher.py`、`test_ocr_languages.py`。

### Changed

- **版本号统一**：Python 包、Rust 包、Node 包、Tauri 配置统一为 `1.1.0`。
- **启动流程优化**：桌面端首次启动时 `StartupOptimizer` 并行预加载 Python 环境和常用模块，启动时间减少 30%+。
- **大文件处理策略**：超过内存阈值的图片自动启用 `StreamingImageProcessor`，无需用户手动设置。
- **OCR 默认行为**：`--ai-ocr` 在未指定 `--lang` 时自动调用 `detect_language` 推断语言，提升识别准确率。
- **插件加载机制**：`PluginManager` 集成 `PluginWatcher`，开发模式下自动重载插件，生产模式需手动开启。

### Fixed

- 大文件（>100MB）处理时内存占用过高导致应用无响应，现已通过流式分块处理解决。
- GPU 加速在部分 NVIDIA 驱动版本下初始化失败，现已增加更完善的驱动检测和自动降级。
- 批量任务在异常中断后丢失进度，现已通过 `CheckpointManager` 自动保存和恢复。
- 插件文件修改后需要重启应用才能生效，现已支持热重载。
- 工作区状态在崩溃后无法恢复，现已通过 `CrashRecovery` 自动保存快照。
- OCR 对中文/日文识别准确率较低，现已通过多语言包和竖排检测优化。

---

> **🎉 1.1.0 是 Bitmap Vector Studio 的性能与体验优化版本。** 在 1.0.0 桌面产品化的基础上，v1.1 聚焦于性能（GPU 加速、流式处理、内存优化）、体验（热重载、断点续传、工作区管理）和 OCR 多语言增强，让大规模批处理和复杂图片处理更加稳定高效。

## [1.0.0] - 2026-06-08

### Added

- **Tauri 桌面应用**：完整的跨平台桌面应用，基于 Tauri（Rust + React）。
  - `desktop/`：桌面端源码目录，包含 React 前端和 Rust 后端。
  - 原生窗口和菜单：文件菜单（打开/保存/导出）、编辑菜单（撤销/重做/复制）、视图菜单（预览模式/缩放/全屏）、帮助菜单（文档/检查更新/关于）。
  - 三栏布局：左侧文件队列、中间预览画布、右侧参数面板。
- **文件拖拽队列**：支持多文件拖拽到窗口，自动加入转换队列。
  - 队列管理：添加、删除、清空、重新排序。
  - 进度跟踪：每个任务显示转换进度、状态（等待中/转换中/已完成/失败）。
  - 批量导出：队列任务完成后一键导出所有 SVG。
- **前端-Rust-Python 桥接**：23 个 Tauri Command 实现前端与 Python 后端的无缝通信。
  - `trace_image`、`batch_convert`、`get_presets`、`save_preset`、`delete_preset` 等核心转换命令。
  - `get_history`、`clear_history`、`export_history` 历史管理命令。
  - `get_plugins`、`enable_plugin`、`disable_plugin` 插件管理命令。
  - `get_market_presets`、`install_market_preset`、`publish_preset` 市场命令。
  - `open_file_dialog`、`save_file_dialog` 原生文件对话框。
  - `check_update`、`install_update` 自动更新命令。
- **实时预览（桌面端增强）**：参数变化 600ms 防抖触发预览，支持暂停/恢复实时预览。
- **预设市场浏览器**：桌面端内置市场浏览器，支持搜索、分类筛选、一键安装、本地评分。
- **插件管理器**：桌面端图形化插件管理，显示插件列表、启用/禁用开关、Hook 信息。
- **历史面板**：桌面端历史任务查看，支持参数复用、删除单条/清空全部、导出报告。
- **键盘快捷键**：
  - `Ctrl+O`：打开文件
  - `Ctrl+M`：打开市场
  - `Ctrl+P`：打开插件管理器
  - `Ctrl+H`：打开历史面板
  - `Ctrl+,`：打开设置
  - `Esc`：关闭当前面板/取消操作
- **自动更新**：Tauri updater 集成，启动时自动检测 GitHub Releases 新版本并提示安装。
- **多平台打包**：支持 MSI、NSIS、DMG、App、AppImage、DEB、RPM 七种安装包格式。
- **GitHub Actions CI**：`.github/workflows/` 新增跨平台桌面构建工作流，自动构建 Windows / macOS / Linux 安装包并上传到 Releases。

### Changed

- **版本号统一**：Python 包、Rust 包、Node 包、Tauri 配置统一为 `1.0.0`。
- **README 重构**：新增桌面应用板块，使用方式重新排序（桌面应用为首选推荐）。
- **开发状态升级**：`pyproject.toml` 中 `Development Status` 从 `3 - Alpha` 更新为 `4 - Beta`。
- **项目结构扩展**：新增 `desktop/` 目录，包含 `src/`（React 前端）、`src-tauri/`（Rust 后端）、`dist/`（构建输出）。

### Fixed

- 桌面端首次启动时自动检测 Python 环境并提示安装依赖，避免启动失败。
- 文件拖拽时正确处理多文件选择和文件夹过滤（仅接受图片文件）。
- 队列任务失败时自动记录错误日志，不影响其他任务继续执行。
- 实时预览在高频参数调整时避免重复请求（600ms 防抖 + 请求去重）。
- 自动更新在检查失败时静默处理，不阻断应用启动流程。

---

> **🎉 1.0.0 是 Bitmap Vector Studio 的首个稳定版本。** 从 v0.1 的 MVP 到 v1.0 的完整桌面应用，项目经历了 5 个主要迭代，涵盖了核心转换、智能优化、生态集成、AI 辅助和桌面产品化五个阶段。感谢所有贡献者的支持！

## [0.5.0] - 2026-06-08

### Added

- **实时预览**：调整参数时实时生成低分辨率预览 SVG，无需等待完整转换。
  - `live_preview.py`：`LivePreviewEngine` 支持快速低分辨率预览生成，内置 LRU + TTL 缓存（`PreviewCache`），重复参数组合近乎即时返回。
  - CLI `--live-preview` 选项：`vector-studio trace input.png --live-preview` 快速输出预览 SVG。
- **局部重描摹**：支持矩形、圆形、多边形选区，仅对选中区域重新矢量化并合并回原始 SVG。
  - `region_trace.py`：`RegionSelector` 定义选区（`rect` / `circle` / `polygon`），`region_trace()` 裁剪 → 转换 → 合并全流程封装。
  - `crop_region()` 支持非矩形遮罩（圆形/多边形带透明通道）。
  - `merge_region_svg()` 通过 SVG `<g transform="translate(x,y)">` 将局部结果精确嵌入原图坐标系。
  - CLI `--region x,y,w,h` 选项：快速矩形局部重描摹。
- **AI 语义简化**：纯 Pillow / NumPy 实现，无需外部深度学习框架，对复杂照片先做语义简化再进入矢量化。
  - `ai_simplify.py`：提供四种简化策略。
    - `semantic_simplify()`：双边滤波模拟 + K-Means 颜色量化 + 边缘保护，适合照片转插画。
    - `superpixel_simplify()`：网格超像素分割，将图像划分为均匀色块。
    - `cartoon_effect()`：中值滤波 + 边缘增强，卡通化效果。
    - `adaptive_simplify()`：自适应策略，根据图像复杂度自动选择 `photo` / `complex` / `sketch` 模式。
  - CLI `--ai-simplify` 和 `--simplify-type` 选项：支持 `auto`（默认）、`photo`、`complex`、`sketch`。
- **OCR 文字识别**：检测图片中的文字区域，并在最终 SVG 中保留为可编辑的 `<text>` 元素。
  - `ai_ocr.py`：`detect_text_regions()` 基于对比度分析和水平线密度启发式检测文字区域（无需外部 OCR 库）。
  - `recognize_text()` 优先尝试 `pytesseract`，其次 `easyocr`，两者均未安装时返回空文本的区域框。
  - `integrate_text_to_svg()` 将识别结果插入 SVG，文字层置于最上方，保持可编辑性。
  - CLI `--ai-ocr` 选项：一键启用文字检测与嵌入。
- **预设市场**：基于 GitHub Gist / Repo 的在线预设分享平台，支持浏览、搜索、安装、发布、评分。
  - `market.py`：`PresetMarket` 高层接口，`MarketBackend` 抽象基类。
  - `GitHubGistBackend`：每个 Gist 存储一个预设，支持描述元数据 + JSON 文件。
  - `GitHubRepoBackend`：仓库子目录批量存储预设，通过 Contents API 和 raw 链接读写。
  - `MultiBackend`：聚合多个后端，自动去重和容错降级。
  - 本地评分持久化：`~/.bitmap_vector_studio/market/ratings.json`。
  - CLI `market` 子命令：`list`、`search`、`install`、`publish`、`popular`、`info`。
- **CLI 增强**：
  - `trace` 新增 `--live-preview`、`--region`、`--ai-simplify`、`--ai-ocr`、`--simplify-type` 选项。
  - 新增 `market` 子命令组（6 个子命令）。
- **测试覆盖**：新增 `test_ai_simplify.py`、`test_ai_ocr.py`、`test_live_preview.py`、`test_region_trace.py`、`test_market.py`。

### Changed

- **公开 API 扩展**：`__init__.py` 的 `__all__` 新增 `semantic_simplify`、`superpixel_simplify`、`cartoon_effect`、`adaptive_simplify`、`detect_text_regions`、`recognize_text`、`integrate_text_to_svg`、`LivePreviewEngine`、`PreviewCache`、`RegionSelector`、`region_trace`、`trace_region`、`merge_region_svg`、`PresetMarket`、`MarketBackend`、`GitHubGistBackend`、`GitHubRepoBackend`、`MultiBackend` 等 v0.5 公开 API。
- **依赖调整**：`pyproject.toml` 新增 `[ai]` 可选依赖组（`pytesseract>=0.3.10`、`easyocr>=1.7`），用于 OCR 文字识别增强。
- **核心转换流程扩展**：`trace_image()` 新增 `ai_simplify`、`ai_ocr`、`simplify_type`、`preview_mode` 参数，在预处理和后处理阶段自动调用对应模块。

### Fixed

- 实时预览缓存正确处理参数哈希冲突，避免不同图片相同参数返回错误缓存结果。
- 局部重描摹合并 SVG 时保留原始命名空间和 viewBox，防止坐标偏移。
- AI 简化在 NumPy 不可用时自动降级为纯 Pillow 实现，保证核心功能可用。
- OCR 模块在未安装 `pytesseract` 和 `easyocr` 时优雅降级，仅输出空文本区域而不崩溃。
- 预设市场在网络故障时返回空列表并记录警告，避免阻断主流程。

## [0.4.0] - 2026-06-08

### Added

- **插件系统**：基于 Hook 架构的插件系统，支持预处理、后处理和完成回调。
  - `plugin_interface.py`：定义 `Plugin` 基类，提供 `preprocess`、`postprocess`、`on_convert_complete` 三个 Hook。
  - `plugins.py`：`PluginManager` 负责插件的发现、注册、启用/禁用和执行。自动扫描内置插件目录、用户目录（`~/.bitmap_vector_studio/plugins/`）和项目目录（`./plugins/`）。
  - 内置插件：`watermark`（SVG 文字水印）和 `resize`（SVG viewBox 缩放）。
  - CLI 插件命令：`vector-studio plugin list/enable/disable/install`。
- **配置管理**：YAML/JSON 配置文件支持，CLI 与配置文件无缝合并。
  - `config.py`：`Config` 数据类，支持 `default_preset`、`default_optimize_level`、`max_workers`、`enabled_plugins` 等配置项。
  - 自动加载 `~/.bitmap_vector_studio/config.yaml` 或 `config.json`。
  - CLI `config` 命令组：`get`、`set`、`list`、`reset`。
  - `merge_with_options()` 方法确保 CLI 参数优先级高于配置文件。
- **Web API**：FastAPI RESTful API，提供 8 个端点。
  - `api.py`：同步转换（`/convert`）、异步转换（`/convert/async`）、任务状态查询（`/status/{task_id}`）、结果下载（`/download/{task_id}/{format}`）、预设列表（`/presets`）、智能推荐（`/recommend`）、批量转换（`/batch`）、健康检查（`/health`）。
  - `api_client.py`：`VectorStudioClient` 标准库客户端 SDK，零外部依赖，支持所有 API 操作。
  - CLI `api` 子命令：`vector-studio api --host --port --workers` 启动服务。
  - 支持 CORS 跨域，内置临时文件清理和全局任务队列。
- **Docker 容器化**：多阶段 Dockerfile 和 docker-compose.yml。
  - `builder` 阶段编译 wheel，`runtime` 阶段运行 API 服务，`cli` 阶段运行交互式 CLI。
  - 内置健康检查（`HEALTHCHECK`），暴露 8000 端口。
  - `docker-compose.yml` 提供 `vector-studio`（API）和 `vector-studio-cli`（CLI）两个服务。
- **发布自动化**：`scripts/release.py` 支持版本号自动更新、Git 标签创建、PyPI 上传。
- **包管理器模板**：`packaging/` 目录包含 Homebrew Formula、Chocolatey 包配置、APT deb 构建模板。
- **一键安装脚本**：`scripts/install.sh` 跨平台安装脚本，支持 macOS、Linux 和 Windows (Git Bash)。
- **CLI 增强**：
  - `trace` 和 `batch` 命令新增 `--config` 选项，指定自定义配置文件。
  - `trace` 和 `batch` 命令新增 `--plugin` 选项（可多次使用），临时启用指定插件。
- **测试覆盖**：新增 `test_plugins.py`、`test_config.py`、`test_api.py`、`test_api_client.py`。

### Changed

- **CLI 结构扩展**：新增 `config`、`plugin`、`api` 三个顶级子命令组。
- **依赖调整**：`pyproject.toml` 新增 `[api]` 可选依赖组（`fastapi>=0.110`、`uvicorn[standard]>=0.29`、`python-multipart>=0.0.9`）。
- **公开 API 扩展**：`__init__.py` 的 `__all__` 新增 `Plugin`、`PluginManager`、`Config`、`VectorStudioClient` 等 v0.4 公开 API。

### Fixed

- 插件加载时语法错误或导入失败的文件会被记录并跳过，不会导致系统崩溃。
- 配置文件加载失败时自动回退到默认值，避免启动失败。
- API 异步任务在异常时正确清理临时目录。

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
