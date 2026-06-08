# 多矢量化引擎使用指南

Bitmap Vector Studio v1.2 引入多引擎架构，支持 VTracer、Potrace、AutoTrace 三种矢量化后端，并可根据图像特征自动选择最佳引擎。

---

## 目录

- [支持的引擎](#支持的引擎)
- [引擎特点对比](#引擎特点对比)
- [自动选择逻辑](#自动选择逻辑)
- [手动指定引擎](#手动指定引擎)
- [基准测试](#基准测试)
- [CLI 使用示例](#cli-使用示例)
- [Python API 使用](#python-api-使用)
- [注意事项](#注意事项)

---

## 支持的引擎

| 引擎 | 标识 | 适用场景 | 算法特点 |
|---|---|---|---|
| **VTracer** | `vtracer` | 通用场景、彩色插画、照片 | 基于颜色分层和曲线拟合，保留丰富颜色层次 |
| **Potrace** | `potrace` | 黑白线稿、Logo、印章、扫描件 | 位图追踪算法，输出单色轮廓，路径最简洁 |
| **AutoTrace** | `autotrace` | 照片、复杂图像的中心线提取 | 中心线追踪，适合线条画和技术图纸 |

VTracer 是默认引擎，保留 v1.1 及之前版本的所有行为。Potrace 和 AutoTrace 作为备选引擎，在特定素材类型上可能产生更优结果。

---

## 引擎特点对比

### 质量维度

| 维度 | VTracer | Potrace | AutoTrace |
|---|---|---|---|
| 彩色保留 | ⭐⭐⭐⭐⭐ | ⭐（仅单色） | ⭐⭐⭐ |
| 路径简洁度 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 边缘平滑度 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| 细节还原 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| 文件大小 | 中等 | 最小 | 较小 |

### 速度维度

| 引擎 | 小图 (<1MB) | 中图 (1-10MB) | 大图 (>10MB) |
|---|---|---|---|
| VTracer | 快 | 中等 | 较慢 |
| Potrace | 极快 | 快 | 快 |
| AutoTrace | 快 | 中等 | 较慢 |

---

## 自动选择逻辑

`EngineSelector` 在转换前分析图像特征，自动推荐最佳引擎：

### 特征分析

| 特征 | 检测方式 | 影响 |
|---|---|---|
| 颜色数量 | 颜色直方图统计 | 颜色数 < 8 且为黑白 → 推荐 Potrace |
| 边缘密度 | Sobel 边缘检测 | 高边缘密度 + 低颜色数 → 推荐 Potrace |
| 对比度 | 亮度标准差 | 高对比度 + 单色 → 推荐 Potrace |
| 复杂度 | 颜色梯度分析 | 高复杂度彩色图 → 推荐 VTracer |
| 线条特征 | 中心线密度 | 技术图纸风格 → 推荐 AutoTrace |

### 选择策略

```text
如果 颜色数 <= 2 且 对比度 > 0.8:
    推荐 Potrace
否则如果 中心线密度 > 0.3 且 颜色数 < 16:
    推荐 AutoTrace
否则:
    推荐 VTracer（默认）
```

自动选择可通过 `--engine auto` 显式启用，这也是 v1.2 的默认行为。

---

## 手动指定引擎

### CLI

```bash
# 使用 VTracer（v1.1 及之前版本的默认行为）
vector-studio trace photo.jpg --engine vtracer --preset photo

# 使用 Potrace（适合黑白线稿）
vector-studio trace sketch.png --engine potrace --preset bw

# 使用 AutoTrace（适合中心线提取）
vector-studio trace blueprint.png --engine autotrace --preset scan

# 自动选择（v1.2 默认）
vector-studio trace logo.png --engine auto --preset logo
```

### Python API

```python
from pathlib import Path
from vector_studio import trace_image

# 手动指定引擎
result = trace_image(
    Path("logo.png"),
    preset="logo",
    engine="potrace"  # 或 "vtracer" / "autotrace" / "auto"
)
```

---

## 基准测试

`engine_benchmark` 模块提供标准化引擎对比测试。

### CLI 运行基准测试

```bash
# 运行默认基准测试（使用示例图片集）
vector-studio engine benchmark

# 指定迭代次数
vector-studio engine benchmark --iterations 10

# 指定测试图片目录
vector-studio engine benchmark --input-dir ./test_images

# 输出 JSON 报告
vector-studio engine benchmark --output report.json
```

### 基准测试输出

```json
{
  "engines": {
    "vtracer": {
      "avg_time": 2.34,
      "avg_size": 15360,
      "quality_score": 85,
      "speed_score": 70
    },
    "potrace": {
      "avg_time": 0.56,
      "avg_size": 2048,
      "quality_score": 60,
      "speed_score": 95
    },
    "autotrace": {
      "avg_time": 1.89,
      "avg_size": 8192,
      "quality_score": 75,
      "speed_score": 80
    }
  },
  "recommendations": {
    "photo": "vtracer",
    "bw": "potrace",
    "scan": "autotrace"
  }
}
```

### Python API 运行基准测试

```python
from vector_studio.engine_benchmark import run_benchmark
from pathlib import Path

results = run_benchmark(
    input_dir=Path("./test_images"),
    iterations=5,
    engines=["vtracer", "potrace", "autotrace"]
)

for engine, stats in results.items():
    print(f"{engine}: {stats['avg_time']:.2f}s, score={stats['quality_score']}")
```

---

## CLI 使用示例

### 引擎管理

```bash
# 列出所有可用引擎
vector-studio engine list

# 设置个人默认引擎
vector-studio engine select potrace

# 查看当前默认引擎
vector-studio engine info
```

### 按素材类型选择引擎

```bash
# Logo / 图标 → Potrace（单色、高对比度）
vector-studio trace logo.png --engine potrace --preset bw

# 照片 → VTracer（保留颜色层次）
vector-studio trace photo.jpg --engine vtracer --preset photo

# 蓝图 / 技术图纸 → AutoTrace（中心线提取）
vector-studio trace blueprint.png --engine autotrace --preset scan

# 不确定 → 自动选择
vector-studio trace unknown.png --engine auto
```

### 批量转换指定引擎

```bash
# 批量使用 Potrace 处理线稿
vector-studio batch ./sketches ./outputs --engine potrace --preset bw

# 批量自动选择引擎
vector-studio batch ./mixed ./outputs --engine auto --preset poster
```

---

## Python API 使用

### EngineManager

```python
from vector_studio.engine_manager import EngineManager
from pathlib import Path

manager = EngineManager()

# 列出引擎
for name, info in manager.list_engines().items():
    print(f"{name}: {info['description']}")

# 转换
result = manager.trace(
    input_path=Path("logo.png"),
    engine="potrace",
    preset="bw"
)
```

### EngineSelector

```python
from vector_studio.engine_selector import EngineSelector
from PIL import Image

selector = EngineSelector()

img = Image.open("photo.jpg")
recommendation = selector.recommend(img)

print(f"推荐引擎: {recommendation['engine']}")
print(f"置信度: {recommendation['confidence']}")
print(f"原因: {recommendation['reason']}")
```

---

## 注意事项

1. **引擎依赖**：Potrace 和 AutoTrace 需要系统级二进制文件。首次使用时会自动检测并提示安装：
   - **Potrace**：`apt install potrace`（Ubuntu）/ `brew install potrace`（macOS）
   - **AutoTrace**：`apt install autotrace`（Ubuntu）/ `brew install autotrace`（macOS）
   - Windows 用户需下载对应可执行文件并放入 PATH

2. **缓存隔离**：不同引擎的临时文件相互隔离，切换引擎不会导致缓存冲突。

3. **预设兼容性**：部分预设参数（如 `color_precision`）对 Potrace 无效（Potrace 仅输出单色）。系统会自动忽略不兼容参数并给出警告。

4. **GPU 加速**：目前仅 VTracer 支持 GPU 加速。Potrace 和 AutoTrace 均为 CPU 计算。

5. **自动选择准确率**：`EngineSelector` 对典型素材（Logo、线稿、照片）准确率 > 90%。对艺术化、非标准素材可能推荐偏差，建议手动指定引擎后对比效果。

---

<p align="center">
  Made with ❤️ by Bitmap Vector Studio Contributors
</p>
