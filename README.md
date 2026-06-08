# Bitmap Vector Studio

一个以 **VTracer** 为核心引擎的位图转矢量工具模板，目标是做出接近 Adobe Illustrator「Image Trace / 图像描摹」体验的本地工具：

- 支持 PNG / JPG / JPEG / WEBP / BMP / TIFF 输入。
- 输出紧凑 SVG，并可选导出 PDF / PNG 预览。
- 内置 Illustrator 风格预设：黑白线稿、海报插画、高保真照片、Logo、像素艺术、扫描图。
- 提供命令行批处理和 Streamlit 网页 GUI。
- 支持参数面板：颜色模式、堆叠/剪切、曲线拟合、滤斑点、颜色精度、梯度层级、角点、路径精度等。
- 预留后处理、批量队列、Tauri 桌面版升级路线。

> 说明：矢量化本质是近似重建。Logo、图标、线稿、海报插画最容易达到专业效果；复杂照片可以接近 Illustrator 的「High Fidelity Photo」方向，但会在文件大小、颜色层数、可编辑性之间取舍。

## 1. 安装

推荐 Python 3.10+。

```bash
cd bitmap-vector-studio
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
# .venv\Scripts\Activate.ps1

pip install -U pip
pip install -e .
```

也可以直接安装依赖：

```bash
pip install -r requirements.txt
```

## 2. 启动网页 GUI

```bash
streamlit run app.py
```

打开浏览器后，上传图片、选择预设、调整参数，点击转换即可下载 SVG。

## 3. 命令行使用

单张图片转换：

```bash
vector-studio trace examples/input.png --output outputs/input.svg --preset poster
```

高保真照片：

```bash
vector-studio trace photo.jpg --output outputs/photo.svg --preset photo --export-pdf
```

Logo / 图标：

```bash
vector-studio trace logo.png --output outputs/logo.svg --preset logo --color-precision 7 --filter-speckle 2
```

像素艺术：

```bash
vector-studio trace pixel.png --output outputs/pixel.svg --preset pixel_art
```

批量转换：

```bash
vector-studio batch ./inputs ./outputs --preset poster --recursive
```

查看内置预设：

```bash
vector-studio presets
```

## 4. 预设建议

| 预设 | 适用素材 | 目标效果 |
|---|---|---|
| `bw` | 黑白线稿、印章、签名、扫描图 | 少色、清晰、路径干净 |
| `poster` | 插画、海报、扁平图形 | 接近 Illustrator 的详细插画模式 |
| `photo` | 照片、复杂彩色素材 | 更高颜色保真，但文件更大 |
| `logo` | Logo、图标、UI 图形 | 形状少、边缘顺滑、后续可编辑 |
| `pixel_art` | 像素画、游戏素材 | 保持像素风格，不强行平滑 |
| `scan` | 蓝图、历史扫描、手绘图 | 降噪、提高清晰度 |

## 5. 关键参数解释

- `colormode`：`color` 彩色；`binary` 黑白/单色。
- `hierarchical`：`stacked` 分层堆叠，通常更接近 Illustrator 的多层矢量；`cutout` 剪切模式，某些图形可减少重叠。
- `mode`：`spline` 平滑贝塞尔曲线；`polygon` 多边形；`pixel` 像素风；`none` 不做曲线拟合。
- `filter_speckle`：过滤小色块，数值越大越干净，但可能丢细节。
- `color_precision`：颜色精度，越高颜色越多、越准确，SVG 可能更大。
- `layer_difference`：梯度分层间隔，越小层数越多、越细腻，SVG 可能更大。
- `corner_threshold`：角点识别阈值。
- `length_threshold`：曲线细分长度，越低越精细。
- `splice_threshold`：样条拼接阈值。
- `path_precision`：SVG path 小数位数，越高越精确，文件越大。

## 6. 导出格式

- SVG：原生输出。
- PDF / PNG：通过 CairoSVG 转换。
- EPS：建议后续接入 Inkscape CLI；代码里已提供 `export_svg_to_eps_with_inkscape` 辅助函数。

## 7. 项目结构

```text
bitmap-vector-studio/
├─ app.py                         # Streamlit GUI
├─ pyproject.toml                 # Python 包配置
├─ requirements.txt
├─ src/vector_studio/
│  ├─ cli.py                      # 命令行入口
│  ├─ models.py                   # 参数模型和校验
│  ├─ presets.py                  # 预设策略
│  ├─ preprocess.py               # Pillow 预处理
│  ├─ svg_tools.py                # SVG 优化/统计/导出
│  └─ tracer.py                   # VTracer 调用封装
├─ tests/
└─ docs/
```

## 8. 下一步升级路线

第一阶段：稳定转换和批处理。
第二阶段：加入对比预览、参数历史、自定义预设保存。
第三阶段：封装 Tauri 桌面端，保持 Rust/VTracer 性能优势。
第四阶段：增加 AI 辅助重绘、自动识别 Logo/照片/线稿并推荐参数。

详细路线见 `docs/ROADMAP.md`。
