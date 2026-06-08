# AI 功能文档

Bitmap Vector Studio v1.2 引入纯 Pillow / NumPy 实现的 AI 辅助功能，无需 PyTorch、TensorFlow 等深度学习框架，在本地即可完成对复杂照片的语义简化、卡通化效果以及文字区域检测与识别。

---

## 目录

- [AI 语义简化](#ai-语义简化)
- [OCR 文字识别](#ocr-文字识别)
- [OCR 多语言增强](#ocr-多语言增强)
- [安装可选依赖](#安装可选依赖)
- [使用示例](#使用示例)
- [效果对比与参数建议](#效果对比与参数建议)
- [注意事项](#注意事项)

---

## AI 语义简化

AI 语义简化在矢量化之前对输入图像进行预处理，将复杂照片转换为更适合矢量化的插画风格图像。所有算法均基于 Pillow 和可选的 NumPy 实现，无需 GPU。

### 四种简化策略

| 函数 | 适用场景 | 核心算法 | 输出风格 |
|---|---|---|---|
| `semantic_simplify()` | 照片、复杂彩图 | 双边滤波模拟 + K-Means 量化 + 边缘保护 | 扁平插画，保留主要色块 |
| `superpixel_simplify()` | 风景、大色块照片 | 网格超像素分割 + 区域平均色填充 | 均匀色块，类似低多边形 |
| `cartoon_effect()` | 人像、动漫素材 | 中值滤波 + 高斯平滑 + 边缘加深 | 卡通/漫画风格 |
| `adaptive_simplify()` | 未知类型素材 | 自动估计复杂度并选择上述策略之一 | 自适应，无需手动选择 |

### 参数说明

#### `semantic_simplify`

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `color_clusters` | int | `8` | 保留的主导颜色数量（2–256），越大颜色越丰富 |
| `edge_preserve` | bool | `True` | 是否在量化时保护边缘，防止色块边界模糊 |

#### `superpixel_simplify`

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `n_segments` | int | `100` | 目标分割块数，越大块越小、细节越多 |

#### `cartoon_effect`

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `blur_radius` | int | `5` | 平滑半径，越大色块越平坦 |
| `edge_threshold` | int | `100` | 边缘检测阈值（0–255），越低边缘越多 |

#### `adaptive_simplify`

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `image_type` | str | `"auto"` | `"photo"`、`"complex"`、`"sketch"` 或 `"auto"` |

---

## OCR 文字识别

OCR 模块检测图片中的文字区域，并在最终 SVG 中将文字保留为可编辑的 `<text>` 元素，而不是全部转为路径。这对于扫描件、海报、Logo 中的文字尤为重要。

### 工作流程

1. **文字区域检测**（`detect_text_regions`）：基于对比度分析、水平线密度和宽高比启发式，无需外部 OCR 库即可定位可能的文字区域。
2. **文字识别**（`recognize_text`）：优先尝试 `pytesseract`，其次 `easyocr`。两者均未安装时返回空文本的区域框。
3. **SVG 嵌入**（`integrate_text_to_svg`）：将识别结果插入 SVG 最上层，文字可在外部编辑器中直接编辑。

### 识别引擎对比

| 引擎 | 依赖 | 优势 | 劣势 |
|---|---|---|---|
| **pytesseract** | Tesseract OCR + `pytesseract` | 速度快、支持多语言、离线运行 | 对复杂排版和倾斜文字效果一般 |
| **easyocr** | `easyocr` | 对自然场景文字、倾斜文字效果更好 | 首次运行需下载模型、体积较大 |

---

## OCR 多语言增强

v1.1 大幅增强 OCR 多语言支持，覆盖 10 种常用语言，并新增竖排文字检测。

### 支持的语言

| 语言 | Tesseract 代码 | EasyOCR 代码 | 竖排支持 |
|---|---|---|---|
| 简体中文 | `chi_sim` | `ch_sim` | ✅ |
| 繁体中文 | `chi_tra` | `ch_tra` | ✅ |
| 日文 | `jpn` | `ja` | ✅ |
| 韩文 | `kor` | `ko` | ❌ |
| 阿拉伯文 | `ara` | `ar` | ❌ |
| 俄文 | `rus` | `ru` | ❌ |
| 德文 | `deu` | `de` | ❌ |
| 法文 | `fra` | `fr` | ❌ |
| 西班牙文 | `spa` | `es` | ❌ |
| 英文 | `eng` | `en` | ❌ |

### 语言自动检测

v1.1 新增 `detect_language()` 函数，自动判断图片中主要文字语言：

```python
from PIL import Image
from vector_studio import detect_language

img = Image.open("scan.png")
lang = detect_language(img)
print(f"Detected language: {lang}")  # 例如: 'chi_sim'
```

检测基于以下启发式：
- 文字区域密度和分布
- 字符宽高比特征
- 行高和字间距模式

### 多语言混合识别

使用 `recognize_text_multilang()` 支持同图多语言混合识别：

```python
from PIL import Image
from vector_studio import recognize_text_multilang

img = Image.open("mixed.png")

# 中文 + 英文混合
results = recognize_text_multilang(img, lang="chi_sim+eng")
for r in results:
    print(f"  '{r['text']}' at {r['bbox']} (lang={r.get('lang', 'unknown')})")
```

### 竖排文字检测

v1.1 新增 `detect_vertical_text()`，支持日文、中文传统竖排排版：

```python
from PIL import Image
from vector_studio import detect_vertical_text, create_text_overlay_svg_multilang
from pathlib import Path

img = Image.open("vertical_japanese.png")

# 检测竖排文字区域
regions = detect_vertical_text(img, lang="jpn")
for r in regions:
    print(f"  Vertical text: '{r['text']}' at {r['bbox']}")

# 生成带竖排文字的 SVG
integrate_text_to_svg(
    svg_path=Path("output.svg"),
    text_regions=regions,
    output_path=Path("output_with_text.svg"),
    vertical=True,
)
```

竖排文字在 SVG 中使用 `writing-mode: vertical-rl` 样式，在 Illustrator / Inkscape 中可正常编辑。

### 安装语言包

**Tesseract 语言包**：

```bash
# Ubuntu/Debian
sudo apt install tesseract-ocr-chi-sim tesseract-ocr-chi-tra tesseract-ocr-jpn tesseract-ocr-kor

# macOS
brew install tesseract-lang

# Windows
# 下载语言包并放入 Tesseract 的 tessdata 目录
```

**EasyOCR**：首次使用指定语言时会自动下载模型：

```python
import easyocr
reader = easyocr.Reader(['ch_sim', 'en'])  # 自动下载模型
```

---

## 安装可选依赖

### AI 语义简化

AI 语义简化的核心功能仅依赖 Pillow（已包含在核心依赖中）。**推荐**安装 NumPy 以获得更快的 K-Means 量化和数组操作：

```bash
pip install -e ".[smart]"
```

### OCR 文字识别

OCR 是可选功能，需要额外安装识别引擎：

#### 方案一：Tesseract + pytesseract（推荐）

**1. 安装 Tesseract OCR（系统级）**

- **Windows**：下载安装包 https://github.com/UB-Mannheim/tesseract/wiki ，安装后确保 `tesseract.exe` 在 PATH 中。
- **macOS**：`brew install tesseract`
- **Ubuntu/Debian**：`sudo apt install tesseract-ocr`
- **Fedora**：`sudo dnf install tesseract`

**2. 安装 Python 绑定**

```bash
pip install pytesseract
```

#### 方案二：EasyOCR

```bash
pip install easyocr
```

首次使用时会自动下载识别模型（约 100MB+）。

#### 方案三：同时安装（完整 OCR 支持）

```bash
pip install -e ".[ai]"
```

---

## 使用示例

### CLI 快速使用

```bash
# AI 语义简化（自适应策略）
vector-studio trace photo.jpg --ai-simplify --output photo.svg

# 指定简化类型
vector-studio trace photo.jpg --ai-simplify --simplify-type photo --output photo.svg
vector-studio trace sketch.jpg --ai-simplify --simplify-type sketch --output sketch.svg

# OCR 文字保留
vector-studio trace scan.png --ai-ocr --output scan.svg

# 组合使用：简化 + OCR + 局部重描摹
vector-studio trace poster.jpg --ai-simplify --ai-ocr --region 100,100,400,200
```

### Python API 使用

#### AI 语义简化

```python
from PIL import Image
from vector_studio import adaptive_simplify, semantic_simplify, cartoon_effect

img = Image.open("photo.jpg")

# 自适应简化（自动判断类型）
simplified = adaptive_simplify(img, image_type="auto")
simplified.save("simplified.png")

# 指定策略
illustration = semantic_simplify(img, color_clusters=6, edge_preserve=True)
cartoon = cartoon_effect(img, blur_radius=5, edge_threshold=80)
```

#### OCR 文字识别

```python
from PIL import Image
from vector_studio import detect_text_regions, recognize_text, integrate_text_to_svg
from pathlib import Path

img = Image.open("scan.png")

# 仅检测文字区域（无需 OCR 库）
regions = detect_text_regions(img)
print(f"Found {len(regions)} text regions")
for r in regions:
    print(f"  bbox={r['bbox']}, confidence={r['confidence']}")

# 完整识别（需要 pytesseract 或 easyocr）
results = recognize_text(img)
for r in results:
    print(f"  '{r['text']}' at {r['bbox']} (confidence={r['confidence']:.2f})")

# 嵌入到 SVG
integrate_text_to_svg(
    svg_path=Path("output.svg"),
    text_regions=results,
    output_path=Path("output_with_text.svg")
)
```

#### 实时预览

```python
from vector_studio import LivePreviewEngine, TraceOptions
from pathlib import Path

engine = LivePreviewEngine(max_size=400, cache_size=10)
opts = TraceOptions(preset="poster")

preview_path, elapsed = engine.generate_preview(Path("input.png"), opts)
print(f"Preview saved to {preview_path} ({elapsed:.2f}s)")

# 查看缓存统计
print(engine.get_cache_stats())
```

#### OCR 多语言增强

```python
from PIL import Image
from vector_studio import (
    detect_language,
    recognize_text_multilang,
    detect_vertical_text,
    create_text_overlay_svg_multilang,
)
from pathlib import Path

img = Image.open("mixed_document.png")

# 自动检测语言
lang = detect_language(img)
print(f"Detected: {lang}")

# 多语言混合识别
results = recognize_text_multilang(img, lang="chi_sim+eng")
for r in results:
    print(f"  '{r['text']}' at {r['bbox']} (lang={r.get('lang')})")

# 竖排文字检测
vertical_regions = detect_vertical_text(img, lang="jpn")

# 生成多语言 SVG
create_text_overlay_svg_multilang(
    svg_path=Path("output.svg"),
    text_regions=results + vertical_regions,
    output_path=Path("output_multilang.svg"),
)
```

```python
from vector_studio import RegionSelector, region_trace, TraceOptions
from pathlib import Path

# 矩形选区
region = RegionSelector(x=100, y=100, width=200, height=200, shape="rect")
result = region_trace(
    input_path=Path("input.png"),
    region=region,
    output_path=Path("region.svg"),
    options=TraceOptions(preset="logo"),
)

# 合并回原始 SVG（局部更新）
from vector_studio import region_trace  # 传入 original_svg 参数自动合并
result = region_trace(
    input_path=Path("input.png"),
    region=region,
    output_path=Path("updated.svg"),
    options=TraceOptions(preset="logo"),
    original_svg=Path("original.svg"),
)
```

---

## 效果对比与参数建议

### 照片转插画

| 原始素材 | 推荐策略 | 参数建议 | 预期效果 |
|---|---|---|---|
| 高保真照片 | `semantic_simplify` | `color_clusters=8`, `edge_preserve=True` | 颜色减少到 6–10 种，边缘清晰 |
| 风景/建筑 | `superpixel_simplify` | `n_segments=80–120` | 均匀色块，类似低多边形 |
| 人像/动漫 | `cartoon_effect` | `blur_radius=5`, `edge_threshold=100` | 卡通化，边缘粗黑线 |
| 线稿/草图 | `adaptive_simplify` | `image_type="sketch"` | 强边缘保护 + 激进量化 |

### OCR 效果优化

| 场景 | 推荐引擎 | 预处理建议 |
|---|---|---|
| 扫描件、印刷体 | pytesseract | `--enhance scan` 去噪 |
| 屏幕截图、UI 文字 | pytesseract | 无需预处理 |
| 自然场景、招牌 | easyocr | `--enhance photo` 增强对比度 |
| 倾斜/弯曲文字 | easyocr | 先裁剪文字区域再识别 |

---

## 注意事项

1. **可选依赖**：AI 语义简化的核心功能无需额外依赖；NumPy 仅用于加速。OCR 功能必须安装 `pytesseract` 或 `easyocr` 才能输出实际文字内容，否则仅返回空文本的区域框。
2. **性能**：
   - `semantic_simplify` 的 K-Means 量化在 NumPy 可用时处理一张 1920×1080 图片约 1–3 秒；纯 Pillow 回退约 5–10 秒。
   - `superpixel_simplify` 的网格分割在 NumPy 下接近实时；纯 Pillow 回退约 3–5 秒。
   - `easyocr` 首次运行需下载模型（约 100MB+），后续加载模型约 2–5 秒。
   - `pytesseract` 识别速度较快，但受 Tesseract 引擎版本影响。
3. **文字可编辑性**：OCR 嵌入的 `<text>` 元素使用通用 `sans-serif` 字体，字号根据区域高度估算。在 Illustrator / Inkscape 中打开后可自由修改字体、颜色、位置。
4. **识别准确率**：OCR 对复杂背景、艺术字体、手写体识别率有限。建议对重要文档进行人工校对。
5. **实时预览缓存**：`LivePreviewEngine` 默认缓存最近 10 组参数组合（TTL 300 秒）。GUI 中频繁调整参数时，缓存可显著减少重复计算。
