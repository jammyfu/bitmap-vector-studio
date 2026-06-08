# Examples

本目录包含 Bitmap Vector Studio 的示例素材和输出文件。

## 示例图片

以下测试图片由 `generate_examples.py` 脚本生成：

| 文件 | 描述 | 转换预设 |
|------|------|----------|
| `geometric_shapes.png` | 几何图形（圆形、矩形、三角形、星形） | `logo` |
| `text_sample.png` | 文字排版示例（Vector Studio v0.2.0） | `bw` |
| `gradient_bands.png` | 彩虹色带渐变模拟 | `poster` |

## 示例 SVG 输出

使用项目 CLI 将上述 PNG 转换为 SVG：

```bash
# 几何图形 → SVG (logo 预设，适合图标/Logo)
vector-studio trace examples/geometric_shapes.png --output examples/geometric_shapes.svg --preset logo

# 文字 → SVG (bw 预设，黑白高对比)
vector-studio trace examples/text_sample.png --output examples/text_sample.svg --preset bw

# 色带 → SVG (poster 预设，保留色彩)
vector-studio trace examples/gradient_bands.png --output examples/gradient_bands.svg --preset poster
```

## 批量转换示例

准备一个 `inputs/` 文件夹进行批量转换：

```bash
vector-studio batch ./inputs ./outputs --preset logo --recursive
```

## 建议测试素材

1. 黑白线稿或签名：`--preset bw`
2. Logo / 图标：`--preset logo`
3. 插画或海报：`--preset poster`
4. 照片：`--preset photo`
5. 像素画：`--preset pixel_art`

## 生成新的示例图片

```bash
cd examples
python generate_examples.py
```
