# Roadmap

## v0.1：可用 MVP

- [x] VTracer Python 绑定封装
- [x] Streamlit 参数 GUI
- [x] Typer CLI
- [x] 单图转换
- [x] 批量转换
- [x] SVG 清理和统计
- [x] PDF / PNG 可选导出
- [x] EPS 通过 Inkscape CLI 预留

## v0.2：Illustrator-like 体验

- [ ] 原图 / SVG 双栏同步缩放
- [ ] 转换前后叠加对比
- [ ] 自定义预设保存为 JSON
- [ ] 最近任务历史
- [ ] 输出 SVG 图层命名
- [ ] 一键打开 Illustrator / Inkscape

## v0.3：质量优化

- [ ] 对 logo 自动做背景透明处理
- [ ] OpenCV 边缘增强 / 扫描件去噪
- [ ] SVG 路径合并和颜色合并
- [ ] SVG 文件大小评分
- [ ] 多参数批量试跑并自动挑选最优结果

## v1.0：桌面产品

- [ ] Tauri + Rust 前端
- [ ] 拖拽队列
- [ ] 原生文件菜单
- [ ] 内置预设市场 / 导入导出
- [ ] Windows / macOS / Linux 打包

## 长线方向

- AI 辅助重绘：对复杂照片先做语义简化，再进入矢量化。
- 文字/Logo OCR：对含文字的图片保留文字结构，而不是全部变 path。
- 局部重描摹：用户圈选区域，仅重新生成某一块 SVG。
