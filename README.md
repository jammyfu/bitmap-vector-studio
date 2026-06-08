# Bitmap Vector Studio

<p align="center">
  <img src="https://raw.githubusercontent.com/jammyfu/bitmap-vector-studio/main/docs/assets/logo.png" alt="Bitmap Vector Studio" width="120">
</p>

<h1 align="center">Bitmap Vector Studio</h1>

<p align="center">
  <strong>基于 VTracer 的 Illustrator 风格位图转矢量工具</strong>
</p>

<p align="center">
  <a href="https://github.com/jammyfu/bitmap-vector-studio/actions"><img src="https://img.shields.io/github/actions/workflow/status/jammyfu/bitmap-vector-studio/ci.yml?branch=main&label=tests" alt="Tests"></a>
  <img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License: MIT">
  <img src="https://img.shields.io/badge/version-3.0.0-orange" alt="Version 3.0.0">
</p>

---

Bitmap Vector Studio 是一个以 **VTracer** 为核心引擎的位图转矢量工具，目标是做出接近 Adobe Illustrator「Image Trace / 图像描摹」体验的本地工具。

- 支持 PNG / JPG / JPEG / WEBP / BMP / TIFF 输入
- 输出紧凑 SVG，并可选导出 PDF / PNG 预览 / EPS
- 内置 Illustrator 风格预设：黑白线稿、海报插画、高保真照片、Logo、像素艺术、扫描图
- **v0.3 新增**：智能背景透明、图像增强、智能预设推荐、SVG 深度优化、参数搜索、批量任务队列
- **v0.4 新增**：插件系统、Web API、Docker 容器化、配置管理、一键安装脚本、包管理器模板
- **v0.5 新增**：实时预览、局部重描摹、AI 语义简化、OCR 文字识别、预设市场
- **v1.1 新增**：性能优化（GPU 加速、大文件流式处理、内存监控）、体验打磨（插件热重载、断点续传、工作区自动保存）、OCR 多语言增强（10 种语言、竖排文字）
- **v1.2 新增**：多矢量化引擎（VTracer/Potrace/AutoTrace 自动选择）、插件 SDK 完善（验证器/脚手架/调试器/文档生成）、云端同步预览（分享链接+QR码）、社区工具链（预设验证/贡献指南/发布说明）
- **v2.0 新增**：本地 AI 模型推理（ONNX Runtime 分割/风格迁移/超分辨率）、多引擎智能编排（AI 辅助选择最优引擎流水线）、实时协作编辑（WebSocket 多人同步）、矢量动画导出（SVG SMIL/Lottie/GIF/CSS）、智能批处理工作流（可视化节点编辑器）、跨设备同步（桌面端↔网页端↔API服务端）、云端账号与付费市场（用户账号/积分/付费插件/预设）
- **v3.0 新增**：AI 生成式矢量创作（文本/图生图生成矢量风格图）、云端渲染农场（分布式Worker并行渲染）、设计系统集成（Figma/Sketch导入导出+设计令牌同步）、3D矢量与AR预览（SVG挤出3D/AR标记/USDZ导出）、企业级权限管理（RBAC团队工作区/SSO/审计日志）、智能模板市场（AI推荐/评分/发布）
- **v1.0 新增**：Tauri 桌面应用、文件拖拽队列、原生窗口菜单、自动更新、多平台打包、键盘快捷键
- 自定义预设管理：保存、加载、删除、导入、导出用户预设（JSON）
- 任务历史记录：自动记录转换历史，支持参数复用、CSV/Markdown 报告导出
- 外部编辑器集成：一键打开 Illustrator、Inkscape、Affinity Designer、Figma 等
- 提供桌面应用（推荐）、Streamlit 网页 GUI、命令行批处理、FastAPI RESTful 服务和 Docker 容器化五种使用方式

> **说明**：矢量化本质是近似重建。Logo、图标、线稿、海报插画最容易达到专业效果；复杂照片可以接近 Illustrator 的「High Fidelity Photo」方向，但会在文件大小、颜色层数、可编辑性之间取舍。

---

## ✨ 功能特性

### 🎨 核心转换
- 🖼️ 支持多种位图格式：PNG、JPG、WEBP、BMP、TIFF
- 📐 输出标准 SVG，兼容 Inkscape、Illustrator、Figma 等主流工具
- 🎯 6 种内置预设，覆盖常见设计场景
- 🔧 12+ 项可调参数，精细控制转换效果

### 🧠 智能功能（v0.3）
- 🤖 **智能预设推荐**：分析图片颜色、边缘密度、宽高比等特征，自动推荐最佳预设（bw / logo / pixel_art / photo / poster / scan）
- 🪟 **智能背景透明**：自动检测 Logo 类图片的背景色并移除，生成透明 PNG 后进入矢量化
- ✨ **图像增强**：边缘增强、扫描件去噪、自适应对比度（纯 Pillow 实现，无需 OpenCV）

### 🔧 高级优化（v0.3）
- 🔀 **SVG 深度优化**：路径合并、相似颜色合并、路径简化，显著减小 SVG 体积
- 📊 **质量评分**：从文件大小、路径效率、复杂度、颜色效率四个维度评估 SVG 质量
- 🔍 **参数搜索**：多参数批量试跑，自动挑选最优结果，告别手动调参
- 📋 **批量任务队列**：异步并发转换、进度跟踪、失败重试、暂停恢复

### 🔌 生态与集成（v0.4）
- 🔌 **插件系统**：基于 Hook 的插件架构，支持预处理、后处理、完成回调。内置水印和缩放插件，支持用户自定义插件
- 🌐 **Web API**：FastAPI RESTful API（8 个端点），支持同步/异步转换、批量任务、预设查询、智能推荐
- 🐳 **Docker 容器化**：多阶段 Dockerfile，支持 API 服务和 CLI 两种运行模式，内置健康检查
- ⚙️ **配置管理**：YAML/JSON 配置文件，CLI `config` 命令组，配置与命令行参数自动合并
- 📦 **包管理器模板**：Homebrew Formula、Chocolatey、APT deb 模板，支持多平台分发
- 🚀 **一键安装脚本**：`install.sh` 跨平台自动安装，支持 macOS / Linux / Windows (Git Bash)

### 🤖 AI 辅助与实时交互（v0.5）
- ⚡ **实时预览**：调整参数时实时生成低分辨率预览 SVG，LRU + TTL 缓存，重复参数近乎即时返回
- 🎯 **局部重描摹**：矩形 / 圆形 / 多边形选区，仅重新生成选中区域的 SVG 并合并回原始坐标系
- 🧠 **AI 语义简化**：纯 Pillow / NumPy 实现，无需深度学习框架。支持语义简化、超像素分割、卡通化效果、自适应策略
- 📝 **OCR 文字识别**：检测文字区域，保留为 SVG 可编辑 `<text>` 元素。支持 pytesseract / easyocr 可选依赖

### 🖥️ 桌面应用（v1.0）
- 🖥️ **Tauri 桌面端**：基于 Rust + React 的跨平台桌面应用，原生窗口和菜单
- 📥 **文件拖拽队列**：多文件拖拽到窗口，自动加入转换队列，支持进度跟踪和批量导出
- ⌨️ **键盘快捷键**：Ctrl+O/M/P/H/,/Esc 等常用操作快捷键
- 🔄 **自动更新**：启动时自动检测 GitHub Releases 新版本并提示安装
- 📦 **多平台打包**：支持 MSI、NSIS、DMG、App、AppImage、DEB、RPM 七种安装包
- 🔌 **桌面端插件管理器**：图形化界面浏览、启用/禁用插件
- 🛒 **桌面端预设市场**：内置市场浏览器，搜索、分类筛选、一键安装
- 🕐 **桌面端历史面板**：历史任务查看和参数复用
- 👁️ **实时预览增强**：参数变化 600ms 防抖触发预览，支持暂停/恢复

### ⚡ 性能优化（v1.1）
- 🚀 **GPU 加速预览**：自动检测 CUDA / Metal / OpenCL 后端，矢量化过程 GPU 加速，失败时自动降级到 CPU
- 🌊 **大文件流式处理**：`StreamingImageProcessor` 分块读取超大图片，避免内存溢出，支持边读取边处理
- 🧠 **内存监控优化**：`PerformanceMonitor` 实时追踪内存占用，大文件自动触发分块策略，防止 OOM
- ⚡ **延迟加载**：`LazyModuleLoader` 按需加载重型模块（OCR、AI 简化），启动速度提升 30%+
- 🔥 **启动预热**：`StartupOptimizer` 预加载常用模块，`StartupProfiler` 分析启动瓶颈

### 🛠️ 体验打磨（v1.1）
- 🔌 **插件热重载**：`PluginWatcher` 监听插件目录文件变化，`SafePluginReloader` 安全重载，无需重启应用
- 💾 **断点续传**：`CheckpointManager` 批量任务持久化，崩溃后自动恢复未完成任务
- 🗂️ **工作区自动保存**：`WorkspaceManager` 自动保存当前打开的文件、参数设置、队列状态，崩溃后一键恢复
- 🌍 **崩溃恢复**：异常退出时自动保存工作区快照，重启后提示恢复

### 📝 OCR 多语言增强（v1.1）
- 🌐 **10 种语言支持**：中文、日文、韩文、阿拉伯文、俄文、德文、法文、西班牙文、英文等
- 📖 **竖排文字检测**：自动识别竖排排版文字（日文、中文传统排版）
- 🔤 **语言自动检测**：`detect_language` 自动判断图片中主要文字语言
- 🎯 **多语言混合识别**：`recognize_text_multilang` 支持同图多语言混合识别

### 🔧 多引擎支持（v1.2）
- ⚙️ **三引擎架构**：VTracer（默认）、Potrace（黑白线稿）、AutoTrace（中心线提取）
- 🤖 **自动引擎选择**：`EngineSelector` 根据颜色数、边缘密度、对比度自动推荐最佳引擎
- 📊 **引擎基准测试**：`engine_benchmark` 对比各引擎在质量、速度、文件大小维度的评分
- 🔀 **引擎切换**：CLI `--engine` 选项一键切换，或 `auto` 让系统自动选择

### 🧩 插件 SDK（v1.2）
- ✅ **PluginValidator**：验证插件结构、Hook 签名、依赖完整性
- 🏗️ **PluginScaffold**：一键生成标准插件模板（含测试文件、README）
- 🐛 **PluginDebugger**：单步执行 Hook、捕获异常、输出调用链日志
- 📝 **PluginDocsGenerator**：自动生成插件 API 文档（Markdown）

### ☁️ 云端分享（v1.2）
- 🔗 **分享链接**：转换结果一键上传到 GitHub Gist 或本地服务器，生成可分享 URL
- 📱 **QR 码生成**：扫码即可在手机/平板上查看 SVG 预览
- 🔄 **跨设备同步**：桌面端转换，移动端预览，无需手动传输文件
- 🛡️ **分享管理**：`vector-studio cloud list/revoke` 管理已分享内容

### 🤖 AI 原生（v2.0）
- 🧠 **本地 AI 模型推理**：ONNX Runtime 实时分割、风格迁移、超分辨率，无需云端 API
- 🎯 **智能语义分割**：自动识别图像主体与背景，精准分离前景对象后矢量化
- 🎨 **AI 风格迁移**：将艺术风格应用到预处理阶段，生成风格化矢量插画
- 🔍 **超分辨率重建**：低分辨率素材先通过 AI 放大再矢量化，显著提升细节保留

### 👥 实时协作（v2.0）
- 🌐 **WebSocket 多人同步**：多人实时编辑同一矢量项目，操作毫秒级同步
- ✏️ **OT 冲突解决**：基于操作变换算法，无冲突并发编辑路径、颜色、图层
- 👤 **在线状态管理**：显示协作者光标位置、选区范围、操作历史
- 📴 **离线编辑支持**：断网时本地缓存操作，恢复后自动合并同步

### 🎬 矢量动画（v2.0）
- 🎞️ **SVG SMIL 动画**：路径变形、颜色过渡、位移动画原生 SVG 输出
- 📱 **Lottie 导出**：After Effects 兼容的 Lottie JSON 格式，支持移动端动画
- 🖼️ **GIF 动画导出**：帧率控制、调色板优化、循环设置
- 💻 **CSS 动画生成**：输出可直接用于网页的关键帧 CSS 代码

### 🧩 智能工作流（v2.0）
- 🧱 **可视化节点编辑器**：拖拽式构建批处理工作流，输入 → 预处理 → 矢量化 → 后处理 → 导出
- 📋 **内置节点库**：输入、预处理、矢量化、后处理、导出、条件分支、循环节点
- ⚡ **并行执行引擎**：WorkflowEngine 支持并行节点执行、错误回滚、进度追踪
- 📂 **工作流模板**：Logo 批量处理、照片转插画、扫描件归档等一键套用模板

### 🔄 跨设备同步（v2.0）
- 💻 **桌面端 ↔ 网页端 ↔ API 服务端**：项目文件、预设、插件、工作区状态实时同步
- 🌉 **同步桥接器**：自动处理不同平台间的数据格式转换和冲突合并
- 📴 **离线操作队列**：网络恢复后自动同步离线期间的所有操作
- 🔐 **云端账号体系**：邮箱/第三方登录，JWT 安全令牌管理

### 🛒 付费市场（v2.0）
- 💰 **积分系统**：按 API 调用、高级功能、云存储使用量计费
- 🛍️ **付费插件/预设市场**：支持购买、订阅、试用、退款
- 📦 **订阅分级**：免费版 / Pro 版 / 团队版，按需解锁功能
- 💳 **账号管理**：`vector-studio account` 子命令管理登录、积分、订阅
- 🌐 **在线预设分享**：基于 GitHub Gist / Repo 后端，浏览、搜索、安装社区预设
- ⬆️ **一键发布**：将本地预设发布到市场，生成可分享的预设 ID
- ⭐ **本地评分**：为预设打分，热门预设按评分和下载量排序
- 🔧 **自定义源**：通过配置文件添加私有或团队预设源

### 🤖 AI 生成式矢量创作（v3.0）
- 🎨 **文本生成矢量**：输入自然语言描述，AI 生成对应风格的矢量风格图片（flat/line/gradient/3d/sketch）
- 🖼️ **图生图风格迁移**：基于参考图生成新矢量风格图，支持风格编码器提取14维风格特征
- 🎯 **专用生成器**：图标生成器（`generate_icon`）、Logo生成器（`generate_logo`）、插画生成器（`generate_illustration`）
- 🧠 **纯Pillow扩散模拟**：零PyTorch/TensorFlow依赖，使用NumPy+Pillow模拟扩散过程

### 🌐 云端渲染农场（v3.0）
- 🖥️ **分布式Worker节点**：轻量级HTTP Worker服务，支持多机并行渲染
- ⚖️ **智能负载均衡**：按 load/capacity 比率自动分配任务到最优Worker
- 📦 **批量任务分片**：`DistributedBatch` 将大批量任务自动分片分发到多个Worker
- 💓 **心跳监控**：自动检测失联节点，任务自动重新分配
- 🔌 **API集成**：FastAPI新增 `/farm/submit`、`/farm/status`、`/farm/workers` 等端点

### 🎨 设计系统集成（v3.0）
- 🖌️ **Figma集成**：SVG导出到Figma文件、从Figma导入设计、设计令牌同步
- 📝 **Sketch集成**：读写Sketch文档（ZIP格式），图层导入导出
- 🎨 **设计令牌提取**：从SVG自动提取颜色、字体、间距等设计令牌，导出JSON

### 🧊 3D矢量与AR预览（v3.0）
- 🔲 **SVG挤出3D**：`extrude` 将2D SVG挤出为3D效果，`rotate` 3D旋转，`perspective` 透视变换
- 💡 **光照效果**：`add_lighting` 为SVG添加定向光照
- 📱 **AR预览**：生成AR标记、创建AR叠加配置、导出USDZ格式（iOS AR）
- 🧮 **纯Python 3D数学**：4×4旋转/透视矩阵，投影为SVG 2D变换，零3D库依赖

### 🏢 企业级权限管理（v3.0）
- 👥 **团队工作区**：`TeamWorkspace` 支持成员增删、角色变更、权限查询
- 🔐 **RBAC角色权限**：admin/editor/viewer/guest四级角色，细粒度权限控制
- 📝 **审计日志**：`RolePermissions` 记录所有操作，支持按用户过滤查询
- 🔑 **SSO集成**：支持Google/GitHub/SAML/LDAP四种单点登录提供商

### 🛍️ 智能模板市场（v3.0）
- 📋 **模板发现与推荐**：`TemplateMarket` 支持关键词/类别过滤，AI启发式推荐引擎
- 🎨 **模板应用**：一键将模板应用到输入图片，自动累加下载计数
- ⭐ **评分系统**：1-5星评分，自动计算平均分并持久化
- 🏗️ **模板编辑器**：`TemplateEditor` 提供加载、编辑、预览、保存完整工作流
- 📤 **发布与分享**：`publish_template` 将本地模板发布到市场

### 🖥️ GUI 界面
- 🔄 并排对比 + 叠加对比滑块模式
- 📂 预设分组选择器（内置预设 + 用户自定义预设）
- 🕐 最近任务历史面板，一键复用参数
- 📐 SVG 结构分析（图层列表、颜色面板）
- 📁 参数分组折叠面板（核心 / 高级 / 预处理 / 导出）

### 💾 预设管理
- 💾 保存当前参数为用户自定义预设
- 🗑️ 删除不再需要的用户预设
- 📤 导出预设为 JSON 文件，便于备份和分享
- 📥 导入预设 JSON 文件，快速迁移配置

### 📜 历史记录
- 📝 自动记录每次转换任务的参数和结果
- 🔄 从历史任务中一键加载参数到当前面板
- 📊 导出历史报告为 CSV 或 Markdown 表格
- 🧹 支持清空历史记录

### 🔗 外部编辑器
- 🚀 一键在系统默认编辑器中打开 SVG
- 🎨 支持 Adobe Illustrator、Inkscape、Affinity Designer
- 🖌️ 支持 Figma、CorelDRAW、Vectr、Boxy SVG
- 🔍 自动检测已安装的外部编辑器

### 📤 导出格式
- SVG：原生矢量输出
- PDF：通过 CairoSVG 转换
- PNG：预览图导出
- EPS：通过 Inkscape CLI 导出

---

## 📦 安装

### 桌面版下载（Tauri）

| 平台 | 下载 | 说明 |
|---|---|---|
| Windows | [MSI 安装包](https://github.com/jammyfu/bitmap-vector-studio/releases/latest) | Windows 10+，x64 |
| macOS | [DMG 镜像](https://github.com/jammyfu/bitmap-vector-studio/releases/latest) | macOS 10.13+，Intel / Apple Silicon |
| Linux | [AppImage](https://github.com/jammyfu/bitmap-vector-studio/releases/latest) | 多数发行版通用，x64 |

> 桌面版支持自动更新，启动时会自动检测新版本并提示安装。

### 一键安装（命令行 / Python 包，推荐）

```bash
curl -fsSL https://raw.githubusercontent.com/jammyfu/bitmap-vector-studio/main/scripts/install.sh | bash
```

支持 macOS、Linux 和 Windows (Git Bash)。安装完成后可直接使用 `vector-studio` 命令。

### 手动安装

#### 系统要求

| 项目 | 要求 |
|---|---|
| Python | 3.9 或更高版本 |
| 操作系统 | Windows 10+ / macOS 11+ / Linux |
| 内存 | 建议 4GB+（处理高分辨率图片） |
| 磁盘 | 约 100MB 安装空间 |

#### 桌面版系统要求

| 平台 | 最低要求 | 推荐配置 |
|---|---|---|
| Windows | Windows 10 1809+，4GB 内存 | Windows 11，8GB 内存，SSD |
| macOS | macOS 10.13+，4GB 内存 | macOS 14+，8GB 内存，Apple Silicon |
| Linux | 内核 3.10+，glibc 2.17+，4GB 内存 | 主流发行版最新版，8GB 内存，SSD |

> 桌面版依赖本地 Python 环境（`python3` 需在 PATH 中）。首次启动时会自动检测并提示安装 `vector-studio` Python 包。

#### 快速安装

```bash
# 克隆仓库
git clone https://github.com/jammyfu/bitmap-vector-studio.git
cd bitmap-vector-studio

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# 安装依赖
pip install -U pip
pip install -e .
```

### 平台差异说明

**Windows**
- 推荐使用 PowerShell 或 Git Bash
- 若遇到执行策略限制，先运行 `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
- Inkscape 安装后需确保 `inkscape.exe` 在 PATH 中（用于 EPS 导出）

**macOS**
- 需要 Xcode Command Line Tools（`xcode-select --install`）
- 若使用 Homebrew 安装的 Python，确保 `pip` 指向正确的环境
- 部分编辑器（如 Illustrator）需通过 `open -a` 方式启动

**Linux**
- 需要 `xdg-open` 用于打开外部编辑器（通常已预装）
- 推荐通过包管理器安装 Inkscape：`sudo apt install inkscape`
- 若使用 Flatpak/Snap 安装的 Inkscape，会自动检测

### 桌面版安装说明

**Windows**
1. 从 [Releases](https://github.com/jammyfu/bitmap-vector-studio/releases/latest) 下载 `.msi` 安装包
2. 双击运行安装向导
3. 安装完成后从开始菜单启动「Bitmap Vector Studio」
4. 首次启动会自动检测 Python 环境并提示安装依赖

**macOS**
1. 从 [Releases](https://github.com/jammyfu/bitmap-vector-studio/releases/latest) 下载 `.dmg` 镜像
2. 双击挂载 DMG，将应用拖入「应用程序」文件夹
3. 首次启动若提示「无法打开」，请前往「系统设置 → 隐私与安全性」允许
4. 应用会自动检查更新并在有新版本时提示

**Linux**
1. 从 [Releases](https://github.com/jammyfu/bitmap-vector-studio/releases/latest) 下载 `.AppImage` 文件
2. 赋予执行权限：`chmod +x bitmap-vector-studio_*.AppImage`
3. 直接运行：`./bitmap-vector-studio_*.AppImage`
4. 可选：使用 [AppImageLauncher](https://github.com/TheAssassin/AppImageLauncher) 集成到系统菜单

> **注意**：桌面版依赖本地 Python 环境（`python3` 需在 PATH 中）。首次启动时会自动检测并提示安装 `vector-studio` Python 包。
> 
> 详细安装指南、快捷键列表、故障排查请参阅 [docs/DESKTOP.md](docs/DESKTOP.md)。

### 可选依赖

```bash
# 开发依赖（测试 + 代码风格检查）
pip install -e ".[dev]"

# 智能分析增强（推荐安装，用于智能预设推荐和背景透明）
pip install -e ".[smart]"

# API 服务依赖（FastAPI + Uvicorn）
pip install -e ".[api]"

# AI 与 OCR 增强（语义简化、文字识别）
pip install -e ".[ai]"

# 若需 EPS 导出，请安装 Inkscape（系统级）
# https://inkscape.org/release/
```

---

## 🚀 快速开始

### 方式一：桌面应用（推荐）

从 [GitHub Releases](https://github.com/jammyfu/bitmap-vector-studio/releases/latest) 下载对应平台的安装包：

| 平台 | 安装包 | 说明 |
|---|---|---|
| Windows | `.msi` 或 `.exe` | Windows 10+，x64 |
| macOS | `.dmg` | macOS 10.13+，Intel / Apple Silicon |
| Linux | `.AppImage` | 多数发行版通用，x64 |

安装完成后启动应用：
1. 拖拽图片到左侧队列（或按 `Ctrl+O` 选择文件）
2. 在右侧参数面板选择预设（`poster` 或 `logo` 适合大多数场景）
3. 调整参数（可选），实时预览自动更新
4. 点击「开始转换」或 `Ctrl+T`
5. 导出 SVG 或在外部编辑器中打开

![Desktop Preview](docs/desktop-preview.png)

> 桌面版支持自动更新，启动时会自动检测新版本并提示安装。详见 [docs/DESKTOP.md](docs/DESKTOP.md)。

### 方式二：Streamlit 网页 GUI

```bash
streamlit run app.py
```

打开浏览器后：
1. 上传图片（支持拖拽）
2. 选择预设（`poster` 或 `logo` 适合大多数场景）
3. 调整参数（可选）
4. 点击「开始转换」
5. 下载 SVG 或在外部编辑器中打开

![GUI Preview](docs/gui-preview.png)

### 方式三：CLI 单图转换

```bash
# 使用预设快速转换
vector-studio trace examples/input.png --output outputs/input.svg --preset poster

# 高保真照片
vector-studio trace photo.jpg --output outputs/photo.svg --preset photo --export-pdf

# Logo / 图标（精细调参）
vector-studio trace logo.png --output outputs/logo.svg --preset logo --color-precision 7 --filter-speckle 2

# 像素艺术
vector-studio trace pixel.png --output outputs/pixel.svg --preset pixel_art

# 转换后自动打开外部编辑器
vector-studio trace design.png --preset logo --open inkscape
```

### 方式四：CLI 批量转换

```bash
# 批量转换整个文件夹
vector-studio batch ./inputs ./outputs --preset poster

# 递归扫描子文件夹
vector-studio batch ./inputs ./outputs --preset poster --recursive

# 覆盖已存在的输出文件
vector-studio batch ./inputs ./outputs --preset logo --overwrite

# 批量导出 PDF
vector-studio batch ./inputs ./outputs --preset photo --export-pdf
```

### 方式五：Web API 服务

```bash
# 启动 API 服务
vector-studio api --host 0.0.0.0 --port 8000

# 或使用 Docker
docker run -p 8000:8000 jammyfu/bitmap-vector-studio
```

API 启动后，可通过 HTTP 请求进行转换：

```bash
# 同步转换
curl -X POST "http://localhost:8000/convert" \
  -F "file=@logo.png" \
  -F "preset=logo" \
  --output logo.svg

# 异步转换
curl -X POST "http://localhost:8000/convert/async" \
  -F "file=@photo.jpg" \
  -F "preset=photo"
```

详见 [docs/API.md](docs/API.md)。

### 方式六：Docker 部署

```bash
# 拉取镜像
docker pull jammyfu/bitmap-vector-studio

# 运行 API 服务
docker run -d -p 8000:8000 --name vs-api jammyfu/bitmap-vector-studio

# 运行 CLI 交互模式
docker run -it --rm \
  -v $(pwd)/inputs:/app/inputs \
  -v $(pwd)/outputs:/app/outputs \
  jammyfu/bitmap-vector-studio:cli
```

详见 [docs/DOCKER.md](docs/DOCKER.md)。

### 方式七：v0.5 AI 与实时交互（CLI）

```bash
# 实时预览（CLI 快速模式）
vector-studio trace input.png --live-preview

# 局部重描摹（矩形选区）
vector-studio trace input.png --region 100,100,200,200

# AI 语义简化（自适应策略）
vector-studio trace photo.jpg --ai-simplify --simplify-type photo

# AI 语义简化（草图风格）
vector-studio trace sketch.jpg --ai-simplify --simplify-type sketch

# OCR 文字保留（扫描件）
vector-studio trace scan.png --ai-ocr

# 组合使用：简化 + OCR
vector-studio trace poster.jpg --ai-simplify --ai-ocr --preset poster

# 预设市场
vector-studio market search logo
vector-studio market install preset-id
vector-studio market publish my_preset --token ghp_xxx
```

### 方式八：v1.1 性能优化与 OCR 多语言（CLI）

```bash
# GPU 加速转换（自动检测 CUDA/Metal/OpenCL）
vector-studio trace photo.jpg --gpu --preset photo

# 大文件流式处理（避免内存溢出）
vector-studio trace large_image.tif --stream --max-input-side 4000

# 性能基准测试
vector-studio benchmark --gpu --iterations 10

# OCR 多语言识别（中文 + 英文混合）
vector-studio trace scan.png --ai-ocr --lang chi_sim+eng

# 竖排文字检测（日文竖排）
vector-studio ocr vertical japanese.png --lang jpn

# 保存工作区（包含文件队列和参数）
vector-studio workspace save project_a

# 断点续传：恢复崩溃前的批量任务
vector-studio resume checkpoint-id

# 插件热重载（开发时自动加载新插件）
vector-studio trace input.png --plugin my_plugin --hot-reload
```

详见 [docs/AI.md](docs/AI.md) 和 [docs/MARKET.md](docs/MARKET.md)。

### 方式九：v3.0 AI 生成与设计集成（CLI）

```bash
# AI文本生成矢量图
vector-studio generate text "a cute cat" --style flat --output cat.png

# AI图生图风格迁移
vector-studio generate image input.png --prompt "convert to line art" --output line_art.png

# AI生成图标
vector-studio generate icon "settings gear" --style minimal --output gear.svg

# AI生成Logo
vector-studio generate logo "tech company" --style modern --output logo.svg

# AI生成插画
vector-studio generate illustration "forest scene" --style watercolor --output forest.svg

# 渲染农场：查看状态
vector-studio render-farm status

# 渲染农场：提交单文件
vector-studio render-farm submit large_image.png --preset photo

# 渲染农场：批量分布式转换
vector-studio render-farm batch ./inputs --preset poster --workers 4

# 渲染农场：启动Worker节点
vector-studio render-farm worker --host 0.0.0.0 --port 9001

# Figma集成：导出SVG到Figma
vector-studio design figma-export design.svg --file-key abc123 --node-id 456

# Figma集成：从Figma导入
vector-studio design figma-import --file-key abc123 --node-id 456

# Sketch集成：导出到Sketch文档
vector-studio design sketch-export design.svg --document ./project.sketch

# 提取设计令牌
vector-studio design tokens-extract design.svg --output tokens.json

# 3D挤出效果
vector-studio 3d extrude design.svg --depth 10 --output design_3d.svg

# 3D旋转
vector-studio 3d rotate design.svg --axis y --angle 45 --output rotated.svg

# AR预览生成
vector-studio 3d ar-preview design.svg --output ar_config.json

# 企业：创建团队
vector-studio enterprise team create "Design Team"

# 企业：添加成员
vector-studio enterprise team add-member user@example.com --role editor

# 企业：查看审计日志
vector-studio enterprise audit-log --user user@example.com

# 企业：配置SSO
vector-studio enterprise sso-configure --provider google

# 模板市场：列出模板
vector-studio template list --category logo

# 模板市场：AI推荐
vector-studio template recommend --image-type photo

# 模板市场：应用模板
vector-studio template apply template_123 --input photo.jpg --output result.svg

# 模板市场：发布模板
vector-studio template publish my_template.json --user myuser
```

详见 [docs/V3.md](docs/V3.md)。

---

## 🖥️ GUI 使用指南

### 桌面应用界面

桌面应用采用三栏布局：左侧文件队列、中间预览画布、右侧参数面板。

**左栏：文件队列**
- 拖拽图片到队列区域加入待处理列表
- 支持多文件拖拽（1-50个文件）
- 显示转换进度和状态（等待中/转换中/已完成/失败）
- 支持删除、重新排序、一键导出全部

**中栏：预览画布**
- 并排对比：左侧原图，右侧 SVG 结果，同步缩放
- 叠加对比：拖动滑块查看原图与矢量化结果的差异
- 实时预览：参数调整 600ms 防抖后自动更新（可暂停）
- 缩放控制：鼠标滚轮缩放，双击重置，支持 25% - 400%

**右栏：参数面板**
- 转换预设、核心参数、高级参数、预处理、智能功能、AI 辅助、导出选项
- 最近任务历史，一键加载参数

详见 [docs/DESKTOP.md](docs/DESKTOP.md)。

### Streamlit 网页 GUI 侧边栏

| 区域 | 功能 |
|---|---|
| **转换预设** | 选择内置或用户预设，保存/删除自定义预设 |
| **核心参数** | 颜色模式、分层方式、曲线拟合、滤斑点、颜色精度等 |
| **高级参数** | 最大迭代次数等进阶选项 |
| **预处理** | 降噪、限制输入边长、Posterize 颜色量化 |
| **智能功能** | 背景透明、图像增强、预设推荐（v0.3） |
| **AI 辅助** | 实时预览、AI 语义简化、OCR 文字识别、局部重描摹（v0.5） |
| **导出选项** | 压缩 SVG、导出 PDF/PNG、优化级别、质量评分（v0.3） |
| **最近任务** | 查看历史任务，一键加载参数 |

### 预览模式

- **并排对比**：左侧原图，右侧 SVG 预览，同步缩放
- **叠加对比**：拖动滑块或点击画面查看原图与矢量化结果的差异

### SVG 结构分析

转换完成后展开「SVG 结构」面板，可查看：
- 路径数、多边形数、矩形数、圆形数
- 组数、viewBox 信息
- 文件大小
- 图层列表（按 `<g>` 元素提取，带颜色预览）

---

## ⌨️ CLI 完整参考

### 命令列表

| 命令 | 说明 |
|---|---|
| `vector-studio presets` | 查看所有内置预设 |
| `vector-studio trace` | 单张图片转换 |
| `vector-studio batch` | 批量转换文件夹 |
| `vector-studio search` | **v0.3** 参数搜索，自动找最优参数 |
| `vector-studio queue add` | **v0.3** 添加任务到队列 |
| `vector-studio queue status` | **v0.3** 查看队列状态 |
| `vector-studio queue start` | **v0.3** 启动队列处理 |
| `vector-studio queue report` | **v0.3** 导出队列报告 |
| `vector-studio config get` | **v0.4** 查看配置项 |
| `vector-studio config set` | **v0.4** 设置配置项 |
| `vector-studio config list` | **v0.4** 列出所有配置 |
| `vector-studio config reset` | **v0.4** 重置配置 |
| `vector-studio plugin list` | **v0.4** 列出所有插件 |
| `vector-studio plugin enable` | **v0.4** 启用插件 |
| `vector-studio plugin disable` | **v0.4** 禁用插件 |
| `vector-studio plugin install` | **v0.4** 安装插件 |
| `vector-studio plugin validate` | **v1.2** 验证插件结构和签名 |
| `vector-studio plugin test` | **v1.2** 运行插件测试 |
| `vector-studio plugin scaffold` | **v1.2** 生成插件脚手架模板 |
| `vector-studio plugin docs` | **v1.2** 生成插件文档 |
| `vector-studio api` | **v0.4** 启动 API 服务 |
| `vector-studio market list` | **v0.5** 列出市场预设 |
| `vector-studio market search` | **v0.5** 搜索市场预设 |
| `vector-studio market install` | **v0.5** 安装市场预设 |
| `vector-studio market publish` | **v0.5** 发布本地预设 |
| `vector-studio market popular` | **v0.5** 查看热门预设 |
| `vector-studio market info` | **v0.5** 查看预设详情 |
| `vector-studio benchmark` | **v1.1** 性能基准测试，检测 GPU/CPU 性能 |
| `vector-studio resume` | **v1.1** 恢复断点续传的批量任务 |
| `vector-studio workspace save` | **v1.1** 保存当前工作区 |
| `vector-studio workspace load` | **v1.1** 加载工作区 |
| `vector-studio workspace list` | **v1.1** 列出所有保存的工作区 |
| `vector-studio ocr` | **v1.1** OCR 子命令：识别、语言检测、竖排文字 |
| `vector-studio engine` | **v1.2** 引擎管理：列出、选择、基准测试 |
| `vector-studio cloud` | **v1.2** 云端分享：分享、列出、撤销、QR码 |
| `vector-studio validate` | **v1.2** 验证工具：验证预设/插件 |
| `vector-studio contrib` | **v1.2** 社区工具：生成贡献指南 |
| `vector-studio ai segment` | **v2.0** AI 语义分割 |
| `vector-studio ai style` | **v2.0** AI 风格迁移 |
| `vector-studio ai superres` | **v2.0** AI 超分辨率 |
| `vector-studio animate export` | **v2.0** 导出矢量动画 |
| `vector-studio animate preview` | **v2.0** 预览动画效果 |
| `vector-studio collab create` | **v2.0** 创建协作会话 |
| `vector-studio collab join` | **v2.0** 加入协作会话 |
| `vector-studio workflow create` | **v2.0** 创建工作流 |
| `vector-studio workflow run` | **v2.0** 执行工作流 |
| `vector-studio workflow list` | **v2.0** 列出工作流模板 |
| `vector-studio sync push` | **v2.0** 推送状态到云端 |
| `vector-studio sync pull` | **v2.0** 从云端拉取状态 |
| `vector-studio account login` | **v2.0** 登录云端账号 |
| `vector-studio account status` | **v2.0** 查看账号状态 |
| `vector-studio account credits` | **v2.0** 查看积分余额 |
| `vector-studio account upgrade` | **v2.0** 升级订阅计划 |
| `vector-studio generate text` | **v3.0** AI文本生成矢量图 |
| `vector-studio generate image` | **v3.0** AI图生图风格迁移 |
| `vector-studio generate icon` | **v3.0** AI生成图标 |
| `vector-studio generate logo` | **v3.0** AI生成Logo |
| `vector-studio generate illustration` | **v3.0** AI生成插画 |
| `vector-studio render-farm status` | **v3.0** 查看渲染农场状态 |
| `vector-studio render-farm submit` | **v3.0** 提交任务到渲染农场 |
| `vector-studio render-farm batch` | **v3.0** 批量分布式转换 |
| `vector-studio render-farm worker` | **v3.0** 启动Worker节点 |
| `vector-studio design figma-export` | **v3.0** 导出SVG到Figma |
| `vector-studio design figma-import` | **v3.0** 从Figma导入设计 |
| `vector-studio design sketch-export` | **v3.0** 导出SVG到Sketch |
| `vector-studio design tokens-extract` | **v3.0** 提取设计令牌 |
| `vector-studio 3d extrude` | **v3.0** SVG挤出3D效果 |
| `vector-studio 3d rotate` | **v3.0** SVG 3D旋转 |
| `vector-studio 3d ar-preview` | **v3.0** AR预览生成 |
| `vector-studio enterprise team create` | **v3.0** 创建团队工作区 |
| `vector-studio enterprise team add-member` | **v3.0** 添加团队成员 |
| `vector-studio enterprise audit-log` | **v3.0** 查看审计日志 |
| `vector-studio enterprise sso-configure` | **v3.0** 配置SSO |
| `vector-studio template list` | **v3.0** 列出模板 |
| `vector-studio template recommend` | **v3.0** AI推荐模板 |
| `vector-studio template apply` | **v3.0** 应用模板 |
| `vector-studio template publish` | **v3.0** 发布模板 |

### `trace` 命令选项

| 选项 | 简写 | 类型 | 默认值 | 说明 |
|---|---|---|---|---|
| `--output` | `-o` | Path | 同目录 `.svg` | 输出 SVG 路径 |
| `--preset` | `-p` | str | `poster` | 预设名称 |
| `--colormode` | | str | | `color` 或 `binary` |
| `--hierarchical` | | str | | `stacked` 或 `cutout` |
| `--mode` | | str | | `spline`, `polygon`, `pixel`, `none` |
| `--filter-speckle` | | int (0-128) | | 滤斑点强度 |
| `--color-precision` | | int (1-8) | | 颜色精度 |
| `--layer-difference` | | int (0-255) | | 梯度层级间隔 |
| `--corner-threshold` | | int (0-180) | | 角点识别阈值 |
| `--length-threshold` | | float (3.5-10.0) | | 曲线段长 |
| `--max-iterations` | | int (1-50) | | 最大迭代次数 |
| `--splice-threshold` | | int (0-180) | | 拼接阈值 |
| `--path-precision` | | int (0-12) | | 路径小数位 |
| `--denoise` / `--no-denoise` | | bool | | 是否降噪 |
| `--posterize` | | int (1-8) | | Posterize 位数 |
| `--max-input-side` | | int (≥64) | | 限制输入最大边长 |
| `--optimize` / `--no-optimize` | | bool | `True` | 压缩清理 SVG |
| `--optimize-level` | | str | `basic` | **v0.3** `none` / `basic` / `comprehensive` / `aggressive` |
| `--score` | | bool | `False` | **v0.3** 输出质量评分 |
| `--name-layers` | | bool | `False` | 为图层添加语义化名称 |
| `--export-pdf` | | bool | `False` | 同时导出 PDF |
| `--export-png` | | bool | `False` | 同时导出 PNG 预览 |
| `--export-eps` | | bool | `False` | 同时导出 EPS（需 Inkscape） |
| `--open` | | str | | 转换后在指定编辑器中打开 |
| `--smart-remove-bg` | | bool | `False` | **v0.3** 自动检测并移除背景 |
| `--enhance` | | str | | **v0.3** 增强类型：`scan` / `photo` / `logo` / `auto` |
| `--recommend` | | bool | `False` | **v0.3** 仅分析并推荐预设，不转换 |
| `--live-preview` | | bool | `False` | **v0.5** 实时预览模式，快速低分辨率输出 |
| `--region` | | str | | **v0.5** 局部重描摹区域，格式 `x,y,w,h` |
| `--ai-simplify` | | bool | `False` | **v0.5** AI 语义简化预处理 |
| `--ai-ocr` | | bool | `False` | **v0.5** OCR 文字检测并嵌入 SVG `<text>` |
| `--simplify-type` | | str | `auto` | **v0.5** 简化策略：`photo` / `complex` / `sketch` / `auto` |
| `--config` | | Path | | **v0.4** 指定配置文件路径 |
| `--plugin` | | str | | **v0.4** 启用指定插件（可多次使用） |
| `--gpu` | | bool | `False` | **v1.1** 优先使用 GPU 加速（CUDA/Metal/OpenCL） |
| `--stream` | | bool | `False` | **v1.1** 大文件流式处理，分块读取 |
| `--workspace` | | str | | **v1.1** 指定工作区名称，自动保存/恢复状态 |
| `--engine` | | str | `auto` | **v1.2** 矢量化引擎：`vtracer` / `potrace` / `autotrace` / `auto` |
| `--ai-segment` | | bool | `False` | **v2.0** AI 语义分割预处理 |
| `--ai-style` | | str | | **v2.0** AI 风格迁移风格名 |
| `--ai-superres` | | bool | `False` | **v2.0** AI 超分辨率预处理 |
| `--animate` | | str | | **v2.0** 导出动画类型：`smil` / `lottie` / `gif` / `css` |
| `--collab-session` | | str | | **v2.0** 加入协作会话 ID |

### `batch` 命令选项

| 选项 | 简写 | 类型 | 默认值 | 说明 |
|---|---|---|---|---|
| `--preset` | `-p` | str | `poster` | 预设名称 |
| `--recursive` | `-r` | bool | `False` | 递归扫描子文件夹 |
| `--overwrite` | | bool | `False` | 覆盖已存在的 SVG |
| `--name-layers` | | bool | `False` | 为图层添加语义化名称 |
| `--export-pdf` | | bool | `False` | 同时导出 PDF |
| `--export-png` | | bool | `False` | 同时导出 PNG 预览 |
| `--open` | | bool | `False` | 转换后在默认编辑器中打开 |
| `--optimize-level` | | str | `basic` | **v0.3** 优化级别 |
| `--score` | | bool | `False` | **v0.3** 输出质量评分 |
| `--workers` | `-w` | int | `1` | **v0.3** 并发工作线程数（1-16） |
| `--retry` | | int | `0` | **v0.3** 失败重试次数（0-5） |
| `--config` | | Path | | **v0.4** 指定配置文件路径 |
| `--plugin` | | str | | **v0.4** 启用指定插件 |

### `search` 命令选项（v0.3）

| 选项 | 简写 | 类型 | 默认值 | 说明 |
|---|---|---|---|---|
| `--output-dir` | `-o` | Path | 必填 | 搜索结果输出目录 |
| `--max` | `-m` | int | `20` | 最大参数组合数（1-100） |
| `--quick` | | bool | `False` | 仅搜索预设，不展开参数网格 |

### `queue` 子命令（v0.3）

| 子命令 | 说明 |
|---|---|
| `queue add <file>` | 添加单张图片到队列并立即处理 |
| `queue status` | 查看队列状态 |
| `queue start` | 启动队列（`add` 已自动处理） |
| `queue report --path <csv>` | 导出队列任务报告 |

### `config` 子命令（v0.4）

| 子命令 | 说明 | 示例 |
|---|---|---|
| `config get <key>` | 查看指定配置项 | `vector-studio config get default_preset` |
| `config set <key> <value>` | 设置配置项 | `vector-studio config set default_preset logo` |
| `config list` | 列出所有配置 | `vector-studio config list` |
| `config reset` | 重置为默认值 | `vector-studio config reset` |

### `plugin` 子命令（v0.4）

| 子命令 | 说明 | 示例 |
|---|---|---|
| `plugin list` | 列出所有插件 | `vector-studio plugin list` |
| `plugin enable <name>` | 启用插件 | `vector-studio plugin enable watermark` |
| `plugin disable <name>` | 禁用插件 | `vector-studio plugin disable resize` |
| `plugin install <path>` | 安装插件文件 | `vector-studio plugin install ./my_plugin.py` |

### `api` 子命令（v0.4）

| 选项 | 简写 | 类型 | 默认值 | 说明 |
|---|---|---|---|---|
| `--host` | | str | `127.0.0.1` | 绑定主机地址 |
| `--port` | | int | `8000` | 绑定端口 |
| `--workers` | `-w` | int | `4` | API 工作进程数 |

### `market` 子命令（v0.5）

| 子命令 | 说明 | 示例 |
|---|---|---|
| `market list` | 列出市场所有预设 | `vector-studio market list` |
| `market search <query>` | 搜索预设 | `vector-studio market search logo` |
| `market install <id>` | 安装指定预设 | `vector-studio market install abc123` |
| `market publish <name>` | 发布本地预设 | `vector-studio market publish my_preset --token ghp_xxx` |
| `market popular` | 查看热门预设 | `vector-studio market popular --limit 10` |
| `market info <id>` | 查看预设详情 | `vector-studio market info abc123` |

### `benchmark` 子命令（v1.1）

| 选项 | 简写 | 类型 | 默认值 | 说明 |
|---|---|---|---|---|
| `--gpu` | | bool | `False` | 测试 GPU 加速性能 |
| `--iterations` | `-n` | int | `5` | 测试迭代次数 |

```bash
# 基准测试当前设备性能
vector-studio benchmark

# 测试 GPU 加速
vector-studio benchmark --gpu
```

### `resume` 子命令（v1.1）

```bash
# 列出可恢复的任务
vector-studio resume list

# 恢复指定检查点的批量任务
vector-studio resume checkpoint-id

# 清除已完成的检查点
vector-studio resume clear
```

### `workspace` 子命令（v1.1）

| 子命令 | 说明 | 示例 |
|---|---|---|
| `workspace save <name>` | 保存当前工作区 | `vector-studio workspace save project_a` |
| `workspace load <name>` | 加载工作区 | `vector-studio workspace load project_a` |
| `workspace list` | 列出所有工作区 | `vector-studio workspace list` |
| `workspace delete <name>` | 删除工作区 | `vector-studio workspace delete project_a` |

### `ocr` 子命令（v1.1）

| 子命令 | 说明 | 示例 |
|---|---|---|
| `ocr detect <image>` | 检测文字区域 | `vector-studio ocr detect scan.png` |
| `ocr recognize <image>` | 识别文字内容 | `vector-studio ocr recognize scan.png --lang chi_sim+eng` |
| `ocr languages` | 列出支持的语言 | `vector-studio ocr languages` |
| `ocr vertical <image>` | 检测竖排文字 | `vector-studio ocr vertical japanese.png --lang jpn` |

### `engine` 子命令（v1.2）

| 子命令 | 说明 | 示例 |
|---|---|---|
| `engine list` | 列出所有可用引擎 | `vector-studio engine list` |
| `engine benchmark` | 运行引擎基准测试 | `vector-studio engine benchmark --iterations 5` |
| `engine select <engine>` | 设置默认引擎 | `vector-studio engine select potrace` |

```bash
# 列出引擎
vector-studio engine list

# 基准测试
vector-studio engine benchmark

# 使用指定引擎转换
vector-studio trace logo.png --engine potrace --preset bw
```

### `cloud` 子命令（v1.2）

| 子命令 | 说明 | 示例 |
|---|---|---|
| `cloud share <file>` | 分享文件到云端 | `vector-studio cloud share result.svg` |
| `cloud list` | 列出已分享内容 | `vector-studio cloud list` |
| `cloud revoke <id>` | 撤销分享 | `vector-studio cloud revoke gist-id` |
| `cloud qr <url>` | 生成分享链接 QR 码 | `vector-studio cloud qr https://gist.github.com/...` |

```bash
# 分享转换结果
vector-studio cloud share output.svg

# 生成 QR 码
vector-studio cloud qr https://gist.github.com/xxx
```

### `validate` 子命令（v1.2）

| 子命令 | 说明 | 示例 |
|---|---|---|
| `validate preset <file>` | 验证预设 JSON | `vector-studio validate preset my_preset.json` |
| `validate plugin <file>` | 验证插件文件 | `vector-studio validate plugin my_plugin.py` |

### `contrib` 子命令（v1.2）

| 子命令 | 说明 | 示例 |
|---|---|---|
| `contrib guide` | 生成贡献指南 | `vector-studio contrib guide` |

---

## 🎯 预设参考

### 内置预设

| 预设 | 适用素材 | 目标效果 | 颜色模式 | 曲线模式 |
|---|---|---|---|---|
| `bw` | 黑白线稿、印章、签名、扫描图 | 少色、清晰、路径干净 | binary | spline |
| `poster` | 插画、海报、扁平图形 | 接近 Illustrator 的详细插画模式 | color | spline |
| `photo` | 照片、复杂彩色素材 | 更高颜色保真，但文件更大 | color | spline |
| `logo` | Logo、图标、UI 图形 | 形状少、边缘顺滑、后续可编辑 | color | spline |
| `pixel_art` | 像素画、游戏素材 | 保持像素风格，不强行平滑 | color | pixel |
| `scan` | 蓝图、历史扫描、手绘图 | 降噪、提高清晰度 | binary | spline |

### 自定义预设

除了 6 种内置预设，你可以通过 GUI 或 Python API 创建自己的预设：

**通过 GUI**：
1. 调整参数到满意效果
2. 在侧边栏「保存当前参数为预设」中输入名称和描述
3. 点击「保存」

**通过 Python API**：
```python
from vector_studio.models import TraceOptions
from vector_studio.preset_manager import save_preset

opts = TraceOptions(
    colormode="color",
    color_precision=5,
    filter_speckle=3,
    # ... 其他参数
)
save_preset("my_custom", opts, description="我的自定义预设")
```

**导入/导出预设**：
```python
from vector_studio.preset_manager import export_presets, import_presets

# 导出所有用户预设
export_presets(Path("my-presets.json"))

# 导入预设
import_presets(Path("my-presets.json"), overwrite=False)
```

---

## 🔧 参数详解

### 颜色与分层

| 参数 | 范围 | 默认值 | 说明与调参建议 |
|---|---|---|---|
| `colormode` | `color` / `binary` | `color` | `color` 保留彩色；`binary` 转为黑白/单色。线稿、扫描件用 `binary`。 |
| `hierarchical` | `stacked` / `cutout` | `stacked` | `stacked` 分层堆叠，更接近 Illustrator 的多层矢量；`cutout` 剪切模式，某些图形可减少重叠。 |
| `mode` | `spline` / `polygon` / `pixel` / `none` | `spline` | `spline` 平滑贝塞尔曲线（最常用）；`polygon` 多边形；`pixel` 像素风；`none` 不做曲线拟合。 |

### 颜色控制

| 参数 | 范围 | 默认值 | 说明与调参建议 |
|---|---|---|---|
| `color_precision` | 1 - 8 | 6 | 颜色精度，越高颜色越多、越准确，SVG 可能更大。照片建议 7-8，Logo 建议 5-7。 |
| `layer_difference` | 0 - 255 | 16 | 梯度分层间隔，越小层数越多、越细腻，SVG 可能更大。插画 16-24，照片 8-16。 |

### 路径质量

| 参数 | 范围 | 默认值 | 说明与调参建议 |
|---|---|---|---|
| `filter_speckle` | 0 - 128 | 4 | 过滤小色块/噪点，数值越大越干净，但可能丢失细节。扫描件建议 6-8，照片建议 2-4。 |
| `corner_threshold` | 0 - 180 | 60 | 角点识别阈值。越低越敏感，保留更多尖角；越高越平滑。技术图纸建议 50-55，插画 60-70。 |
| `length_threshold` | 3.5 - 10.0 | 4.0 | 曲线细分长度，越低越精细，路径数越多。追求精细用 3.5，追求简洁用 4.5-5.0。 |
| `splice_threshold` | 0 - 180 | 45 | 样条拼接阈值。影响曲线段的连接方式。一般保持默认即可。 |
| `path_precision` | 0 - 12 | 3 | SVG path 小数位数，越高越精确，文件越大。Web 用图建议 2-3，印刷用图建议 4-5。 |
| `max_iterations` | 1 - 50 | 10 | 最大迭代次数。复杂图像可适当提高。一般保持默认。 |

### 预处理

| 参数 | 范围 | 默认值 | 说明与调参建议 |
|---|---|---|---|
| `denoise` | True / False | False | 轻度降噪。扫描件、低质量图片建议开启。 |
| `posterize` | 1 - 8 | None | 颜色量化位数。提前减少颜色数量，可让矢量化结果更干净。插画可尝试 4-6。 |
| `max_input_side` | ≥64 | None | 限制输入最大边长。超大图片先缩放可显著提速，照片建议 2400。 |

### 智能与优化（v0.3）

| 参数 | 范围 | 默认值 | 说明与调参建议 |
|---|---|---|---|
| `smart_remove_bg` | True / False | False | 自动检测 Logo 背景色并移除。适合纯色背景的 Logo/图标。 |
| `enhance` | `scan` / `photo` / `logo` / `auto` | None | 图像增强类型。`scan` 去噪；`photo` 自适应对比度；`logo` 边缘增强；`auto` 自动判断。 |
| `optimize_level` | `none` / `basic` / `comprehensive` / `aggressive` | `basic` | SVG 优化深度。`basic` 保守清理；`comprehensive` 路径合并+颜色合并；`aggressive` 最大压缩。 |
| `score` | True / False | False | 转换后输出 SVG 质量评分（0-100）。 |

---

## 🔌 插件开发快速指南

Bitmap Vector Studio v0.4 引入了基于 Hook 的插件系统。你可以编写自定义插件来扩展转换流程。

### 最小插件示例

创建一个 `hello_plugin.py` 文件：

```python
from pathlib import Path
from typing import Any
from PIL import Image
from vector_studio.plugin_interface import Plugin

class HelloPlugin(Plugin):
    name = "hello"
    version = "2.0.0"
    description = "A minimal hello-world plugin."
    author = "Your Name"

    def on_convert_complete(self, result, options: dict[str, Any]) -> None:
        print(f"[HelloPlugin] Conversion complete: {result.svg_path}")
```

### 安装插件

```bash
# 复制到用户插件目录
mkdir -p ~/.bitmap_vector_studio/plugins
cp hello_plugin.py ~/.bitmap_vector_studio/plugins/

# 或通过 CLI 安装
vector-studio plugin install ./hello_plugin.py

# 启用插件
vector-studio plugin enable hello
```

### 使用插件转换

```bash
vector-studio trace input.png --plugin hello --preset poster
```

插件支持三种 Hook：
- `preprocess(image, options)`：在矢量化之前修改输入图片
- `postprocess(svg_path, options)`：在 SVG 优化后修改输出文件
- `on_convert_complete(result, options)`：在转换完成后执行副作用操作

详见 [docs/PLUGIN.md](docs/PLUGIN.md)。

---

## 🌐 API 使用

### 启动 API 服务

```bash
# 本地启动
vector-studio api --host 0.0.0.0 --port 8000

# Docker 启动
docker run -p 8000:8000 jammyfu/bitmap-vector-studio
```

### 端点列表

| 端点 | 方法 | 说明 |
|---|---|---|
| `/health` | GET | 健康检查 |
| `/presets` | GET | 列出所有预设 |
| `/convert` | POST | 同步转换，直接返回 SVG |
| `/convert/async` | POST | 异步转换，返回任务 ID |
| `/status/{task_id}` | GET | 查询异步任务状态 |
| `/download/{task_id}/{format}` | GET | 下载转换结果（svg/pdf/png） |
| `/recommend` | POST | 上传图片获取预设推荐 |
| `/batch` | POST | 批量异步转换 |

### Python 客户端示例

```python
from vector_studio.api_client import VectorStudioClient

client = VectorStudioClient("http://localhost:8000")

# 同步转换
svg_bytes = client.convert(Path("logo.png"), preset="logo")
Path("output.svg").write_bytes(svg_bytes)

# 异步转换
task_id = client.convert_async(Path("photo.jpg"), preset="photo")
status = client.get_status(task_id)

# 批量转换
task_ids = client.batch_convert([Path("a.png"), Path("b.png")], preset="poster")

# 健康检查
print(client.health())  # {'status': 'ok', 'version': '2.0.0'}
```

详见 [docs/API.md](docs/API.md)。

---

## 🐳 Docker 部署

### 使用 Docker Run

```bash
# 拉取镜像
docker pull jammyfu/bitmap-vector-studio

# 运行 API 服务
docker run -d -p 8000:8000 --name vs-api jammyfu/bitmap-vector-studio

# 运行 CLI 交互模式
docker run -it --rm \
  -v $(pwd)/inputs:/app/inputs \
  -v $(pwd)/outputs:/app/outputs \
  jammyfu/bitmap-vector-studio:cli \
  vector-studio trace /app/inputs/logo.png --preset logo
```

### 使用 Docker Compose

```bash
docker-compose up -d
```

`docker-compose.yml` 已包含 API 服务和 CLI 服务两种模式，支持数据卷挂载和环境变量配置。

详见 [docs/DOCKER.md](docs/DOCKER.md)。

### `animate` 子命令（v2.0）

| 子命令 | 说明 | 示例 |
|---|---|---|
| `animate export <svg>` | 导出矢量动画 | `vector-studio animate export logo.svg --format lottie` |
| `animate preview <svg>` | 预览动画效果 | `vector-studio animate preview logo.svg --format smil` |
| `animate list-presets` | 列出动画预设 | `vector-studio animate list-presets` |

### `collab` 子命令（v2.0）

| 子命令 | 说明 | 示例 |
|---|---|---|
| `collab create` | 创建协作会话 | `vector-studio collab create --name "Project A"` |
| `collab join <session>` | 加入协作会话 | `vector-studio collab join abc123` |
| `collab status` | 查看协作状态 | `vector-studio collab status` |

### `workflow` 子命令（v2.0）

| 子命令 | 说明 | 示例 |
|---|---|---|
| `workflow create` | 创建工作流 | `vector-studio workflow create --template logo_batch` |
| `workflow run <file>` | 执行工作流 | `vector-studio workflow run my_workflow.json` |
| `workflow list` | 列出模板 | `vector-studio workflow list` |
| `workflow export <name>` | 导出工作流 | `vector-studio workflow export my_workflow` |

### `sync` 子命令（v2.0）

| 子命令 | 说明 | 示例 |
|---|---|---|
| `sync push` | 推送状态到云端 | `vector-studio sync push` |
| `sync pull` | 从云端拉取状态 | `vector-studio sync pull` |
| `sync status` | 查看同步状态 | `vector-studio sync status` |

### `account` 子命令（v2.0）

| 子命令 | 说明 | 示例 |
|---|---|---|
| `account login` | 登录云端账号 | `vector-studio account login` |
| `account status` | 查看账号状态 | `vector-studio account status` |
| `account credits` | 查看积分余额 | `vector-studio account credits` |
| `account upgrade` | 升级订阅计划 | `vector-studio account upgrade --plan pro` |

---

## 🎨 外部编辑器

Bitmap Vector Studio 支持一键打开以下外部矢量编辑器：

| 编辑器 | Windows | macOS | Linux | 检测方式 |
|---|---|---|---|---|
| Adobe Illustrator | ✅ | ✅ | ❌ | 常见安装路径 + 注册表 |
| Inkscape | ✅ | ✅ | ✅ | 常见路径 + PATH + Snap/Flatpak |
| Affinity Designer | ✅ | ✅ | ❌ | 常见安装路径 |
| Figma | ✅ | ✅ | ✅ (figma-linux) | 常见安装路径 |
| CorelDRAW | ✅ | ❌ | ❌ | 常见安装路径 |
| Vectr | ✅ | ✅ | ❌ | 常见安装路径 |
| Boxy SVG | ✅ | ✅ | ❌ | 常见安装路径 |

### CLI 中使用

```bash
# 使用系统默认程序打开
vector-studio trace image.png --open

# 指定编辑器打开
vector-studio trace image.png --open inkscape
vector-studio trace image.png --open illustrator

# 批量转换后逐个打开
vector-studio batch ./in ./out --open
```

### GUI 中使用

转换完成后，在「外部编辑器」区域选择检测到的编辑器，点击「用外部编辑器打开 SVG」即可。

---

## 📁 项目结构

```text
bitmap-vector-studio/
├─ app.py                         # Streamlit GUI 主入口
├─ pyproject.toml                 # Python 包配置
├─ requirements.txt               # 依赖列表
├─ README.md                      # 项目说明（本文档）
├─ CHANGELOG.md                   # 版本更新日志
├─ CONTRIBUTING.md                # 贡献指南
├─ LICENSE                        # MIT 许可证
├─ Dockerfile                     # v0.4 多阶段 Docker 构建
├─ docker-compose.yml             # v0.4 Docker Compose 配置
├─ desktop/                       # v1.0 Tauri 桌面应用
│  ├─ src/                        # React 前端源码
│  ├─ src-tauri/                  # Rust 后端源码
│  │  ├─ Cargo.toml               # Rust 包配置
│  │  ├─ tauri.conf.json          # Tauri 应用配置
│  │  └─ src/                     # Rust 源码（Tauri Command）
│  ├─ dist/                       # 前端构建输出
│  ├─ package.json                # Node 包配置
│  └─ index.html                  # 前端入口
├─ src/vector_studio/
│  ├─ __init__.py                 # 包入口与公开 API
│  ├─ cli.py                      # Typer 命令行入口
│  ├─ models.py                   # 参数模型和校验（TraceOptions / TraceResult）
│  ├─ presets.py                  # 内置预设策略
│  ├─ preset_manager.py           # 用户自定义预设管理（保存/加载/导入/导出）
│  ├─ preprocess.py               # Pillow 图像预处理
│  ├─ tracer.py                   # VTracer 调用封装
│  ├─ svg_tools.py                # SVG 优化、统计、导出（PDF/PNG/EPS）
│  ├─ svg_optimizer.py            # v0.3 SVG 深度优化（路径合并、颜色合并、简化、评分）
│  ├─ smart_background.py        # v0.3 智能背景透明检测与移除
│  ├─ smart_recommend.py         # v0.3 智能预设推荐（图像特征分析）
│  ├─ enhance.py                 # v0.3 图像增强（边缘增强、去噪、自适应对比度）
│  ├─ param_search.py            # v0.3 多参数批量搜索与自动择优
│  ├─ task_queue.py              # v0.3 异步批量任务队列（并发、重试、进度）
│  ├─ history.py                  # 任务历史记录（JSONL 存储）
│  ├─ external_editors.py         # 外部编辑器检测和启动
│  ├─ plugin_interface.py         # v0.4 插件基类（Plugin）
│  ├─ plugins.py                  # v0.4 插件管理器（PluginManager）
│  ├─ builtin_plugins/            # v0.4 内置插件（水印、缩放）
│  ├─ config.py                   # v0.4 配置管理（Config）
│  ├─ api.py                      # v0.4 FastAPI RESTful API
│  ├─ api_client.py               # v0.4 Python 客户端 SDK
│  ├─ engine_manager.py           # v1.2 多引擎管理器（EngineManager）
│  ├─ vtracer_engine.py           # v1.2 VTracer 引擎封装
│  ├─ potrace_engine.py           # v1.2 Potrace 引擎封装
│  ├─ autotrace_engine.py         # v1.2 AutoTrace 引擎封装
│  ├─ engine_selector.py           # v1.2 自动引擎选择器
│  ├─ engine_benchmark.py          # v1.2 引擎基准测试
│  ├─ plugin_validator.py         # v1.2 插件验证器
│  ├─ plugin_scaffold.py           # v1.2 插件脚手架
│  ├─ plugin_debugger.py           # v1.2 插件调试器
│  ├─ plugin_docs_generator.py     # v1.2 插件文档生成器
│  ├─ cloud_sync.py                # v1.2 云端同步
│  ├─ cloud_backends.py            # v1.2 云端后端（Gist/LocalServer）
│  ├─ qr_generator.py              # v1.2 QR 码生成器
│  ├─ preset_validator.py          # v1.2 预设验证器
│  ├─ contrib_guide_generator.py   # v1.2 贡献指南生成器
│  ├─ release_notes_generator.py   # v1.2 发布说明生成器
│  ├─ performance.py              # v1.1 性能监控与内存优化（PerformanceMonitor）
│  ├─ streaming_processor.py      # v1.1 大文件流式分块处理（StreamingImageProcessor）
│  ├─ lazy_loader.py              # v1.1 延迟加载重型模块（LazyModuleLoader）
│  ├─ gpu_backend.py              # v1.1 GPU 加速后端检测（CUDA/Metal/OpenCL）
│  ├─ startup_optimizer.py        # v1.1 启动预热与性能分析（StartupOptimizer/Profiler）
│  ├─ plugin_watcher.py           # v1.1 插件文件监听热重载（PluginWatcher）
│  ├─ safe_reloader.py            # v1.1 安全插件重载器（SafePluginReloader）
│  ├─ checkpoint_manager.py       # v1.1 断点续传与批量任务持久化（CheckpointManager）
│  ├─ crash_recovery.py           # v1.1 崩溃恢复机制（CrashRecovery）
│  ├─ workspace_manager.py        # v1.1 工作区自动保存与管理（WorkspaceManager）
│  ├─ ocr_languages.py            # v1.1 OCR 多语言配置与语言包管理
│  ├─ ai_simplify.py              # v0.5 AI 语义简化（语义/超像素/卡通/自适应）
│  ├─ ai_ocr.py                   # v0.5 OCR 文字检测与 SVG 嵌入
│  ├─ live_preview.py             # v0.5 实时预览引擎（LRU+TTL 缓存）
│  ├─ region_trace.py             # v0.5 局部重描摹（矩形/圆形/多边形选区）
│  ├─ market.py                   # v0.5 预设市场（Gist/Repo 后端）
│  └─ release.py                  # v0.4 发布自动化脚本
├─ tests/                         # 测试套件
│  ├─ test_cli.py
│  ├─ test_engine_manager.py       # v1.2 引擎管理测试
│  ├─ test_engine_selector.py      # v1.2 引擎选择器测试
│  ├─ test_cloud_sync.py            # v1.2 云端同步测试
│  ├─ test_plugin_sdk.py            # v1.2 插件 SDK 测试
│  ├─ test_community_tools.py       # v1.2 社区工具链测试
│  ├─ test_integration.py           # v1.2 集成测试
│  ├─ test_boundary.py              # v1.2 边界测试
│  ├─ test_regression.py            # v1.2 回归测试
│  ├─ test_benchmark.py             # v1.2 性能基准测试
│  ├─ test_performance.py         # v1.1 性能监控测试
│  ├─ test_streaming.py           # v1.1 流式处理测试
│  ├─ test_gpu_backend.py         # v1.1 GPU 后端测试
│  ├─ test_checkpoint.py          # v1.1 断点续传测试
│  ├─ test_workspace.py           # v1.1 工作区管理测试
│  ├─ test_plugin_watcher.py      # v1.1 插件热重载测试
│  ├─ test_ocr_languages.py       # v1.1 OCR 多语言测试
│  ├─ test_ai_simplify.py         # v0.5 AI 简化测试
│  ├─ test_ai_ocr.py              # v0.5 OCR 测试
│  ├─ test_live_preview.py        # v0.5 实时预览测试
│  ├─ test_region_trace.py        # v0.5 局部重描摹测试
│  ├─ test_market.py              # v0.5 预设市场测试
│  ├─ test_enhance.py
│  ├─ test_external_editors.py
│  ├─ test_history.py
│  ├─ test_models.py
│  ├─ test_param_search.py
│  ├─ test_preset_manager.py
│  ├─ test_preprocess.py
│  ├─ test_presets.py
│  ├─ test_smart_background.py
│  ├─ test_smart_recommend.py
│  ├─ test_svg_layers.py
│  ├─ test_svg_optimizer.py
│  ├─ test_svg_tools.py
│  ├─ test_task_queue.py
│  ├─ test_tracer.py
│  ├─ test_plugins.py            # v0.4 插件系统测试
│  ├─ test_config.py             # v0.4 配置管理测试
│  ├─ test_api.py                # v0.4 API 测试
│  └─ test_api_client.py         # v0.4 客户端测试
├─ docs/
│  ├─ ROADMAP.md                  # 项目路线图
│  ├─ PROJECT_DECISION.md         # 技术选型决策记录
│  ├─ INSTALL.md                  # 详细安装指南
│  ├─ ENGINES.md                  # v1.2 多引擎使用文档
│  ├─ CLOUD.md                     # v1.2 云端同步文档
│  ├─ API.md                      # v0.4 API 文档
│  ├─ PLUGIN.md                   # v0.4 插件开发指南
│  ├─ AI.md                       # v0.5 AI 功能文档
│  ├─ MARKET.md                   # v0.5 预设市场文档
│  ├─ DOCKER.md                   # v0.4 Docker 使用指南
│  └─ DESKTOP.md                  # v1.0 桌面应用使用指南
├─ scripts/
│  ├─ run_gui.bat                 # Windows 快速启动脚本
│  ├─ run_gui.sh                  # macOS/Linux 快速启动脚本
│  ├─ package.py                  # 打包脚本
│  ├─ install.sh                  # v0.4 一键安装脚本
│  ├─ build-desktop.bat           # v1.0 Windows 桌面构建脚本
│  ├─ build-desktop.sh            # v1.0 macOS/Linux 桌面构建脚本
│  └─ release.py                  # v0.4 发布自动化脚本
├─ packaging/
│  ├─ homebrew/                   # v0.4 Homebrew Formula 模板
│  ├─ chocolatey/                 # v0.4 Chocolatey 包模板
│  └─ apt/                        # v0.4 APT deb 包模板
└─ examples/                      # 示例素材
```

---

## 🤝 开发贡献

我们欢迎所有形式的贡献！请参阅 [CONTRIBUTING.md](CONTRIBUTING.md) 了解：

- 开发环境搭建
- 代码风格规范
- 提交信息规范
- 测试要求
- PR 流程

---

## 🗺️ 路线图

项目发展路线详见 [docs/ROADMAP.md](docs/ROADMAP.md)。

**当前阶段（v2.0.0）**：AI 原生与实时协作 — 本地 AI 模型推理（ONNX Runtime 分割/风格迁移/超分辨率）、多引擎智能编排（AI 辅助选择最优引擎流水线）、实时协作编辑（WebSocket 多人同步）、矢量动画导出（SVG SMIL/Lottie/GIF/CSS）、智能批处理工作流（可视化节点编辑器）、跨设备同步（桌面端↔网页端↔API服务端）、云端账号与付费市场（用户账号/积分/付费插件/预设）。

**下一阶段（v3.0）**：智能设计平台 — AI 生成式矢量创作、云端渲染农场、设计系统集成、3D 矢量与 AR 预览、企业级权限管理、智能模板市场。

**长期目标（v3.0）**：智能设计平台 — AI 生成式矢量创作、云端渲染农场、设计系统集成、3D 矢量与 AR 预览、企业级权限管理、智能模板市场。

---

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE) 开源。

---

<p align="center">
  Made with ❤️ by Bitmap Vector Studio Contributors
</p>
