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
  <img src="https://img.shields.io/badge/version-0.5.0-orange" alt="Version 0.5.0">
</p>

---

Bitmap Vector Studio 是一个以 **VTracer** 为核心引擎的位图转矢量工具，目标是做出接近 Adobe Illustrator「Image Trace / 图像描摹」体验的本地工具。

- 支持 PNG / JPG / JPEG / WEBP / BMP / TIFF 输入
- 输出紧凑 SVG，并可选导出 PDF / PNG 预览 / EPS
- 内置 Illustrator 风格预设：黑白线稿、海报插画、高保真照片、Logo、像素艺术、扫描图
- **v0.3 新增**：智能背景透明、图像增强、智能预设推荐、SVG 深度优化、参数搜索、批量任务队列
- **v0.4 新增**：插件系统、Web API、Docker 容器化、配置管理、一键安装脚本、包管理器模板
- **v0.5 新增**：实时预览、局部重描摹、AI 语义简化、OCR 文字识别、预设市场
- 自定义预设管理：保存、加载、删除、导入、导出用户预设（JSON）
- 任务历史记录：自动记录转换历史，支持参数复用、CSV/Markdown 报告导出
- 外部编辑器集成：一键打开 Illustrator、Inkscape、Affinity Designer、Figma 等
- 提供命令行批处理、Streamlit 网页 GUI 和 FastAPI RESTful 服务

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

### 🛒 预设市场（v0.5）
- 🌐 **在线预设分享**：基于 GitHub Gist / Repo 后端，浏览、搜索、安装社区预设
- ⬆️ **一键发布**：将本地预设发布到市场，生成可分享的预设 ID
- ⭐ **本地评分**：为预设打分，热门预设按评分和下载量排序
- 🔧 **自定义源**：通过配置文件添加私有或团队预设源

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

### 方式一：网页 GUI（推荐新手）

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

### 方式二：CLI 单图转换

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

### 方式三：CLI 批量转换

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

### 方式四：v0.3 智能与高级功能

```bash
# 智能推荐最佳预设
vector-studio trace logo.png --recommend

# 智能推荐后直接转换
vector-studio trace logo.png --recommend --preset logo

# 背景透明（适合 Logo）
vector-studio trace logo.png --smart-remove-bg --preset logo

# 图像增强 + 转换
vector-studio trace scan.jpg --enhance scan --preset scan

# 参数搜索（自动找最优参数）
vector-studio search photo.jpg --output-dir ./searches --max 15

# 快速预设搜索
vector-studio search photo.jpg --output-dir ./searches --quick

# 批量队列（并发 + 重试）
vector-studio batch ./inputs ./outputs --workers 4 --retry 2

# SVG 深度优化并评分
vector-studio trace design.png --optimize-level comprehensive --score
```

### 方式五：Web API 服务（v0.4）

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

### 方式六：v0.5 AI 与实时交互

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

详见 [docs/AI.md](docs/AI.md) 和 [docs/MARKET.md](docs/MARKET.md)。

---

## 🖥️ GUI 使用指南

### 侧边栏参数面板

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
| `vector-studio api` | **v0.4** 启动 API 服务 |
| `vector-studio market list` | **v0.5** 列出市场预设 |
| `vector-studio market search` | **v0.5** 搜索市场预设 |
| `vector-studio market install` | **v0.5** 安装市场预设 |
| `vector-studio market publish` | **v0.5** 发布本地预设 |
| `vector-studio market popular` | **v0.5** 查看热门预设 |
| `vector-studio market info` | **v0.5** 查看预设详情 |

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
    version = "1.0.0"
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
print(client.health())  # {'status': 'ok', 'version': '0.5.0'}
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
│  ├─ ai_simplify.py              # v0.5 AI 语义简化（语义/超像素/卡通/自适应）
│  ├─ ai_ocr.py                   # v0.5 OCR 文字检测与 SVG 嵌入
│  ├─ live_preview.py             # v0.5 实时预览引擎（LRU+TTL 缓存）
│  ├─ region_trace.py             # v0.5 局部重描摹（矩形/圆形/多边形选区）
│  ├─ market.py                   # v0.5 预设市场（Gist/Repo 后端）
│  └─ release.py                  # v0.4 发布自动化脚本
├─ tests/                         # 测试套件
│  ├─ test_cli.py
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
│  ├─ API.md                      # v0.4 API 文档
│  ├─ PLUGIN.md                   # v0.4 插件开发指南
│  ├─ AI.md                       # v0.5 AI 功能文档
│  ├─ MARKET.md                   # v0.5 预设市场文档
│  └─ DOCKER.md                   # v0.4 Docker 使用指南
├─ scripts/
│  ├─ run_gui.bat                 # Windows 快速启动脚本
│  ├─ run_gui.sh                  # macOS/Linux 快速启动脚本
│  ├─ package.py                  # 打包脚本
│  ├─ install.sh                  # v0.4 一键安装脚本
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

**当前阶段（v0.5.0）**：AI 辅助与实时交互 — 实时预览、局部重描摹、AI 语义简化、OCR 文字识别、预设市场。

**下一阶段（v0.6）**：质量与体验优化 — 智能参数微调、批量预览、GPU 加速推理、多语言 OCR、插件市场。

**长期目标（v1.0）**：Tauri 桌面端（已启动）、拖拽队列、原生文件菜单、跨平台打包（已配置）、自动更新机制（已配置）、插件市场。

---

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE) 开源。

---

<p align="center">
  Made with ❤️ by Bitmap Vector Studio Contributors
</p>
