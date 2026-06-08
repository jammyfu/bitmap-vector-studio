# 项目方案分析：为什么选择 VTracer + Python MVP

## 结论

第一版选择 **Python + VTracer 官方绑定 + Streamlit GUI + Typer CLI**。

原因：

1. VTracer 已经实现了位图转 SVG 的核心难点：彩色分层、聚类、曲线拟合、紧凑 SVG 输出。
2. 官方 Python 包已经能直接调用 Rust 核心，不需要第一阶段从零做算法。
3. Streamlit 能最快做出可交互参数面板，便于调试预设和验证素材效果。
4. Typer CLI 适合批量转换、自动化处理和后续打包成桌面 App。

## 与 Illustrator Image Trace 的对应关系

| Illustrator 概念 | 本项目 / VTracer 参数 | 说明 |
|---|---|---|
| Mode: Color / Black and White | `colormode=color/binary` | 彩色或单色描摹 |
| Palette / Colors | `color_precision`, `layer_difference` | 控制颜色数量和梯度层数 |
| Paths / Corners / Noise | `length_threshold`, `corner_threshold`, `filter_speckle` | 控制路径精细度、角点和噪点 |
| Method / Stacking | `hierarchical=stacked/cutout` | stacked 更接近多层矢量输出 |
| Curves | `mode=spline/polygon/pixel/none` | 平滑曲线、多边形、像素风 |

## 真实能力边界

- Logo、图标、线稿、扫描件：可以做到接近专业工具的自动描摹效果。
- 插画、海报：通过 `poster` / `logo` 预设效果较好，文件也相对可控。
- 复杂照片：能做高保真矢量化，但 SVG 可能变大，可编辑性通常不如手工重绘。
- Illustrator 仍有完整编辑器、颜色库、描摹后交互式调参、扩展路径等生态优势。

## 为什么不第一版直接做 Tauri/Rust

Tauri + Rust 是最终产品路线，但第一版需要先验证：

- 哪些预设最稳定；
- 用户需要哪些参数；
- 不同素材的默认策略；
- 导出格式和后处理流程。

Python MVP 可以更快调参，等预设稳定后再迁移到 Tauri。

## 后续可增强模块

1. 自动素材识别：Logo / 照片 / 线稿 / 像素艺术。
2. SVG 二次优化：路径简化、颜色合并、图层命名。
3. 批量队列：失败重试、导出报告、参数模板。
4. 桌面端：Tauri + Rust 直接调用 VTracer。
5. AI 辅助重绘：用于复杂照片或低质量素材的语义重建。
