# 实时协作指南

Bitmap Vector Studio v2.0 引入基于 WebSocket 的实时协作编辑功能，支持多人同步编辑同一矢量项目，实现设计团队的无缝协作。

---

## 目录

- [功能概述](#功能概述)
- [快速开始](#快速开始)
- [协作会话管理](#协作会话管理)
- [操作同步机制](#操作同步机制)
- [冲突解决](#冲突解决)
- [在线状态与光标](#在线状态与光标)
- [离线支持](#离线支持)
- [CLI 使用示例](#cli-使用示例)
- [Python API 使用](#python-api-使用)
- [桌面端协作](#桌面端协作)
- [安全与隐私](#安全与隐私)
- [注意事项](#注意事项)

---

## 功能概述

实时协作解决以下场景：

- **团队设计评审**：多人同时查看和编辑同一矢量文件，实时看到彼此的修改
- **远程协作**：设计师、客户、开发者在不同地点同步工作
- **教学演示**：教师实时演示矢量化过程，学生同步观看和操作
- **版本控制替代**：轻量级实时协作，无需复杂的 Git 工作流

### 架构

```text
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   桌面端用户 A   │◄───►│   CollabServer  │◄───►│   桌面端用户 B   │
│  (React + Rust) │     │  (WebSocket)    │     │  (React + Rust) │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  CollabClient   │     │  OperationSync  │     │  PresenceManager│
│  (本地缓存)      │     │  (OT 算法)       │     │  (在线状态)      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

---

## 快速开始

### 创建协作会话

```bash
# 创建一个新的协作会话
vector-studio collab create --name "Project Logo Design"

# 输出：
# Session ID: abc123def456
# Join URL: ws://localhost:8765/collab/abc123def456
# Share this ID with your team members.
```

### 加入协作会话

```bash
# 通过会话 ID 加入
vector-studio collab join abc123def456

# 指定用户名加入
vector-studio collab join abc123def456 --username "Designer Zhang"
```

### 查看协作状态

```bash
vector-studio collab status
```

---

## 协作会话管理

### 会话生命周期

| 状态 | 说明 | 转换条件 |
|---|---|---|
| `created` | 会话已创建，等待参与者 | 创建后自动进入 |
| `active` | 多人正在协作编辑 | 至少 2 人加入 |
| `idle` | 仅剩一人或无人操作 | 其他参与者离开 |
| `closed` | 会话已关闭 | 创建者主动关闭或超时 |

### 会话配置

创建会话时可配置以下参数：

| 参数 | 说明 | 默认值 |
|---|---|---|
| `--name` | 会话名称 | `Untitled Session` |
| `--max-users` | 最大参与人数 | `10` |
| `--password` | 访问密码（可选） | 无 |
| `--ttl` | 会话有效期（分钟） | `1440`（24 小时） |
| `--read-only` | 是否只读模式 | `False` |

```bash
# 创建带密码的只读会话（适合客户评审）
vector-studio collab create --name "Client Review" --password review123 --read-only --max-users 5
```

---

## 操作同步机制

### 同步的操作类型

以下操作会实时同步给所有参与者：

| 操作类型 | 说明 | 同步延迟 |
|---|---|---|
| `path_edit` | 路径节点编辑（添加/删除/移动锚点） | < 50ms |
| `color_change` | 填充/描边颜色修改 | < 50ms |
| `layer_reorder` | 图层顺序调整 | < 50ms |
| `transform` | 位移、旋转、缩放 | < 50ms |
| `parameter_change` | 矢量化参数调整 | < 100ms |
| `preset_apply` | 预设应用 | < 100ms |
| `undo/redo` | 撤销/重做 | < 50ms |

### 操作变换（OT）算法

Bitmap Vector Studio 使用操作变换（Operational Transformation）算法确保并发编辑的一致性：

1. **本地操作立即应用**：用户操作先在本地生效，保证零延迟体验
2. **操作广播**：操作被序列化为 JSON，通过 WebSocket 广播给其他参与者
3. **远程操作变换**：接收到远程操作时，若与本地待发送操作冲突，自动进行变换
4. **最终一致性**：所有参与者在操作完成后达到相同状态

### 操作序列示例

```json
{
  "op_id": "op_abc123",
  "type": "path_edit",
  "target": "path_456",
  "action": "move_node",
  "node_index": 3,
  "new_position": [120, 200],
  "timestamp": 1717824000000,
  "user_id": "user_xyz789"
}
```

---

## 冲突解决

### 冲突场景

| 场景 | 解决策略 | 结果 |
|---|---|---|
| 两人同时编辑同一路径 | OT 算法自动合并 | 保留双方修改 |
| 一人删除路径，一人编辑该路径 | 后到达的操作生效 | 若路径已删除，编辑操作被忽略 |
| 两人同时调整同一参数 | 时间戳优先 | 后提交的值覆盖先提交的值 |
| 离线期间的操作与在线操作冲突 | 版本向量合并 | 提示用户选择或自动合并 |

### 手动冲突解决

当自动合并失败时，系统会弹出冲突解决面板：

```
⚠️ 检测到冲突

路径: logo_main_path

本地修改 (你):
  - 移动节点 3 到 (150, 200)

远程修改 (Designer Li):
  - 删除节点 3

[ 保留本地 ]  [ 保留远程 ]  [ 合并两者 ]
```

---

## 在线状态与光标

### 参与者信息

协作界面显示以下信息：

| 元素 | 说明 |
|---|---|
| **光标** | 每个参与者有唯一颜色的光标，实时显示位置 |
| **选区** | 选中元素时显示半透明遮罩，颜色与光标一致 |
| **用户名标签** | 光标旁显示参与者用户名 |
| **操作提示** | 短暂显示参与者正在进行的操作（如 "正在编辑路径"） |
| **头像/状态** | 右侧面板显示所有在线参与者列表和状态 |

### 光标颜色分配

系统自动为每个参与者分配唯一颜色：

```python
# 预设光标颜色池
CURSOR_COLORS = [
    "#FF5733", "#33FF57", "#3357FF", "#FF33F5",
    "#F5FF33", "#33FFF5", "#FF8C33", "#8C33FF"
]
```

---

## 离线支持

### 离线编辑

网络中断时，协作系统会自动：

1. **切换为本地模式**：继续编辑，操作保存在本地队列
2. **显示离线提示**：状态栏显示「📴 离线模式 - 操作将在恢复后同步」
3. **自动重连**：网络恢复后自动重新加入会话
4. **操作同步**：离线期间的操作按顺序发送给服务器和其他参与者

### 离线队列

```python
from vector_studio.offline_queue import OfflineQueue

queue = OfflineQueue()

# 查看待同步的操作
pending = queue.get_pending_operations()
print(f"待同步操作: {len(pending)}")

# 手动触发同步
queue.sync_now()
```

---

## CLI 使用示例

### 会话管理

```bash
# 创建会话
vector-studio collab create --name "Team Project" --max-users 8

# 加入会话
vector-studio collab join abc123def456 --username "Alice"

# 查看当前会话状态
vector-studio collab status

# 列出所有活跃会话
vector-studio collab list

# 关闭会话（仅创建者可执行）
vector-studio collab close abc123def456

# 踢出参与者（仅创建者可执行）
vector-studio collab kick abc123def456 --user "Bob"
```

### 协作设置

```bash
# 设置协作服务器地址
vector-studio config set collab_server ws://team-server:8765

# 设置默认用户名
vector-studio config set collab_username "MyName"

# 启用/禁用光标显示
vector-studio config set show_remote_cursors true
```

---

## Python API 使用

### CollabClient

```python
from vector_studio.collab_client import CollabClient

client = CollabClient(server_url="ws://localhost:8765")

# 创建会话
session = client.create_session(name="My Project", max_users=5)
print(f"Session ID: {session['id']}")

# 加入会话
client.join_session(session_id="abc123", username="Alice")

# 发送操作
client.send_operation({
    "type": "color_change",
    "target": "path_1",
    "new_color": "#FF5733"
})

# 监听远程操作
@client.on_operation
def handle_remote_op(op):
    print(f"Remote user {op['user_id']} changed {op['target']}")

# 离开会话
client.leave_session()
```

### PresenceManager

```python
from vector_studio.presence_manager import PresenceManager

pm = PresenceManager()

# 获取在线用户
users = pm.get_online_users()
for user in users:
    print(f"{user['username']} - {user['status']} - cursor at {user['cursor']}")

# 更新自己的状态
pm.update_status("editing", target="path_3")
```

---

## 桌面端协作

v2.0 桌面应用新增「协作」面板，提供图形化协作体验：

### 打开协作面板

- 快捷键：`Ctrl+Shift+C`
- 菜单栏：「工具」→「实时协作」

### 界面功能

| 功能 | 说明 |
|---|---|
| 创建会话 | 输入名称，点击「创建」，生成会话 ID 和分享链接 |
| 加入会话 | 输入会话 ID 或扫描二维码加入 |
| 参与者列表 | 显示所有在线用户，含头像、用户名、状态 |
| 聊天面板 | 内置文字聊天，方便协作沟通 |
| 操作历史 | 查看所有参与者的操作记录，支持回滚到任意时间点 |
| 权限管理 | 创建者可设置只读/编辑权限，踢出用户 |

### 协作提示

- 当其他用户编辑你正在查看的元素时，该元素边框会闪烁对应颜色
- 点击参与者头像可「跟随视角」，自动滚动到该用户的视图位置
- 右键点击元素可「请求编辑权」，避免多人同时编辑同一元素

---

## 安全与隐私

### 数据传输

- 所有 WebSocket 通信使用 TLS 加密（`wss://`）
- 操作数据仅包含必要的坐标和参数，不包含完整文件内容
- 会话结束后，操作历史保留 7 天，之后自动清理

### 访问控制

| 功能 | 创建者 | 编辑者 | 只读访客 |
|---|---|---|---|
| 编辑内容 | ✅ | ✅ | ❌ |
| 邀请用户 | ✅ | ❌ | ❌ |
| 踢出用户 | ✅ | ❌ | ❌ |
| 关闭会话 | ✅ | ❌ | ❌ |
| 查看历史 | ✅ | ✅ | ✅ |
| 导出文件 | ✅ | ✅ | ✅ |

### 私有协作服务器

企业用户可部署私有协作服务器：

```bash
# 启动私有协作服务器
vector-studio collab serve --host 0.0.0.0 --port 8765 --max-sessions 100
```

配置文件中设置：

```yaml
collab:
  server: wss://your-company.com:8765
  enable_e2ee: true  # 端到端加密
```

---

## 注意事项

1. **网络要求**：实时协作需要稳定的网络连接，建议延迟 < 200ms。高延迟环境下操作同步会有明显滞后。
2. **并发人数**：建议单个会话不超过 10 人，超过后性能可能下降。大型团队评审建议使用只读模式。
3. **文件大小**：协作编辑的 SVG 文件建议不超过 10MB，超大文件会影响操作同步速度。
4. **浏览器支持**：桌面端协作基于 Tauri WebView，确保系统 WebView 版本较新（WebKit 2.38+ / WebView2 120+）。
5. **操作历史**：操作历史保留 7 天，期间可随时回滚。超过 7 天后仅保留最终状态。
6. **离线同步**：离线期间的大量操作（>1000 条）在恢复时可能需要较长时间同步，建议定期保存本地快照。

---

<p align="center">
  Made with ❤️ by Bitmap Vector Studio Contributors
</p>
