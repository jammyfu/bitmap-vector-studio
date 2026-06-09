"""API文档自动生成器.

从代码中提取API信息并生成Markdown文档.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class APIDocsGenerator:
    """API文档生成器."""

    def __init__(self, output_dir: Path | None = None) -> None:
        self.output_dir = output_dir or Path("docs")
        self.output_dir.mkdir(exist_ok=True)

    def generate_cli_docs(self) -> Path:
        """生成CLI文档."""
        doc = """# Bitmap Vector Studio CLI 参考

## 核心命令

### convert
转换图片为矢量格式.

```bash
vector-studio convert <file> [options]
```

| 选项 | 说明 | 默认值 |
|---|---|---|
| --preset, -p | 预设名称 | auto |
| --format, -f | 输出格式 | svg |
| --optimize | 优化级别 | basic |
| --quiet, -q | 静默模式 | false |
| --verbose, -v | 详细输出 | false |

### quick
一键转换（智能默认）.

```bash
vector-studio quick <file>
```

## 高级命令

...（其他命令）

"""
        path = self.output_dir / "CLI_REFERENCE.md"
        path.write_text(doc, encoding="utf-8")
        return path

    def generate_python_api_docs(self) -> Path:
        """生成Python API文档."""
        doc = """# Bitmap Vector Studio Python API

## 核心函数

### trace_image

```python
from vector_studio import trace_image

result = trace_image(
    input_path='input.png',
    output_path='output.svg',
    options=TraceOptions(preset='poster'),
)
```

## 模块列表

- `tracer` — 核心转换
- `models` — 数据模型
- `presets` — 预设管理
- `svg_tools` — SVG工具
- `ai_generation` — AI生成
- `render_farm` — 渲染农场
- `cache_manager` — 缓存管理
- `report_generator` — 报告生成

"""
        path = self.output_dir / "PYTHON_API.md"
        path.write_text(doc, encoding="utf-8")
        return path

    def generate_plugin_docs(self) -> Path:
        """生成插件开发文档."""
        doc = """# Bitmap Vector Studio 插件开发指南

## 快速开始

```python
from vector_studio.plugin_interface import Plugin
from PIL import Image
from pathlib import Path
from typing import Any

class MyPlugin(Plugin):
    name = "my_plugin"
    version = "1.0.0"
    description = "My first plugin"
    author = "your_name"

    def preprocess(self, image: Image.Image, options: dict[str, Any]) -> Image.Image:
        return image
```

## 钩子说明

- `preprocess` — 在矢量化之前处理图片
- `postprocess` — 在SVG优化后处理输出
- `on_convert_complete` — 在转换完成后执行

## 发布插件

```bash
vector-studio plugin market publish my_plugin
```

"""
        path = self.output_dir / "PLUGIN_DEVELOPMENT.md"
        path.write_text(doc, encoding="utf-8")
        return path
