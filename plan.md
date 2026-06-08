# Bitmap Vector Studio 推进计划 v1.0

## 项目现状
- v0.5.0 已完成并推送到 GitHub: https://github.com/jammyfu/bitmap-vector-studio
- 419 个测试全部通过
- 具备：AI辅助、实时预览、局部重描摹、预设市场、插件系统、Web API、Docker

## 目标版本: v1.0.0 — 桌面产品

### Stage 1: Tauri 项目搭建
1. **初始化 Tauri 项目**
   - 在 `desktop/` 目录下初始化 Tauri + React 项目
   - 配置 `Cargo.toml` 和 `tauri.conf.json`
   - 设置窗口标题、图标、尺寸、菜单
   - 配置原生文件菜单（File, Edit, View, Help）

2. **Python 后端桥接**
   - 创建 `desktop/src-tauri/src/python_bridge.rs`
   - 使用 Tauri Command 调用 Python 脚本
   - 支持通过子进程调用 `vector-studio` CLI
   - 支持通过 HTTP 调用本地 API 服务

### Stage 2: 前端 UI 开发
3. **主窗口布局**
   - 左侧：文件队列 + 预设选择
   - 中间：参数面板
   - 右侧：预览区域（原图/SVG对比）
   - 底部：状态栏 + 进度条

4. **文件拖拽队列**
   - 拖拽区域支持多文件拖入
   - 队列列表显示：文件名、状态、进度
   - 支持开始/暂停/取消/清除队列
   - 支持队列排序和删除单个任务

5. **参数面板**
   - 预设选择下拉框（内置+用户预设）
   - 参数滑块（颜色精度、滤斑点、角点阈值等）
   - 预处理选项（降噪、背景透明、AI简化）
   - 导出选项（SVG/PDF/PNG、优化级别）

6. **预览区域**
   - 并排对比（原图/SVG）
   - 叠加对比滑块
   - 缩放和平移
   - 局部重描摹选区工具

### Stage 3: 功能集成
7. **预设市场集成**
   - 市场浏览器窗口
   - 搜索、安装、发布预设

8. **插件市场集成**
   - 插件列表
   - 启用/禁用/安装插件

9. **设置面板**
   - 通用设置（语言、主题）
   - 输出设置（默认目录、格式）
   - 外部编辑器配置
   - API服务配置

### Stage 4: 打包与发布
10. **自动更新机制**
    - 配置 Tauri 自动更新
    - GitHub Release 作为更新源
    - 更新检查、下载、安装

11. **多平台打包**
    - Windows: MSI/NSIS 安装包
    - macOS: DMG/App 打包
    - Linux: AppImage/DEB/RPM
    - 打包脚本和 CI 配置

### Stage 5: 测试与文档
12. **测试**
    - Rust 单元测试
    - 前端组件测试
    - E2E 测试
13. **文档更新**
    - README 桌面版说明
    - 安装指南
    - CHANGELOG v1.0

## 提交策略
每完成一个Stage就提交并推送到GitHub。

## 当前时间锚点
- 开发周期: v1.0.0
- 目标: 原生桌面应用体验
