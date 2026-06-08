# 预设市场文档

Bitmap Vector Studio v1.1 引入预设市场（Preset Market），允许用户浏览、搜索、安装和发布矢量化预设。市场后端基于 GitHub Gist 和 GitHub Repository，无需额外服务器即可实现预设的在线分享与分发。

---

## 目录

- [功能概述](#功能概述)
- [浏览和安装预设](#浏览和安装预设)
- [发布自己的预设](#发布自己的预设)
- [后端配置](#后端配置)
- [CLI 参考](#cli-参考)
- [Python API](#python-api)
- [常见问题](#常见问题)

---

## 功能概述

预设市场解决以下问题：

- **发现**：浏览社区分享的优质预设，覆盖更多设计场景（如「水彩风格」「复古海报」「科技线条」等）。
- **安装**：一键将市场预设安装到本地，与内置预设同等使用。
- **发布**：将自己的调参成果发布到市场，供他人使用。
- **评分**：为已安装的预设打分，帮助优质预设浮出水面。

### 架构

```text
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   PresetMarket  │────▶│  MultiBackend   │────▶│ GitHubGistBackend│
│  (高层接口)      │     │  (聚合+容错)     │     │  (Gist 存储)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │ GitHubRepoBackend│
                        │  (仓库子目录)     │
                        └─────────────────┘
```

- **GitHubGistBackend**：每个预设对应一个 GitHub Gist，适合个人分享少量精品预设。
- **GitHubRepoBackend**：一个 GitHub 仓库的指定子目录存放多个预设 JSON 文件，适合社区集中维护。
- **MultiBackend**：同时查询多个后端，自动去重，任一后端故障不影响其他后端。

---

## 浏览和安装预设

### 通过 CLI

```bash
# 列出市场中的所有预设
vector-studio market list

# 搜索预设
vector-studio market search logo
vector-studio market search photo

# 查看热门预设
vector-studio market popular --limit 10

# 查看某个预设的详细信息
vector-studio market info preset-id

# 安装预设到本地
vector-studio market install preset-id

# 安装时指定本地名称
vector-studio market install preset-id --name my_logo_preset
```

安装后的预设会保存到用户预设目录（`~/.bitmap_vector_studio/presets/`），与 GUI 和 CLI 中的自定义预设同等使用：

```bash
vector-studio trace input.png --preset my_logo_preset
```

### 通过 Python API

```python
from vector_studio import PresetMarket

market = PresetMarket()

# 浏览所有预设
presets = market.discover_presets()
for p in presets:
    print(f"{p['display_name']} by {p['author']} (rating: {p['rating']})")

# 搜索
results = market.search("logo")

# 安装
local_name = market.install("gist-id-here", name="my_preset")
print(f"Installed as: {local_name}")

# 查看热门
popular = market.get_popular(limit=5)
```

---

## 发布自己的预设

### 前置条件

1. **GitHub 账号**：需要一个 GitHub 账号。
2. **Personal Access Token**：
   - 访问 https://github.com/settings/tokens
   - 点击 **Generate new token (classic)**
   - 勾选 `gist` 权限（若发布到 Gist）或 `repo` 权限（若发布到仓库）
   - 生成后复制 Token（仅显示一次）

### 通过 CLI 发布

```bash
# 先创建并保存一个本地预设
vector-studio trace input.png --preset poster --color-precision 7 --filter-speckle 2
# 在 GUI 中点击「保存当前参数为预设」，命名为 "my_poster_preset"

# 发布到市场（使用 --token 参数）
vector-studio market publish my_poster_preset --token ghp_xxxxxxxxxxxx

# 或使用环境变量（推荐，避免 Token 出现在 shell 历史）
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
vector-studio market publish my_poster_preset
```

发布成功后，CLI 会输出市场预设 ID（Gist ID 或文件路径），可用于分享。

### 通过 Python API 发布

```python
from vector_studio import PresetMarket

market = PresetMarket()
preset_id = market.publish("my_poster_preset", auth_token="ghp_xxxxxxxxxxxx")
print(f"Published at: {preset_id}")
```

### 预设元数据

发布时，系统会自动将以下信息打包到预设中：

| 字段 | 来源 | 说明 |
|---|---|---|
| `name` | 本地预设名称 | 唯一标识 |
| `display_name` | 名称自动格式化 | 展示用名称 |
| `description` | GUI 中填写的描述 | 预设用途说明 |
| `options` | 当前预设参数 | 完整的 `TraceOptions` 字典 |
| `version` | 固定 `1.1.0` | 预设版本 |
| `created_at` | 当前 UTC 时间 | ISO 8601 格式 |

---

## 后端配置

默认情况下，预设市场使用官方占位源（`bitmap-vector-studio-official-examples` Gist 和 `bitmap-vector-studio/community-presets` 仓库）。你可以通过配置文件自定义市场源。

### 配置文件示例

编辑 `~/.bitmap_vector_studio/config.yaml`（或 `config.json`）：

```yaml
# 自定义市场源
market_sources:
  - kind: gist
    username: your-github-username
    gist_ids:
      - abc123def456  # 你的个人预设 Gist
  - kind: repo
    owner: your-org
    repo: shared-presets
    branch: main
    path: presets
  - kind: repo
    owner: another-org
    repo: design-assets
    branch: master
    path: vector-studio/presets
```

### 配置字段说明

#### `gist` 类型

| 字段 | 必填 | 说明 |
|---|---|---|
| `kind` | 是 | 固定为 `gist` |
| `username` | 否 | GitHub 用户名，列出该用户的所有公开 Gist |
| `gist_ids` | 否 | 显式指定的 Gist ID 列表 |

> 提示：至少提供 `username` 或 `gist_ids` 之一。

#### `repo` 类型

| 字段 | 必填 | 说明 |
|---|---|---|
| `kind` | 是 | 固定为 `repo` |
| `owner` | 是 | 仓库所有者 |
| `repo` | 是 | 仓库名称 |
| `branch` | 否 | 分支名称，默认 `main` |
| `path` | 否 | 仓库内子目录，默认根目录 |

### 私有仓库 / Gist

若使用私有仓库或私密 Gist 作为市场源，需要在 HTTP 请求中携带 Token。目前 Token 仅用于发布操作；读取私有内容时，可在配置中通过环境变量注入：

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
vector-studio market list
```

> 注意：当前版本读取公开源无需 Token；读取私有源需确保 Token 具有对应权限并在请求头中传递。

---

## CLI 参考

| 命令 | 说明 | 示例 |
|---|---|---|
| `market list` | 列出市场所有预设 | `vector-studio market list` |
| `market search <query>` | 按关键词搜索 | `vector-studio market search logo` |
| `market install <id>` | 安装指定预设 | `vector-studio market install abc123` |
| `market install <id> --name <name>` | 安装并指定本地名称 | `vector-studio market install abc123 --name my_preset` |
| `market publish <name>` | 发布本地预设 | `vector-studio market publish my_preset --token ghp_xxx` |
| `market popular` | 查看热门预设 | `vector-studio market popular --limit 10` |
| `market info <id>` | 查看预设详情 | `vector-studio market info abc123` |

---

## Python API

### 自定义后端

```python
from vector_studio import (
    PresetMarket,
    GitHubGistBackend,
    GitHubRepoBackend,
    MultiBackend,
)

# 单一 Gist 后端
gist_backend = GitHubGistBackend(
    username="jammyfu",
    gist_ids=["abc123", "def456"]
)

# 单一 Repo 后端
repo_backend = GitHubRepoBackend(
    owner="bitmap-vector-studio",
    repo="community-presets",
    branch="main",
    path="presets"
)

# 组合多个后端
backend = MultiBackend([gist_backend, repo_backend])
market = PresetMarket(backend=backend)

# 使用
presets = market.discover_presets()
```

### 评分系统

```python
from vector_studio import PresetMarket

market = PresetMarket()

# 为某个预设打分（1–5 星）
market.rate("gist-id-123", rating=5)

# 查看热门（按评分和下载量排序）
popular = market.get_popular(limit=10)
```

评分数据保存在本地 `~/.bitmap_vector_studio/market/ratings.json`，不会上传到服务器，属于个人本地标记。

---

## 常见问题

**Q: 市场需要联网吗？**
A: 浏览、搜索、安装和发布都需要联网访问 GitHub API。若离线使用，已安装的本地预设不受影响。

**Q: 发布预设是否公开？**
A: 通过 Gist 后端发布时，默认创建 **公开** Gist。如需私密分享，请手动在 GitHub 上将 Gist 设为私密，或改用私有仓库后端。

**Q: 预设 ID 是什么？**
A: 对于 Gist 后端，预设 ID 就是 Gist ID（如 `abc123def456`）；对于 Repo 后端，预设 ID 是文件在仓库中的路径（如 `presets/logo.json`）。

**Q: 安装后的预设可以修改吗？**
A: 可以。安装后的预设与本地自定义预设完全等同，可通过 GUI 或 `preset_manager` API 修改、重命名、删除。

**Q: 市场源配置错误怎么办？**
A: `MultiBackend` 会自动容错。如果某个源无法访问，CLI 会显示警告并继续返回其他源的结果。检查网络连接或 Token 权限后重试即可。
