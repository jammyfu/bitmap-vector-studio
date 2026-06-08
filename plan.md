# Bitmap Vector Studio 推进计划 v0.4

## 项目现状
- v0.3.0 已完成并推送到 GitHub: https://github.com/jammyfu/bitmap-vector-studio
- 267 个测试全部通过
- 具备：智能预处理、SVG优化、参数搜索、批量队列、GUI增强

## 目标版本: v0.4.0 — 生态与集成

### Stage 1: 插件系统与配置（可并行）
1. **插件系统**
   - 文件: `src/vector_studio/plugins.py` + `src/vector_studio/plugin_interface.py`
   - 功能: 允许用户编写自定义后处理插件（Python文件放入plugins目录自动加载）
   - 插件类型: 预处理插件、后处理插件、导出插件、报告插件
   - 提供Plugin基类和装饰器注册机制

2. **配置文件支持**
   - 文件: `src/vector_studio/config.py`
   - 功能: YAML/JSON配置文件解析，支持批量参数模板
   - CLI集成: `vector-studio trace config.yaml` 支持从配置文件读取参数
   - 配置项: 默认预设、输出目录、优化级别、插件启用、外部编辑器偏好

### Stage 2: Web API模式
3. **FastAPI封装**
   - 文件: `src/vector_studio/api.py`
   - 功能: RESTful API提供图片上传、转换、状态查询、结果下载
   - 端点: /convert, /batch, /status, /download, /presets, /recommend
   - 支持异步任务（基于TaskQueue）
   - 自动API文档（/docs）
   - CLI集成: `vector-studio api --host 0.0.0.0 --port 8000`

### Stage 3: 容器与发布
4. **Docker镜像**
   - 文件: `Dockerfile`, `docker-compose.yml`, `.dockerignore`
   - 功能: 多阶段构建，包含VTracer和CairoSVG
   - 支持API模式和CLI模式
   - 提供docker-compose一键启动

5. **包管理器发布准备**
   - 文件: `scripts/release.py`, `.github/workflows/release.yml`
   - 功能: 自动化版本发布流程
   - PyPI发布配置
   - Homebrew formula模板
   - Chocolatey包模板
   - APT deb包构建脚本

### Stage 4: GUI与CLI集成
6. **Streamlit GUI v0.4升级**
   - 插件管理面板（启用/禁用/配置插件）
   - 配置文件导入/导出
   - API模式状态显示

7. **CLI增强**
   - `vector-studio config` 命令组（查看/编辑/验证配置）
   - `vector-studio plugin` 命令组（列表/启用/禁用/安装）
   - `vector-studio api` 命令启动服务器

### Stage 5: 测试与文档
8. **测试增强**
   - 插件系统测试
   - API端点测试（TestClient）
   - 配置解析测试
9. **文档更新**
   - README更新v0.4功能
   - API文档
   - Docker使用指南
   - 插件开发指南

## 提交策略
每完成一个Stage就提交并推送到GitHub。

## 当前时间锚点
- 开发周期: v0.4.0
- 目标: 生态扩展、远程调用、容器化、可插拔架构
