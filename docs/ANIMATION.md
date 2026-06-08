# 矢量动画导出指南

Bitmap Vector Studio v2.0 引入统一动画导出器，支持将静态 SVG 转换为四种主流动画格式：SVG SMIL、Lottie JSON、GIF 和 CSS 关键帧动画。

---

## 目录

- [功能概述](#功能概述)
- [SVG SMIL 动画](#svg-smil-动画)
- [Lottie 导出](#lottie-导出)
- [GIF 动画导出](#gif-动画导出)
- [CSS 动画生成](#css-动画生成)
- [CLI 使用示例](#cli-使用示例)
- [Python API 使用](#python-api-使用)
- [动画预设](#动画预设)
- [注意事项](#注意事项)

---

## 功能概述

矢量动画导出解决以下场景：

- **网页动画**：导出 CSS 动画或 Lottie，直接嵌入网页和移动端应用
- **演示文稿**：导出 GIF 或 Lottie，在 Keynote、PPT 中播放
- **UI 动效**：将 Logo、图标转换为可交互的 Lottie 动画
- **路径变形**：SVG SMIL 实现路径之间的平滑形变过渡

### 支持的动画类型

| 格式 | 文件扩展名 | 适用场景 | 优势 |
|---|---|---|---|
| **SVG SMIL** | `.svg` | 网页原生动画、路径变形 | 零依赖，浏览器原生支持 |
| **Lottie** | `.json` | 移动端、After Effects | 跨平台，文件极小 |
| **GIF** | `.gif` | 社交媒体、演示文稿 | 兼容性最强 |
| **CSS 动画** | `.css` | 网页开发 | 可直接嵌入样式表 |

---

## SVG SMIL 动画

SVG SMIL（Synchronized Multimedia Integration Language）是 SVG 内置的动画规范，无需 JavaScript 即可实现路径变形、颜色过渡、位移动画。

### 支持的效果

| 效果 | 说明 | 示例 |
|---|---|---|
| `path_morph` | 路径形变，从一个形状平滑过渡到另一个形状 | Logo 变形、图标切换 |
| `color_transition` | 填充颜色和描边颜色渐变过渡 | 主题切换、状态变化 |
| `translate` | 位移动画，沿 X/Y 轴移动 | 入场动画、悬浮效果 |
| `scale` | 缩放动画 | 脉冲效果、强调动画 |
| `rotate` | 旋转动画 | 加载图标、循环动画 |
| `opacity` | 透明度渐变 | 淡入淡出、闪烁效果 |

### CLI 导出 SMIL 动画

```bash
# 基础路径变形动画
vector-studio animate export logo.svg --format smil --effect path_morph --target logo2.svg

# 颜色过渡动画
vector-studio animate export icon.svg --format smil --effect color_transition --duration 2s

# 组合效果：位移 + 缩放 + 淡入
vector-studio animate export badge.svg --format smil --effect translate,scale,opacity --duration 1.5s
```

### Python API

```python
from vector_studio.svg_smil import SVGSMIBuilder
from pathlib import Path

builder = SVGSMIBuilder()

# 路径变形动画
builder.add_path_morph(
    source_path=Path("logo.svg"),
    target_path=Path("logo_alt.svg"),
    duration="2s",
    repeat_count="indefinite"
)
builder.export(Path("logo_animated.svg"))

# 颜色过渡
builder.add_color_transition(
    element_id="main-fill",
    from_color="#FF5733",
    to_color="#33FF57",
    duration="3s"
)
```

---

## Lottie 导出

Lottie 是由 Airbnb 开源的动画格式，基于 JSON 描述矢量动画，可在 iOS、Android、Web、React Native 上原生渲染。

### 特性

- 文件体积通常小于 GIF 的 1/10
- 任意缩放不失真
- 支持暂停、播放、速度控制、逐帧控制
- 与 After Effects 工作流兼容

### CLI 导出 Lottie

```bash
# 基础 Lottie 导出
vector-studio animate export logo.svg --format lottie --output logo.json

# 带入场动画的 Lottie
vector-studio animate export icon.svg --format lottie --effect fade_in_scale --duration 1s

# 循环动画
vector-studio animate export spinner.svg --format lottie --effect rotate --repeat infinite
```

### Python API

```python
from vector_studio.lottie_export import LottieExporterV2
from pathlib import Path

exporter = LottieExporterV2()

# 导出基础 Lottie
exporter.export(
    svg_path=Path("logo.svg"),
    output_path=Path("logo.json"),
    animation={
        "type": "fade_in_scale",
        "duration": 1.0,
        "easing": "easeOutCubic"
    }
)

# 复杂动画：路径变形 + 颜色过渡
exporter.export(
    svg_path=Path("illustration.svg"),
    output_path=Path("illustration.json"),
    animation={
        "type": "path_morph",
        "target_svg": "illustration_alt.svg",
        "duration": 2.5,
        "repeat": -1,  # 无限循环
        "yoyo": True   # 往返播放
    }
)
```

---

## GIF 动画导出

GIF 是最通用的动画格式，适合社交媒体、聊天工具、演示文稿等场景。

### 特性

- 支持自定义帧率（1-60 FPS）
- 调色板优化（最多 256 色）
- 循环设置（无限循环或指定次数）
- 背景透明（支持 Alpha 通道）

### CLI 导出 GIF

```bash
# 基础 GIF 导出（默认 10 FPS，无限循环）
vector-studio animate export logo.svg --format gif --output logo.gif

# 高帧率 GIF
vector-studio animate export animation.svg --format gif --fps 30 --duration 3s

# 有限循环 + 透明背景
vector-studio animate export icon.svg --format gif --loop 3 --transparent
```

### Python API

```python
from vector_studio.gif_export import GIFExporter
from pathlib import Path

exporter = GIFExporter()

exporter.export(
    svg_path=Path("logo.svg"),
    output_path=Path("logo.gif"),
    fps=15,
    duration=2.0,
    loop=0,  # 0 = 无限循环
    transparent=True,
    palette_size=128  # 优化调色板大小
)
```

---

## CSS 动画生成

CSS 动画生成器输出可直接用于网页的 CSS 关键帧代码，无需额外 JavaScript 库。

### 特性

- 输出纯 CSS `@keyframes` 规则
- 支持 `transform`（位移、旋转、缩放）和 `opacity`
- 自动生成浏览器前缀（`-webkit-`、`-moz-`）
- 可自定义缓动函数（ease、linear、ease-in-out 等）

### CLI 生成 CSS 动画

```bash
# 基础 CSS 动画
vector-studio animate export icon.svg --format css --output icon_animation.css

# 指定类名和缓动
vector-studio animate export loader.svg --format css --class-name .spinner --easing linear
```

### Python API

```python
from vector_studio.css_animation import CSSAnimationBuilder
from pathlib import Path

builder = CSSAnimationBuilder()

css = builder.build(
    svg_path=Path("icon.svg"),
    animation_type="rotate",
    duration="2s",
    easing="linear",
    class_name=".icon-spin",
    infinite=True
)

Path("animations.css").write_text(css, encoding="utf-8")
```

### 输出示例

```css
/* 生成的 CSS 动画 */
.icon-spin {
  animation: icon-spin-anim 2s linear infinite;
}

@keyframes icon-spin-anim {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
```

---

## CLI 使用示例

### 列出动画预设

```bash
vector-studio animate list-presets
```

### 预览动画效果

```bash
# 在浏览器中预览 SMIL 动画
vector-studio animate preview logo.svg --format smil

# 预览 Lottie 动画（打开 Lottie 预览网页）
vector-studio animate preview logo.json --format lottie
```

### 批量导出动画

```bash
# 将文件夹内所有 SVG 导出为 Lottie
vector-studio animate export ./icons --format lottie --output-dir ./lottie_icons

# 批量导出 GIF
vector-studio animate export ./badges --format gif --fps 20 --output-dir ./gif_badges
```

---

## Python API 使用

### 统一动画导出器

```python
from vector_studio.animation_exporter import AnimationExporter
from pathlib import Path

exporter = AnimationExporter()

# 自动根据格式选择导出器
exporter.export(
    svg_path=Path("logo.svg"),
    output_path=Path("logo.json"),
    format="lottie",
    animation={"type": "fade_in", "duration": 1.5}
)

exporter.export(
    svg_path=Path("logo.svg"),
    output_path=Path("logo.gif"),
    format="gif",
    fps=20,
    duration=3.0
)
```

### 动画预设

```python
from vector_studio.animation_exporter import list_presets

# 列出所有内置动画预设
for preset in list_presets():
    print(f"{preset['name']}: {preset['description']}")

# 使用预设快速导出
exporter.export(
    svg_path=Path("logo.svg"),
    output_path=Path("logo.json"),
    format="lottie",
    preset="logo_entrance"  # 使用预设
)
```

---

## 动画预设

v2.0 内置以下动画预设：

| 预设名称 | 适用素材 | 动画效果 | 默认格式 |
|---|---|---|---|
| `logo_entrance` | Logo、图标 | 缩放 + 淡入 | Lottie |
| `icon_pulse` | 功能图标 | 缩放脉冲 | CSS |
| `spinner_loop` | 加载图标 | 无限旋转 | CSS / Lottie |
| `path_morph` | 变形图标 | 路径形变 | SMIL |
| `color_breathe` | 状态指示器 | 颜色呼吸 | CSS |
| `slide_in` | 横幅、徽章 | 从侧滑入 | Lottie |
| `bounce` | 强调元素 | 弹跳效果 | Lottie |
| `fade_cycle` | 背景装饰 | 透明度循环 | CSS |

---

## 注意事项

1. **路径变形限制**：SMIL 路径变形要求源路径和目标路径具有相同数量的命令点。若点数不匹配，系统会自动插值，但效果可能不理想。
2. **Lottie 兼容性**：复杂渐变、滤镜效果在 Lottie 中可能不被支持，导出前建议简化 SVG。
3. **GIF 颜色限制**：GIF 最多 256 色，复杂彩色 SVG 导出时可能出现色带。建议减少颜色数量或使用 Lottie 替代。
4. **CSS 动画范围**：CSS 动画仅支持 `transform` 和 `opacity` 属性，不支持路径变形。路径变形请使用 SMIL 或 Lottie。
5. **性能建议**：网页中大量使用 Lottie 动画时，建议启用 `renderer: 'svg'` 模式以获得最佳性能。

---

<p align="center">
  Made with ❤️ by Bitmap Vector Studio Contributors
</p>
