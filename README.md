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
  <img src="https://img.shields.io/badge/version-0.2.0-orange" alt="Version 0.2.0">
</p>

---

Bitmap Vector Studio 是一个以 **VTracer** 为核心引擎的位图转矢量工具，目标是做出接近 Adobe Illustrator「Image Trace / 图像描摹」体验的本地工具。

- 支持 PNG / JPG / JPEG / WEBP / BMP / TIFF 输入
- 输出紧凑 SVG，并可选导出 PDF / PNG 预览 / EPS
- 内置 Illustrator 风格预设：黑白线稿、海报插画、高保真照片、Logo、像素艺术、扫描图
- 自定义预设管理：保存、加载、删除、导入、导出用户预设（JSON）
- 任务历史记录：自动记录转换历史，支持参数复用、CSV/Markdown 报告导出
- 外部编辑器集成：一键打开 Illustrator、Inkscape、Affinity Designer、Figma 等
- 提供命令行批处理和 Streamlit 网页 GUI

> **说明**：矢量化本质是近似重建。Logo、图标、线稿、海报插画最容易达到专业效果；复杂照片可以接近 Illustrator 的「High Fidelity Photo」方向，但会在文件大小、颜色层数、可编辑性之间取舍。

---

## ✨ 功能特性

### 🎨 核心转换
- 🖼️ 支持多种位图格式：PNG、JPG、WEBP、BMP、TIFF
- 📐 输出标准 SVG，兼容 Inkscape、Illustrator、Figma 等主流工具
- 🎯 6 种内置预设，覆盖常见设计场景
- 🔧 12+ 项可调参数，精细控制转换效果

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

### 系统要求

| 项目 | 要求 |
|---|---|
| Python | 3.9 或更高版本 |
| 操作系统 | Windows 10+ / macOS 11+ / Linux |
| 内存 | 建议 4GB+（处理高分辨率图片） |
| 磁盘 | 约 100MB 安装空间 |

### 快速安装

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

### 可选依赖

```bash
# 开发依赖（测试 + 代码风格检查）
pip install -e ".[dev]"

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

---

## 🖥️ GUI 使用指南

### 侧边栏参数面板

| 区域 | 功能 |
|---|---|
| **转换预设** | 选择内置或用户预设，保存/删除自定义预设 |
| **核心参数** | 颜色模式、分层方式、曲线拟合、滤斑点、颜色精度等 |
| **高级参数** | 最大迭代次数等进阶选项 |
| **预处理** | 降噪、限制输入边长、Posterize 颜色量化 |
| **导出选项** | 压缩 SVG、导出 PDF/PNG |
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
| `--name-layers` | | bool | `False` | 为图层添加语义化名称 |
| `--export-pdf` | | bool | `False` | 同时导出 PDF |
| `--export-png` | | bool | `False` | 同时导出 PNG 预览 |
| `--export-eps` | | bool | `False` | 同时导出 EPS（需 Inkscape） |
| `--open` | | str | | 转换后在指定编辑器中打开 |

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
├─ src/vector_studio/
│  ├─ __init__.py
│  ├─ cli.py                      # Typer 命令行入口
│  ├─ models.py                   # 参数模型和校验（TraceOptions / TraceResult）
│  ├─ presets.py                  # 内置预设策略
│  ├─ preset_manager.py           # 用户自定义预设管理（保存/加载/导入/导出）
│  ├─ preprocess.py               # Pillow 图像预处理
│  ├─ svg_tools.py                # SVG 优化、统计、导出（PDF/PNG/EPS）
│  ├─ tracer.py                   # VTracer 调用封装
│  ├─ history.py                  # 任务历史记录（JSONL 存储）
│  └─ external_editors.py         # 外部编辑器检测和启动
├─ tests/                         # 测试套件
│  ├─ test_presets.py
│  ├─ test_preset_manager.py
│  ├─ test_history.py
│  ├─ test_external_editors.py
│  ├─ test_svg_tools.py
│  └─ test_svg_layers.py
├─ docs/
│  ├─ ROADMAP.md                  # 项目路线图
│  ├─ PROJECT_DECISION.md         # 技术选型决策记录
│  └─ INSTALL.md                  # 详细安装指南
├─ scripts/
│  ├─ run_gui.bat                 # Windows 快速启动脚本
│  ├─ run_gui.sh                  # macOS/Linux 快速启动脚本
│  └─ package.py                  # 打包脚本
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

**当前阶段（v0.2.0）**：Illustrator-like 体验 — 自定义预设、历史记录、外部编辑器、GUI 增强。

**下一阶段（v0.3）**：质量优化 — 自动背景透明、OpenCV 边缘增强、SVG 路径合并、多参数自动择优。

**长期目标（v1.0）**：Tauri 桌面端、拖拽队列、原生文件菜单、跨平台打包。

---

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE) 开源。

---

<p align="center">
  Made with ❤️ by Bitmap Vector Studio Contributors
</p>
