# Docker 使用指南

Bitmap Vector Studio v1.0 提供多阶段 Dockerfile 和 docker-compose.yml，支持以 API 服务或 CLI 工具两种方式运行。

> **v1.0 新增**：桌面应用已作为首选使用方式，Docker 部署适合服务器端 API 服务和自动化流水线场景。详见 [docs/DESKTOP.md](DESKTOP.md)。

---

## 目录

- [构建镜像](#构建镜像)
- [运行 API 服务](#运行-api-服务)
- [运行 CLI](#运行-cli)
- [docker-compose 使用](#docker-compose-使用)
- [环境变量说明](#环境变量说明)
- [数据卷挂载](#数据卷挂载)
- [健康检查](#健康检查)

---

## 构建镜像

### 本地构建

```bash
# 构建默认 target（runtime / API 服务）
docker build -t bitmap-vector-studio .

# 构建 CLI target
docker build --target cli -t bitmap-vector-studio:cli .
```

### 多阶段构建说明

Dockerfile 包含三个阶段：

| 阶段 | 用途 | 基础镜像 | 说明 |
|---|---|---|---|
| `builder` | 编译依赖 | `python:3.11-slim` | 安装编译工具，构建 Python wheel |
| `runtime` | API 服务 | `python:3.11-slim` | 仅保留运行时依赖，启动 API 服务 |
| `cli` | 交互 CLI | `runtime` | 覆盖默认命令为交互式 CLI |

多阶段构建的优势：
- 最终镜像体积小（不包含 gcc、build-essential 等编译工具）
- 构建缓存友好（依赖层独立）
- 安全（减少攻击面）

---

## 运行 API 服务

### 基本运行

```bash
docker run -d \
  --name vs-api \
  -p 8000:8000 \
  bitmap-vector-studio
```

服务启动后：
- API 地址：`http://localhost:8000`
- 健康检查：`http://localhost:8000/health`
- 自动文档：`http://localhost:8000/docs`（FastAPI 自动生成的 Swagger UI）

### 带数据卷运行

```bash
docker run -d \
  --name vs-api \
  -p 8000:8000 \
  -v $(pwd)/outputs:/app/outputs \
  -v $(pwd)/inputs:/app/inputs \
  bitmap-vector-studio
```

### 指定环境变量

```bash
docker run -d \
  --name vs-api \
  -p 8000:8000 \
  -e VECTOR_STUDIO_WORKERS=8 \
  -e VECTOR_STUDIO_HOST=0.0.0.0 \
  bitmap-vector-studio
```

---

## 运行 CLI

### 单次命令

```bash
docker run --rm \
  -v $(pwd)/inputs:/app/inputs \
  -v $(pwd)/outputs:/app/outputs \
  bitmap-vector-studio:cli \
  vector-studio trace /app/inputs/logo.png \
    --output /app/outputs/logo.svg \
    --preset logo
```

### 交互模式

```bash
docker run -it --rm \
  -v $(pwd)/inputs:/app/inputs \
  -v $(pwd)/outputs:/app/outputs \
  bitmap-vector-studio:cli
```

进入容器后可直接使用 `vector-studio` 命令：

```bash
vector-studio presets
vector-studio trace /app/inputs/photo.jpg --preset photo --output /app/outputs/photo.svg
```

---

## docker-compose 使用

项目根目录已包含 `docker-compose.yml`，定义了两个服务：

### 服务定义

| 服务 | Target | 端口 | 用途 |
|---|---|---|---|
| `vector-studio` | `runtime` | `8000:8000` | API 服务 |
| `vector-studio-cli` | `cli` | 无 | 交互式 CLI |

### 启动 API 服务

```bash
# 后台启动
docker-compose up -d vector-studio

# 查看日志
docker-compose logs -f vector-studio

# 停止
docker-compose down
```

### 启动 CLI 服务

```bash
# 进入交互式容器
docker-compose run --rm vector-studio-cli

# 在容器内执行单次命令
docker-compose run --rm vector-studio-cli \
  vector-studio trace /app/inputs/image.png --preset poster
```

### 完整 docker-compose.yml 参考

```yaml
services:
  vector-studio:
    build:
      context: .
      target: runtime
    ports:
      - "8000:8000"
    volumes:
      - ./outputs:/app/outputs
      - ./inputs:/app/inputs
    environment:
      - VECTOR_STUDIO_WORKERS=4
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s

  vector-studio-cli:
    build:
      context: .
      target: cli
    volumes:
      - ./inputs:/app/inputs
      - ./outputs:/app/outputs
    stdin_open: true
    tty: true
    environment:
      - VECTOR_STUDIO_WORKERS=4
```

---

## 环境变量说明

| 环境变量 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `VECTOR_STUDIO_WORKERS` | int | `4` | API 异步任务队列的工作线程数 |
| `VECTOR_STUDIO_HOST` | string | `0.0.0.0` | API 绑定主机（仅影响容器内启动） |
| `VECTOR_STUDIO_PORT` | int | `8000` | API 绑定端口 |

> 注意：目前 CLI 入口通过 `vector-studio api` 命令的 `--host` 和 `--port` 参数控制，环境变量需由启动脚本或入口点读取后传入。如需自定义，可覆盖 `CMD`：
>
> ```bash
> docker run -d -p 8080:8080 bitmap-vector-studio \
>   vector-studio api --host 0.0.0.0 --port 8080 --workers 8
> ```

---

## 数据卷挂载

### 推荐挂载点

| 容器路径 | 用途 | 建议挂载 |
|---|---|---|
| `/app/inputs` | 输入图片目录 | `./inputs:/app/inputs` |
| `/app/outputs` | 输出文件目录 | `./outputs:/app/outputs` |
| `/root/.bitmap_vector_studio` | 用户配置和插件 | 持久化卷或绑定挂载 |

### 持久化配置和插件

```bash
# 创建本地目录
mkdir -p ./vs-config/plugins

# 运行并挂载配置目录
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/vs-config:/root/.bitmap_vector_studio \
  bitmap-vector-studio
```

这样：
- 配置文件 `config.yaml` 会保存在 `./vs-config/config.yaml`
- 用户插件放在 `./vs-config/plugins/` 即可被容器加载
- 历史记录也会持久化到 `./vs-config/history.jsonl`

### 完整生产部署示例

```bash
docker run -d \
  --name bitmap-vector-studio \
  --restart unless-stopped \
  -p 8000:8000 \
  -v /data/vs/inputs:/app/inputs \
  -v /data/vs/outputs:/app/outputs \
  -v /data/vs/config:/root/.bitmap_vector_studio \
  -e VECTOR_STUDIO_WORKERS=8 \
  bitmap-vector-studio
```

---

## 健康检查

### Dockerfile 内置健康检查

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
```

### 查看健康状态

```bash
docker ps
# STATUS 列显示 (healthy) 或 (unhealthy)

# 手动检查
docker exec vs-api curl -f http://localhost:8000/health
```

### docker-compose 健康检查

已在 `docker-compose.yml` 中配置，可通过以下命令查看：

```bash
docker-compose ps
docker-compose exec vector-studio curl -f http://localhost:8000/health
```

---

## 常见问题

### 1. 容器内中文字体缺失

若处理含中文的图片，可能需要安装中文字体：

```dockerfile
# 在 Dockerfile runtime 阶段添加
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*
```

### 2. 大文件上传超时

FastAPI 默认上传限制较大，若遇到超时，可在启动时调整：

```bash
vector-studio api --host 0.0.0.0 --port 8000
# 或使用 uvicorn 直接启动并调整超时
uvicorn vector_studio.api:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 120
```

### 3. 权限问题

若挂载卷后出现权限错误，确保宿主机目录对容器用户可写：

```bash
# 以当前用户身份运行容器
docker run --user $(id -u):$(id -g) \
  -v $(pwd)/outputs:/app/outputs \
  bitmap-vector-studio:cli \
  vector-studio trace /app/inputs/image.png --output /app/outputs/image.svg
```

---

## 构建与推送

### 构建多平台镜像

```bash
docker buildx create --use
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t jammyfu/bitmap-vector-studio:1.0.0 \
  -t jammyfu/bitmap-vector-studio:latest \
  --push .
```

### 仅构建 CLI 镜像

```bash
docker buildx build \
  --target cli \
  --platform linux/amd64,linux/arm64 \
  -t jammyfu/bitmap-vector-studio:1.0.0-cli \
  --push .
```
