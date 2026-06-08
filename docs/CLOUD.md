# 云端同步与分享文档

Bitmap Vector Studio v1.2 引入云端同步预览功能，支持将转换结果上传到云端并生成分享链接和 QR 码，实现跨设备查看和协作。

---

## 目录

- [功能概述](#功能概述)
- [分享功能](#分享功能)
- [QR 码生成](#qr-码生成)
- [后端配置](#后端配置)
- [CLI 使用示例](#cli-使用示例)
- [Python API 使用](#python-api-使用)
- [桌面端使用](#桌面端使用)
- [注意事项](#注意事项)

---

## 功能概述

云端同步解决以下场景：

- **跨设备查看**：桌面端转换 SVG，手机扫码即可预览
- **快速分享**：无需发送文件，一个链接即可分享矢量化结果
- **协作审阅**：团队成员通过链接查看、下载、评论
- **临时托管**：转换结果临时托管在云端，7 天后自动过期清理

### 架构

```text
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   CloudSync     │────▶│  CloudBackend   │────▶│ GitHubGistBackend│
│  (高层接口)      │     │  (抽象基类)      │     │  (Gist 存储)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │ LocalServerBackend│
                        │  (本地 HTTP 服务)  │
                        └─────────────────┘
```

- **GitHubGistBackend**：将 SVG 和元数据打包为 Gist，生成公开分享链接。适合个人分享和临时托管。
- **LocalServerBackend**：启动本地 HTTP 服务，在同一局域网内分享。适合内网协作和隐私敏感场景。

---

## 分享功能

### 分享内容

云端同步不仅分享 SVG 文件，还包含完整的转换元数据：

| 字段 | 说明 |
|---|---|
| `svg_content` | SVG 文件内容 |
| `preview_png` | PNG 预览图（Base64） |
| `source_info` | 原图文件名、尺寸、格式 |
| `options` | 转换参数（预设、颜色精度等） |
| `stats` | 路径数、文件大小、耗时 |
| `timestamp` | 转换时间戳 |
| `version` | 生成工具的版本 |

### 分享链接格式

**GitHub Gist**：
```
https://gist.github.com/{username}/{gist-id}
```

**本地服务器**：
```
http://{local-ip}:8080/share/{share-id}
```

---

## QR 码生成

QR 码将分享链接编码为二维码图片，方便移动设备扫描。

### 特性

- 支持标准 QR 码（Version 1-40）
- 自动选择最优纠错级别（L/M/Q/H）
- 输出 PNG 格式，默认尺寸 300×300 像素
- 可自定义前景/背景颜色

### CLI 生成 QR 码

```bash
# 为已有链接生成 QR 码
vector-studio cloud qr https://gist.github.com/jammyfu/abc123

# 指定输出路径和尺寸
vector-studio cloud qr https://gist.github.com/jammyfu/abc123 \
  --output ./share_qr.png --size 400

# 自定义颜色
vector-studio cloud qr https://gist.github.com/jammyfu/abc123 \
  --fg-color "#333333" --bg-color "#ffffff"
```

### Python API 生成 QR 码

```python
from vector_studio.qr_generator import QRCodeGenerator

qr = QRCodeGenerator()
qr.generate(
    url="https://gist.github.com/jammyfu/abc123",
    output_path="share_qr.png",
    size=400,
    fg_color="#333333",
    bg_color="#ffffff"
)
```

---

## 后端配置

### GitHub Gist 后端（默认）

无需额外配置，分享时自动创建公开 Gist。如需使用私有 Gist 或指定账号，配置 Token：

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
vector-studio cloud share result.svg
```

### 本地服务器后端

适合内网协作和隐私敏感场景：

```bash
# 启动本地分享服务器
vector-studio cloud serve --port 8080

# 分享时指定使用本地后端
vector-studio cloud share result.svg --backend local
```

启动后，同一局域网内的设备可通过 `http://{ip}:8080/share/{id}` 访问。

### 配置文件

编辑 `~/.bitmap_vector_studio/config.yaml`：

```yaml
cloud:
  default_backend: gist  # 或 local
  gist:
    token: ghp_xxxxxxxxxxxx  # GitHub Token（可选）
    public: true  # 默认创建公开 Gist
  local:
    port: 8080
    host: 0.0.0.0
    ttl: 604800  # 分享有效期（秒），默认 7 天
```

---

## CLI 使用示例

### 分享转换结果

```bash
# 分享 SVG 文件（默认使用 Gist 后端）
vector-studio cloud share output.svg

# 分享时附带描述
vector-studio cloud share output.svg --description "Logo 矢量化结果"

# 使用本地后端分享
vector-studio cloud share output.svg --backend local

# 分享后自动生成 QR 码
vector-studio cloud share output.svg --qr --qr-output ./qr.png
```

### 列出已分享内容

```bash
# 列出所有分享
vector-studio cloud list

# 列出本地后端的分享
vector-studio cloud list --backend local

# 输出 JSON 格式
vector-studio cloud list --json
```

### 撤销分享

```bash
# 撤销指定分享（Gist ID 或本地 Share ID）
vector-studio cloud revoke abc123def456

# 批量撤销
vector-studio cloud revoke abc123 def456

# 清空所有已过期分享
vector-studio cloud cleanup
```

### 生成 QR 码

```bash
# 为已有链接生成 QR 码
vector-studio cloud qr https://gist.github.com/jammyfu/abc123

# 指定尺寸和颜色
vector-studio cloud qr https://gist.github.com/jammyfu/abc123 \
  --size 500 --fg-color "#000000" --bg-color "#ffffff"
```

### 完整工作流示例

```bash
# 1. 转换图片
vector-studio trace photo.jpg --preset photo --output photo.svg

# 2. 分享到云端并生成 QR 码
vector-studio cloud share photo.svg --qr --qr-output photo_qr.png

# 3. 手机扫描 photo_qr.png 即可查看 SVG

# 4. 稍后撤销分享
vector-studio cloud revoke gist-id-here
```

---

## Python API 使用

### CloudSync 高层接口

```python
from vector_studio.cloud_sync import CloudSync
from pathlib import Path

sync = CloudSync()

# 分享 SVG
share_info = sync.share(
    svg_path=Path("output.svg"),
    description="Logo vectorization result",
    backend="gist"  # 或 "local"
)

print(f"分享链接: {share_info['url']}")
print(f"Share ID: {share_info['id']}")

# 生成 QR 码
qr_path = sync.generate_qr(share_info['url'], output_path=Path("qr.png"))
print(f"QR 码已保存: {qr_path}")

# 列出分享
shares = sync.list_shares()
for s in shares:
    print(f"{s['id']}: {s['url']} ({s['created_at']})")

# 撤销分享
sync.revoke(share_info['id'])
```

### 自定义后端

```python
from vector_studio.cloud_backends import GitHubGistCloudBackend, LocalServerCloudBackend

# GitHub Gist 后端
gist_backend = GitHubGistCloudBackend(token="ghp_xxxxxxxxxxxx")

# 本地服务器后端
local_backend = LocalServerCloudBackend(port=8080, host="0.0.0.0")

# 使用指定后端
from vector_studio.cloud_sync import CloudSync
sync = CloudSync(backend=local_backend)
```

---

## 桌面端使用

v1.2 桌面应用在「导出」菜单中集成云端分享功能：

### 分享操作

1. 转换完成后，点击「文件 → 分享到云端」
2. 选择后端（GitHub Gist / 本地服务器）
3. 可选填写描述信息
4. 点击「分享」，弹出分享链接和 QR 码
5. 点击「复制链接」或「保存 QR 码」

### QR 码预览

分享成功后，桌面端自动显示 QR 码弹窗：
- 右侧显示 QR 码图片
- 下方显示分享链接（可点击复制）
- 提供「保存 QR 码」按钮

### 分享管理

在「工具 → 云端分享管理」中可：
- 查看所有已分享内容列表
- 点击「打开链接」在浏览器中查看
- 点击「撤销」删除分享
- 点击「重新生成 QR 码」

---

## 注意事项

1. **网络依赖**：GitHub Gist 后端需要联网访问 GitHub API。本地服务器后端仅需局域网连接。

2. **隐私安全**：
   - 默认创建的 Gist 为**公开**，任何人可通过链接访问
   - 敏感文件请使用本地服务器后端或手动将 Gist 设为私密
   - 分享链接包含 SVG 完整内容，请勿分享涉密文件

3. **有效期**：
   - GitHub Gist：永久有效（除非手动删除）
   - 本地服务器：默认 7 天后自动清理，可通过配置调整 `ttl`

4. **文件大小限制**：
   - GitHub Gist 单个文件限制 100MB
   - 超大 SVG 建议先优化压缩再分享

5. **本地服务器防火墙**：使用本地后端时，确保防火墙允许对应端口（默认 8080）的入站连接。

6. **跨设备兼容性**：分享的 SVG 在移动端浏览器中可直接预览，但复杂 SVG 在低端设备上可能渲染较慢。

---

<p align="center">
  Made with ❤️ by Bitmap Vector Studio Contributors
</p>
