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

## v0.3：质量优化

- [ ] 对 logo 自动做背景透明处理
- [ ] OpenCV 边缘增强 / 扫描件去噪
- [ ] SVG 路径合并和颜色合并
- [ ] SVG 文件大小评分与优化建议
- [ ] 多参数批量试跑并自动挑选最优结果
- [ ] 智能预设推荐（根据图片内容自动选择最佳预设）
- [ ] 批量任务队列与进度可视化

## v0.4：生态与集成

- [ ] 插件系统（允许用户编写自定义后处理插件）
- [ ] 预设市场 / 在线预设分享
- [ ] 命令行配置文件支持（YAML/JSON 批量参数模板）
- [ ] Docker 镜像发布
- [ ] Homebrew / Chocolatey / APT 包发布

## v1.0：桌面产品

- [ ] Tauri + Rust 前端
- [ ] 拖拽队列
- [ ] 原生文件菜单
- [ ] 内置预设市场 / 导入导出
- [ ] Windows / macOS / Linux 打包
- [ ] 自动更新机制

## 长线方向

- AI 辅助重绘：对复杂照片先做语义简化，再进入矢量化。
- 文字/Logo OCR：对含文字的图片保留文字结构，而不是全部变 path。
- 局部重描摹：用户圈选区域，仅重新生成某一块 SVG。
- 实时预览：调整参数时实时显示矢量化效果（无需点击转换）。
