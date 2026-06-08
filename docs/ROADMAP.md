# Roadmap

## v0.1：可用 MVP ✅

- [x] VTracer Python 绑定封装
- [x] Streamlit 参数 GUI
- [x] Typer CLI
- [x] 单图转换
- [x] 批量转换
- [x] SVG 清理和统计
- [x] PDF / PNG 可选导出
- [x] EPS 通过 Inkscape CLI 预留

## v0.2：Illustrator-like 体验 ✅

- [x] 原图 / SVG 双栏同步缩放（并排对比模式）
- [x] 转换前后叠加对比（滑块模式）
- [x] 自定义预设保存为 JSON
- [x] 最近任务历史（自动记录、参数复用）
- [x] 输出 SVG 图层命名（按颜色或顺序，Inkscape 兼容）
- [x] 一键打开 Illustrator / Inkscape / Affinity Designer / Figma 等
- [x] 预设分组选择器（内置 + 用户预设）
- [x] SVG 结构分析（图层列表、颜色面板）
- [x] 参数分组折叠面板
- [x] 历史报告导出（CSV / Markdown）
- [x] 预设导入/导出

## v0.3：质量优化 ✅

- [x] 对 logo 自动做背景透明处理
- [x] 图像边缘增强 / 扫描件去噪 / 自适应对比度（Pillow 实现，无 OpenCV）
- [x] SVG 路径合并和颜色合并
- [x] SVG 文件大小评分与优化建议
- [x] 多参数批量试跑并自动挑选最优结果
- [x] 智能预设推荐（根据图片内容自动选择最佳预设）
- [x] 批量任务队列与进度可视化（异步并发、失败重试）

## v0.4：生态与集成 ✅

- [x] 插件系统（Plugin 基类、PluginManager、内置插件、用户自定义插件目录）
- [x] 配置管理（YAML/JSON 配置文件、CLI config 命令组、配置与 CLI 参数合并）
- [x] Web API（FastAPI RESTful API，8 个端点，Python 客户端 SDK，异步任务支持）
- [x] Docker 容器化（多阶段 Dockerfile、docker-compose.yml、健康检查）
- [x] 发布自动化（release.py 脚本、GitHub Actions 自动发布到 PyPI）
- [x] 包管理器模板（Homebrew Formula、Chocolatey、APT deb）
- [x] 一键安装脚本（install.sh 跨平台安装）
- [x] CLI 增强（config/plugin/api 子命令、--config 和 --plugin 选项）

## v0.5：AI 辅助方向 ✅

- [x] AI 辅助重绘：对复杂照片先做语义简化，再进入矢量化
- [x] 文字/Logo OCR：对含文字的图片保留文字结构，而不是全部变 path
- [x] 局部重描摹：用户圈选区域，仅重新生成某一块 SVG
- [x] 实时预览：调整参数时实时显示矢量化效果（无需点击转换）
- [x] 预设市场：在线预设分享与下载平台

## v1.0：桌面产品 ✅

- [x] Tauri + Rust 前端
- [x] 拖拽队列
- [x] 原生文件菜单
- [x] 内置预设市场 / 导入导出
- [x] Windows / macOS / Linux 打包
- [x] 自动更新机制
- [x] 插件市场（图形化浏览、安装、管理插件）
- [x] AI 模型本地推理（ONNX Runtime 轻量级分割与识别）

## v1.1：性能优化与体验打磨 ✅

- [x] 桌面端启动速度优化（Rust 端预加载 Python 环境）
- [x] 大文件处理内存优化（流式读取 + 分块处理）
- [x] GPU 加速预览（CUDA / Metal / OpenCL 后端）
- [x] 多语言 OCR 增强（中文、日文、韩文、阿拉伯文、俄文、德文、法文、西班牙文、英文 + 竖排文字）
- [x] 插件热重载（无需重启应用即可加载新插件）
- [x] 批量任务断点续传
- [x] 自动保存工作区状态（崩溃恢复）

## v1.2：稳定性与生态扩展

- [ ] 更多矢量化引擎支持（potrace 等作为备选后端）
- [ ] 插件 SDK 完善（类型提示、调试工具、示例模板）
- [ ] 云端同步预览（跨设备查看转换结果）
- [ ] 社区贡献者工具链（预设验证、插件审核、文档生成）
- [ ] 自动化测试覆盖率提升到 90%+

## v2.0：AI 原生与实时协作

- [ ] 本地 AI 模型推理（ONNX Runtime 实时分割、风格迁移）
- [ ] 实时协作编辑（WebSocket 多人同步编辑同一项目）
- [ ] 云端预设与插件市场（用户账号体系、付费插件支持）
- [ ] 矢量动画导出（SVG 动画、Lottie 格式支持）
- [ ] 智能批处理工作流（可视化节点编辑器）
- [ ] 跨设备同步（桌面端 ↔ 网页端 ↔ API 服务端状态同步）
