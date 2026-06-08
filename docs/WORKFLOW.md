# 工作流使用指南

Bitmap Vector Studio v2.0 引入可视化节点编辑器，支持通过拖拽式工作流实现复杂的智能批处理任务，将重复性设计工作自动化。

---

## 目录

- [功能概述](#功能概述)
- [快速开始](#快速开始)
- [内置节点库](#内置节点库)
- [工作流模板](#工作流模板)
- [可视化编辑器](#可视化编辑器)
- [CLI 使用示例](#cli-使用示例)
- [Python API 使用](#python-api-使用)
- [工作流执行引擎](#工作流执行引擎)
- [高级用法](#高级用法)
- [注意事项](#注意事项)

---

## 功能概述

智能工作流解决以下场景：

- **批量设计流水线**：Logo 批量矢量化 → 自动优化 → 统一导出 PNG/SVG/PDF
- **照片转插画工作流**：照片 → AI 语义简化 → 智能预设推荐 → 矢量化 → 动画导出
- **扫描件归档**：扫描图 → OCR 文字识别 → 背景透明 → 矢量化 → 分类存储
- **条件分支处理**：根据图片特征自动选择不同处理路径（Logo/照片/线稿）
- **定时自动化**：结合 cron 或 CI/CD，定时执行预设工作流

### 架构

```text
┌─────────────────────────────────────────────────────────────┐
│                    WorkflowEditor (可视化编辑器)              │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐ │
│  │  Input  │───►│ Process │───►│ Branch  │───►│ Output  │ │
│  │  Node   │    │  Node   │    │  Node   │    │  Node   │ │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    WorkflowEngine (执行引擎)                  │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐ │
│  │ 调度器   │───►│ 执行器  │───►│ 监控器  │───►│ 报告器  │ │
│  │Scheduler│    │Executor │    │Monitor  │    │Reporter │ │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 快速开始

### 使用模板创建工作流

```bash
# 列出所有内置模板
vector-studio workflow list

# 使用模板创建工作流
vector-studio workflow create --template logo_batch

# 输出：
# Workflow created: logo_batch_20240608.json
# Edit this file or open in the visual editor.
```

### 执行工作流

```bash
# 执行工作流文件
vector-studio workflow run logo_batch_20240608.json

# 指定输入目录
vector-studio workflow run logo_batch_20240608.json --input-dir ./raw_logos

# 指定输出目录
vector-studio workflow run logo_batch_20240608.json --output-dir ./processed_logos
```

---

## 内置节点库

### 输入节点

| 节点 | 标识 | 说明 | 配置参数 |
|---|---|---|---|
| `file_input` | 📁 | 从目录读取图片文件 | `path`, `pattern`, `recursive` |
| `api_input` | 🌐 | 从 API 接收图片 | `endpoint`, `auth_token` |
| `clipboard_input` | 📋 | 从剪贴板读取 | `format` |
| `batch_input` | 📦 | 批量文件输入 | `paths[]`, `preset` |

### 处理节点

| 节点 | 标识 | 说明 | 配置参数 |
|---|---|---|---|
| `preprocess` | 🔧 | 图像预处理（降噪/缩放/量化） | `denoise`, `max_size`, `posterize` |
| `ai_segment` | 🧠 | AI 语义分割 | `model`, `target` (foreground/background) |
| `ai_style` | 🎨 | AI 风格迁移 | `style_name`, `intensity` |
| `ai_superres` | 🔍 | AI 超分辨率 | `scale`, `denoise` |
| `trace` | ✏️ | 矢量化转换 | `engine`, `preset`, `options` |
| `optimize` | ⚡ | SVG 优化 | `level`, `merge_colors`, `simplify` |
| `ocr` | 📝 | OCR 文字识别 | `lang`, `vertical`, `embed` |
| `remove_bg` | 🪟 | 背景透明 | `method`, `tolerance` |
| `enhance` | ✨ | 图像增强 | `type` (scan/photo/logo/auto) |

### 条件节点

| 节点 | 标识 | 说明 | 配置参数 |
|---|---|---|---|
| `if_image_type` | ❓ | 根据图片类型分支 | `types[]` (logo/photo/scan/bw) |
| `if_size` | 📐 | 根据尺寸分支 | `min_width`, `min_height` |
| `if_color_count` | 🎨 | 根据颜色数分支 | `threshold` |
| `if_file_exists` | 🔍 | 根据文件存在性分支 | `path` |

### 输出节点

| 节点 | 标识 | 说明 | 配置参数 |
|---|---|---|---|
| `file_output` | 💾 | 保存到文件 | `path`, `format`, `overwrite` |
| `api_output` | 🌐 | 发送到 API | `endpoint`, `method` |
| `cloud_share` | ☁️ | 分享到云端 | `backend`, `description` |
| `animate_export` | 🎬 | 导出动画 | `format`, `preset`, `duration` |
| `multi_output` | 📤 | 多格式同时输出 | `formats[]` (svg/pdf/png/lottie/gif/css) |

### 控制节点

| 节点 | 标识 | 说明 | 配置参数 |
|---|---|---|---|
| `loop` | 🔄 | 循环处理 | `count`, `condition` |
| `parallel` | ⚡ | 并行执行 | `branches[]`, `max_workers` |
| `delay` | ⏱️ | 延迟等待 | `seconds` |
| `checkpoint` | 💾 | 保存检查点 | `name`, `auto_resume` |

---

## 工作流模板

v2.0 内置以下工作流模板：

### Logo 批量处理

```json
{
  "name": "logo_batch",
  "description": "批量处理 Logo：背景透明 → 矢量化 → 优化 → 多格式导出",
  "nodes": [
    {"id": "input", "type": "file_input", "config": {"path": "./logos", "pattern": "*.png"}},
    {"id": "bg", "type": "remove_bg", "config": {"method": "smart"}},
    {"id": "trace", "type": "trace", "config": {"engine": "auto", "preset": "logo"}},
    {"id": "opt", "type": "optimize", "config": {"level": "comprehensive"}},
    {"id": "output", "type": "multi_output", "config": {"formats": ["svg", "pdf", "png"]}}
  ],
  "edges": [
    {"from": "input", "to": "bg"},
    {"from": "bg", "to": "trace"},
    {"from": "trace", "to": "opt"},
    {"from": "opt", "to": "output"}
  ]
}
```

### 照片转插画

```json
{
  "name": "photo_to_illustration",
  "description": "照片 → AI 简化 → 矢量化 → 动画导出",
  "nodes": [
    {"id": "input", "type": "file_input", "config": {"path": "./photos"}},
    {"id": "superres", "type": "ai_superres", "config": {"scale": 2}},
    {"id": "simplify", "type": "ai_style", "config": {"style_name": "illustration", "intensity": 0.7}},
    {"id": "trace", "type": "trace", "config": {"preset": "poster", "color_precision": 6}},
    {"id": "animate", "type": "animate_export", "config": {"format": "lottie", "preset": "fade_in_scale"}}
  ],
  "edges": [
    {"from": "input", "to": "superres"},
    {"from": "superres", "to": "simplify"},
    {"from": "simplify", "to": "trace"},
    {"from": "trace", "to": "animate"}
  ]
}
```

### 智能分类处理

```json
{
  "name": "smart_sort",
  "description": "根据图片类型自动选择不同处理路径",
  "nodes": [
    {"id": "input", "type": "file_input", "config": {"path": "./mixed"}},
    {"id": "branch", "type": "if_image_type", "config": {"types": ["logo", "photo", "scan"]}},
    {"id": "logo_path", "type": "trace", "config": {"preset": "logo"}},
    {"id": "photo_path", "type": "trace", "config": {"preset": "photo", "ai_simplify": true}},
    {"id": "scan_path", "type": "trace", "config": {"preset": "scan", "ocr": true}},
    {"id": "output", "type": "file_output", "config": {"path": "./output"}}
  ],
  "edges": [
    {"from": "input", "to": "branch"},
    {"from": "branch", "to": "logo_path", "condition": "logo"},
    {"from": "branch", "to": "photo_path", "condition": "photo"},
    {"from": "branch", "to": "scan_path", "condition": "scan"},
    {"from": "logo_path", "to": "output"},
    {"from": "photo_path", "to": "output"},
    {"from": "scan_path", "to": "output"}
  ]
}
```

---

## 可视化编辑器

v2.0 桌面应用提供可视化节点编辑器：

### 打开编辑器

- 快捷键：`Ctrl+Shift+W`
- 菜单栏：「工具」→「工作流编辑器」

### 界面操作

| 操作 | 说明 |
|---|---|
| 拖拽节点 | 从左侧节点库拖拽节点到画布 |
| 连接节点 | 点击节点输出端口，拖拽到另一个节点的输入端口 |
| 配置节点 | 双击节点打开配置面板 |
| 运行工作流 | 点击顶部「▶ 运行」按钮 |
| 保存工作流 | `Ctrl+S` 保存为 JSON 文件 |
| 导入工作流 | 拖拽 JSON 文件到编辑器窗口 |

### 节点状态指示

| 颜色 | 状态 |
|---|---|
| 🟢 绿色 | 节点执行成功 |
| 🔴 红色 | 节点执行失败 |
| 🟡 黄色 | 节点正在执行 |
| ⚪ 灰色 | 节点等待中 |
| 🔵 蓝色 | 节点被选中 |

---

## CLI 使用示例

### 工作流管理

```bash
# 列出所有模板
vector-studio workflow list

# 从模板创建工作流
vector-studio workflow create --template logo_batch --output my_workflow.json

# 执行工作流
vector-studio workflow run my_workflow.json

# 执行时覆盖参数
vector-studio workflow run my_workflow.json --param input.path=./my_logos --param trace.preset=logo

# 导出工作流为脚本
vector-studio workflow export my_workflow.json --format python --output my_workflow.py

# 验证工作流
vector-studio workflow validate my_workflow.json

# 查看工作流执行历史
vector-studio workflow history
```

### 定时执行

结合系统 cron 定时执行工作流：

```bash
# 每天凌晨 2 点执行批量处理
0 2 * * * /usr/local/bin/vector-studio workflow run /path/to/daily_batch.json >> /var/log/vs_workflow.log 2>&1
```

---

## Python API 使用

### WorkflowEngine

```python
from vector_studio.workflow_engine import WorkflowEngine
from pathlib import Path

engine = WorkflowEngine()

# 加载工作流
engine.load(Path("my_workflow.json"))

# 执行工作流
result = engine.run()
print(f"处理完成: {result['processed']} 个文件")
print(f"成功: {result['success']}, 失败: {result['failed']}")

# 查看执行报告
for step in result['steps']:
    print(f"{step['node']}: {step['status']} ({step['duration']:.2f}s)")
```

### WorkflowEditor（程序化构建）

```python
from vector_studio.workflow_editor import WorkflowEditor
from vector_studio.workflow_nodes import FileInputNode, TraceNode, MultiOutputNode

editor = WorkflowEditor()

# 添加节点
input_node = editor.add_node(FileInputNode(path="./images", pattern="*.png"))
trace_node = editor.add_node(TraceNode(engine="auto", preset="poster"))
output_node = editor.add_node(MultiOutputNode(formats=["svg", "pdf"]))

# 连接节点
editor.connect(input_node, trace_node)
editor.connect(trace_node, output_node)

# 保存工作流
editor.save(Path("my_workflow.json"))

# 直接执行
result = editor.run()
```

### 自定义节点

```python
from vector_studio.workflow_nodes import BaseNode

class WatermarkNode(BaseNode):
    name = "custom_watermark"
    description = "添加自定义水印"
    
    def __init__(self, text, color="#999999"):
        self.text = text
        self.color = color
    
    def execute(self, input_data):
        svg = input_data['svg']
        # 在 SVG 中添加水印
        svg.add_watermark(self.text, self.color)
        return {"svg": svg}

# 注册并使用自定义节点
from vector_studio.workflow_engine import WorkflowEngine
engine = WorkflowEngine()
engine.register_node(WatermarkNode)
```

---

## 工作流执行引擎

### 执行模式

| 模式 | 说明 | 适用场景 |
|---|---|---|
| `sequential` | 顺序执行，一个节点完成后执行下一个 | 依赖关系明确的流水线 |
| `parallel` | 并行执行无依赖关系的节点 | 独立预处理任务 |
| `pipeline` | 流式执行，前一个节点的输出直接流入下一个 | 大文件处理 |

### 错误处理策略

| 策略 | 说明 | 配置方式 |
|---|---|---|
| `stop` | 遇到错误立即停止整个工作流 | `"on_error": "stop"` |
| `skip` | 跳过当前节点，继续执行后续节点 | `"on_error": "skip"` |
| `retry` | 重试当前节点（最多 3 次） | `"on_error": "retry"` |
| `fallback` | 切换到备用节点执行 | `"on_error": "fallback", "fallback_node": "id"` |

### 进度监控

```python
from vector_studio.workflow_engine import WorkflowEngine

engine = WorkflowEngine()

@engine.on_progress
def on_progress(progress):
    print(f"进度: {progress['percent']}% - 当前节点: {progress['current_node']}")

@engine.on_node_complete
def on_node_complete(node_id, result):
    print(f"节点 {node_id} 完成，输出: {result}")

engine.run()
```

---

## 高级用法

### 条件分支动态路由

```json
{
  "nodes": [
    {
      "id": "smart_branch",
      "type": "if_image_type",
      "config": {
        "types": ["logo", "photo"],
        "confidence_threshold": 0.8
      }
    }
  ]
}
```

### 并行批处理

```json
{
  "nodes": [
    {
      "id": "parallel_process",
      "type": "parallel",
      "config": {
        "branches": [
          [{"type": "trace", "preset": "bw"}],
          [{"type": "trace", "preset": "poster"}],
          [{"type": "trace", "preset": "photo"}]
        ],
        "max_workers": 3
      }
    }
  ]
}
```

### 循环处理

```json
{
  "nodes": [
    {
      "id": "retry_loop",
      "type": "loop",
      "config": {
        "condition": "error_rate > 0.1",
        "max_iterations": 5,
        "delay": 2
      }
    }
  ]
}
```

---

## 注意事项

1. **循环检测**：工作流引擎会自动检测循环依赖并拒绝执行。确保节点连接形成有向无环图（DAG）。
2. **内存管理**：并行节点同时执行时可能占用大量内存，建议根据系统配置调整 `max_workers`。
3. **文件路径**：工作流 JSON 中的路径支持相对路径（相对于工作流文件位置）和绝对路径。
4. **节点兼容性**：部分节点组合可能不兼容（如 `ai_superres` 后接 `remove_bg` 顺序可能影响效果），建议参考模板配置。
5. **执行日志**：工作流执行日志保存在 `~/.bitmap_vector_studio/workflows/logs/`，包含详细的节点输入输出和错误堆栈。
6. **版本兼容**：工作流 JSON 包含 `version` 字段，未来版本升级时会自动迁移旧版工作流。

---

<p align="center">
  Made with ❤️ by Bitmap Vector Studio Contributors
</p>
