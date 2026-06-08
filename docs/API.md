# API 文档

Bitmap Vector Studio v1.2 提供基于 FastAPI 的 RESTful API，支持同步/异步位图转矢量转换、批量任务、预设查询和智能推荐。

> **v1.1 新增**：桌面应用通过 Tauri Command 桥接 Python 后端，提供与 Web API 等价的功能。详见 [docs/DESKTOP.md](DESKTOP.md)。

---

## 目录

- [启动服务](#启动服务)
- [端点列表](#端点列表)
- [请求/响应示例](#请求响应示例)
- [错误码说明](#错误码说明)
- [Python 客户端](#python-客户端)
- [curl 示例](#curl-示例)

---

## 启动服务

### 通过 CLI 启动

```bash
# 默认启动（127.0.0.1:8000）
vector-studio api

# 指定主机和端口
vector-studio api --host 0.0.0.0 --port 8000

# 指定工作进程数
vector-studio api --host 0.0.0.0 --port 8000 --workers 4
```

### 通过 Docker 启动

```bash
docker run -d -p 8000:8000 jammyfu/bitmap-vector-studio
```

### 通过 Docker Compose 启动

```bash
docker-compose up -d vector-studio
```

服务启动后，访问 `http://localhost:8000/health` 验证运行状态。

---

## 端点列表

| 端点 | 方法 | 说明 | 请求类型 |
|---|---|---|---|
| `/health` | GET | 健康检查 | - |
| `/presets` | GET | 列出所有内置预设 | - |
| `/convert` | POST | 同步转换，直接返回 SVG 文件 | `multipart/form-data` |
| `/convert/async` | POST | 异步转换，返回任务 ID | `multipart/form-data` |
| `/status/{task_id}` | GET | 查询异步任务状态 | - |
| `/download/{task_id}/{format}` | GET | 下载已完成任务的结果 | - |
| `/recommend` | POST | 上传图片获取智能预设推荐 | `multipart/form-data` |
| `/batch` | POST | 批量异步转换多张图片 | `multipart/form-data` |
| `/gpu/status` | GET | **v1.1** 查询 GPU 加速状态 | - |
| `/performance` | GET | **v1.1** 查询内存和性能指标 | - |
| `/checkpoint` | POST | **v1.1** 创建批量任务检查点 | `application/json` |
| `/checkpoint/{id}` | GET | **v1.1** 查询检查点状态 | - |
| `/workspace` | POST | **v1.1** 保存工作区 | `application/json` |
| `/workspace/{name}` | GET | **v1.1** 加载工作区 | - |
| `/ocr/detect` | POST | **v1.1** 检测文字区域 | `multipart/form-data` |
| `/ocr/recognize` | POST | **v1.1** 识别文字内容 | `multipart/form-data` |

---

## 请求/响应示例

### GET `/health`

**响应 200：**

```json
{
  "status": "ok",
  "version": "1.2.0"
}
```

---

### GET `/presets`

**响应 200：**

```json
[
  {
    "name": "bw",
    "colormode": "binary",
    "hierarchical": "stacked",
    "mode": "spline",
    "color_precision": 6,
    "layer_difference": 16,
    "filter_speckle": 4
  },
  {
    "name": "poster",
    "colormode": "color",
    "hierarchical": "stacked",
    "mode": "spline",
    "color_precision": 6,
    "layer_difference": 16,
    "filter_speckle": 4
  }
]
```

---

### POST `/convert`

同步转换单张图片，直接返回 SVG 文件。

**请求参数（Form Data）：**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `file` | File | 是 | 位图文件（PNG/JPG/WEBP/BMP/TIFF） |
| `preset` | string | 否 | 预设名称，默认 `poster` |
| `options` | string | 否 | JSON 字符串，覆盖预设参数 |

**curl 示例：**

```bash
curl -X POST "http://localhost:8000/convert" \
  -F "file=@logo.png" \
  -F "preset=logo" \
  -F "options={\"color_precision\": 7, \"filter_speckle\": 2}" \
  --output logo.svg
```

**响应 200：** 返回 `image/svg+xml` 文件。

**响应 400：**

```json
{
  "detail": "Unsupported input format: .gif. Supported: .bmp, .jpg, .jpeg, .png, .tif, .tiff, .webp"
}
```

**响应 500：**

```json
{
  "detail": "Conversion failed: ..."
}
```

---

### POST `/convert/async`

启动异步转换任务，立即返回任务 ID。

**请求参数（Form Data）：**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `file` | File | 是 | 位图文件 |
| `preset` | string | 否 | 预设名称，默认 `poster` |
| `options` | string | 否 | JSON 字符串，覆盖预设参数 |

**curl 示例：**

```bash
curl -X POST "http://localhost:8000/convert/async" \
  -F "file=@photo.jpg" \
  -F "preset=photo" \
  -F "options={\"color_precision\": 8}"
```

**响应 200：**

```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "pending"
}
```

---

### GET `/status/{task_id}`

查询异步任务状态。

**curl 示例：**

```bash
curl "http://localhost:8000/status/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

**响应 200（进行中）：**

```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "running",
  "progress": 0.5,
  "result": null,
  "error": null,
  "created_at": "2026-06-08T12:00:00",
  "started_at": "2026-06-08T12:00:01",
  "completed_at": null
}
```

**响应 200（已完成）：**

```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "completed",
  "progress": 1.0,
  "result": {
    "svg_path": "/tmp/vs-api-xxx/uploads/xxx/photo.svg",
    "duration": 2.34,
    "stats": { "paths": 42, "file_size": 15360 }
  },
  "error": null,
  "created_at": "2026-06-08T12:00:00",
  "started_at": "2026-06-08T12:00:01",
  "completed_at": "2026-06-08T12:00:03"
}
```

**响应 404：**

```json
{
  "detail": "Task not found: a1b2c3d4-..."
}
```

---

### GET `/download/{task_id}/{format}`

下载已完成任务的结果文件。

**路径参数：**

| 参数 | 类型 | 说明 |
|---|---|---|
| `task_id` | string | 异步任务 ID |
| `format` | string | 格式：`svg`、`pdf`、`png` |

**curl 示例：**

```bash
# 下载 SVG
curl "http://localhost:8000/download/a1b2c3d4-.../svg" --output result.svg

# 下载 PDF
curl "http://localhost:8000/download/a1b2c3d4-.../pdf" --output result.pdf

# 下载 PNG 预览
curl "http://localhost:8000/download/a1b2c3d4-.../png" --output result.png
```

**响应 200：** 返回对应格式的文件。

**响应 400（任务未完成）：**

```json
{
  "detail": "Task is not completed yet. Current status: running"
}
```

**响应 404：**

```json
{
  "detail": "Task not found: a1b2c3d4-..."
}
```

---

### POST `/recommend`

上传图片获取智能预设推荐。

**请求参数（Form Data）：**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `file` | File | 是 | 位图文件 |

**curl 示例：**

```bash
curl -X POST "http://localhost:8000/recommend" \
  -F "file=@logo.png"
```

**响应 200：**

```json
{
  "preset": "logo",
  "confidence": 0.92,
  "reason": "Low color count, high edge density, near-square aspect ratio",
  "features": {
    "color_count": 4,
    "edge_density": 0.35,
    "aspect_ratio": 1.02,
    "symmetry": 0.88
  }
}
```

---

### POST `/batch`

批量异步转换多张图片。

**请求参数（Form Data）：**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `files` | File[] | 是 | 多个位图文件（字段名均为 `files`） |
| `preset` | string | 否 | 预设名称，默认 `poster` |
| `options` | string | 否 | JSON 字符串，覆盖预设参数 |

**curl 示例：**

```bash
curl -X POST "http://localhost:8000/batch" \
  -F "files=@image1.png" \
  -F "files=@image2.jpg" \
  -F "files=@image3.png" \
  -F "preset=poster"
```

**响应 200：**

```json
{
  "task_ids": [
    "task-id-1",
    "task-id-2",
    "task-id-3"
  ]
}
```

---

## 错误码说明

| HTTP 状态码 | 说明 | 常见场景 |
|---|---|---|
| 200 | 成功 | 正常响应 |
| 400 | 请求参数错误 | 不支持的文件格式、无效的 options JSON、任务未完成时下载 |
| 404 | 资源未找到 | 任务 ID 不存在、输出文件已过期 |
| 500 | 服务器内部错误 | 转换过程异常、PDF/PNG 导出失败 |

---

## Python 客户端

Bitmap Vector Studio 内置标准库客户端 `VectorStudioClient`，零第三方依赖。

### 基础用法

```python
from pathlib import Path
from vector_studio.api_client import VectorStudioClient

client = VectorStudioClient("http://localhost:8000")

# 检查服务健康
health = client.health()
print(health)  # {'status': 'ok', 'version': '1.2.0'}
```

### 同步转换

```python
from pathlib import Path
from vector_studio.api_client import VectorStudioClient

client = VectorStudioClient("http://localhost:8000")

svg_bytes = client.convert(
    Path("logo.png"),
    preset="logo",
    options={"color_precision": 7, "filter_speckle": 2}
)
Path("output.svg").write_bytes(svg_bytes)
```

### 异步转换与轮询

```python
import time
from pathlib import Path
from vector_studio.api_client import VectorStudioClient

client = VectorStudioClient("http://localhost:8000")

# 提交异步任务
task_id = client.convert_async(Path("photo.jpg"), preset="photo")
print(f"Task ID: {task_id}")

# 轮询状态
while True:
    status = client.get_status(task_id)
    print(f"Status: {status['status']}, Progress: {status['progress']}")
    if status["status"] in ("completed", "failed"):
        break
    time.sleep(1)

# 下载结果
if status["status"] == "completed":
    svg_bytes = client.download(task_id, format="svg")
    Path("result.svg").write_bytes(svg_bytes)
```

### 批量转换

```python
from pathlib import Path
from vector_studio.api_client import VectorStudioClient

client = VectorStudioClient("http://localhost:8000")

images = [Path("a.png"), Path("b.png"), Path("c.png")]
task_ids = client.batch_convert(images, preset="poster")
print(f"Created {len(task_ids)} tasks")

# 等待所有任务完成
for tid in task_ids:
    # ... 轮询并下载
    pass
```

### 智能推荐

```python
from pathlib import Path
from vector_studio.api_client import VectorStudioClient

client = VectorStudioClient("http://localhost:8000")

result = client.recommend(Path("unknown.png"))
print(f"Recommended preset: {result['preset']} (confidence: {result['confidence']})")
print(f"Reason: {result['reason']}")
```

---

## curl 示例

### 健康检查

```bash
curl "http://localhost:8000/health"
```

### 列出预设

```bash
curl "http://localhost:8000/presets" | python -m json.tool
```

### 同步转换

```bash
curl -X POST "http://localhost:8000/convert" \
  -F "file=@input.png" \
  -F "preset=poster" \
  --output result.svg
```

### 异步转换

```bash
# 提交任务
TASK=$(curl -s -X POST "http://localhost:8000/convert/async" \
  -F "file=@input.png" \
  -F "preset=logo" | python -c "import sys,json; print(json.load(sys.stdin)['task_id'])")

# 查询状态
curl "http://localhost:8000/status/$TASK"

# 下载结果
curl "http://localhost:8000/download/$TASK/svg" --output result.svg
```

### 批量转换

```bash
curl -X POST "http://localhost:8000/batch" \
  -F "files=@img1.png" \
  -F "files=@img2.jpg" \
  -F "preset=bw"
```

### 智能推荐

```bash
curl -X POST "http://localhost:8000/recommend" \
  -F "file=@logo.png" | python -m json.tool
```

---

## 桌面端 API（Tauri Command）

v1.1 桌面应用通过 Tauri Command 桥接 Python 后端，提供与 Web API 等价的功能，并新增性能、工作区、检查点、OCR 多语言相关 Command。所有 Command 均为异步，前端通过 `@tauri-apps/api` 调用。

### Command 列表

| Command | 参数 | 返回值 | 说明 |
|---|---|---|---|
| `trace_image` | `{ filePath, options }` | `{ svgPath, stats, duration }` | 单图转换 |
| `batch_convert` | `{ filePaths, options }` | `{ taskIds }` | 批量转换 |
| `get_presets` | - | `Preset[]` | 获取所有预设 |
| `save_preset` | `{ name, options, description }` | `{ success }` | 保存用户预设 |
| `delete_preset` | `{ name }` | `{ success }` | 删除用户预设 |
| `get_history` | `{ limit? }` | `TaskRecord[]` | 获取历史任务 |
| `clear_history` | - | `{ success }` | 清空历史 |
| `export_history` | `{ format, path? }` | `{ filePath }` | 导出历史报告 |
| `get_plugins` | - | `PluginInfo[]` | 获取插件列表 |
| `enable_plugin` | `{ name }` | `{ success }` | 启用插件 |
| `disable_plugin` | `{ name }` | `{ success }` | 禁用插件 |
| `get_market_presets` | `{ backend?, query? }` | `MarketPreset[]` | 获取市场预设 |
| `install_market_preset` | `{ id, backend? }` | `{ success }` | 安装市场预设 |
| `publish_preset` | `{ name, token, backend? }` | `{ presetId }` | 发布预设到市场 |
| `open_file_dialog` | `{ multiple?, filters? }` | `string[]` | 打开文件对话框 |
| `save_file_dialog` | `{ defaultName?, filter? }` | `string` | 保存文件对话框 |
| `check_update` | - | `{ hasUpdate, version, url }` | 检查更新 |
| `install_update` | - | `{ success }` | 安装更新 |
| `get_app_version` | - | `string` | 获取应用版本 |
| `show_notification` | `{ title, body }` | `{ success }` | 显示系统通知 |
| `get_gpu_status` | - | `{ available, backend, memory? }` | **v1.1** 查询 GPU 状态 |
| `get_performance` | - | `{ memory, cpu, cache }` | **v1.1** 查询性能指标 |
| `save_workspace` | `{ name }` | `{ success }` | **v1.1** 保存工作区 |
| `load_workspace` | `{ name }` | `{ files, options }` | **v1.1** 加载工作区 |
| `list_workspaces` | - | `string[]` | **v1.1** 列出工作区 |
| `create_checkpoint` | `{ taskIds, options }` | `{ checkpointId }` | **v1.1** 创建检查点 |
| `resume_checkpoint` | `{ checkpointId }` | `{ restored, taskIds }` | **v1.1** 恢复检查点 |
| `list_checkpoints` | - | `CheckpointInfo[]` | **v1.1** 列出检查点 |
| `ocr_detect` | `{ filePath }` | `{ regions }` | **v1.1** 检测文字区域 |
| `ocr_recognize` | `{ filePath, lang? }` | `{ text, regions }` | **v1.1** 识别文字 |
| `get_ocr_languages` | - | `LanguageInfo[]` | **v1.1** 获取支持的语言列表 |

### 前端调用示例

```typescript
import { invoke } from '@tauri-apps/api/tauri';

// 单图转换
const result = await invoke('trace_image', {
  filePath: '/path/to/image.png',
  options: { preset: 'logo', color_precision: 7 }
});

// 获取预设列表
const presets = await invoke('get_presets');

// 打开文件对话框
const files = await invoke('open_file_dialog', {
  multiple: true,
  filters: [{ name: 'Images', extensions: ['png', 'jpg', 'webp'] }]
});
```

---

## 注意事项

1. **临时文件**：API 使用临时目录存储上传文件和转换结果。同步转换（`/convert`）在响应后自动清理；异步转换（`/convert/async`）的结果在任务完成后保留，但重启服务后会丢失。生产环境建议挂载持久化卷。
2. **并发限制**：异步任务使用全局 `TaskQueue`，默认 4 个工作线程。可通过 `VECTOR_STUDIO_WORKERS` 环境变量调整。
3. **CORS**：API 默认允许所有跨域请求（`allow_origins=["*"]`），生产环境建议根据实际需求限制。
4. **文件大小**：FastAPI 默认上传限制为单个文件，若需处理超大图片，建议在客户端先压缩或调整 `max_input_side`，或启用 v1.1 的 `--stream` 流式处理模式。
