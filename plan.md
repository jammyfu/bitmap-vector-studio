# Bitmap Vector Studio 推进计划

## 项目现状
- v0.1.0 MVP 已完成：VTracer封装、Streamlit GUI、Typer CLI、批量转换、SVG清理/统计、PDF/PNG导出
- 已推送到 GitHub: https://github.com/jammyfu/bitmap-vector-studio

## 目标版本: v0.2.0 — Illustrator-like 体验升级

### Stage 1: 基础设施增强（可并行）
1. **自定义预设管理系统**
   - 文件: `src/vector_studio/preset_manager.py`
   - 功能: 保存/加载/删除用户自定义预设到JSON文件
   - 集成到CLI和GUI

2. **任务历史记录系统**
   - 文件: `src/vector_studio/history.py`
   - 功能: 记录最近转换任务，支持查看、重新加载参数、导出报告

3. **外部编辑器集成**
   - 文件: `src/vector_studio/external_editors.py`
   - 功能: 检测并启动Illustrator/Inkscape/Figma等打开SVG

### Stage 2: GUI体验升级
4. **Streamlit GUI增强**
   - 对比预览模式（原图/SVG并排+叠加对比滑块）
   - 自定义预设选择器（内置+用户预设）
   - 历史记录面板
   - 一键打开外部编辑器按钮
   - SVG图层信息展示

### Stage 3: 质量与工程化
5. **SVG图层命名优化**
   - 在 `svg_tools.py` 中添加图层命名功能
   - 按颜色或层级命名SVG group元素

6. **测试增强**
   - 新增 `test_preset_manager.py`
   - 新增 `test_history.py`
   - 新增 `test_external_editors.py`
   - GUI组件测试

7. **文档完善**
   - 更新README：新增功能说明、截图占位、更详细的安装指南
   - 更新ROADMAP：标记v0.2完成项
   - 新增CHANGELOG.md
   - 新增CONTRIBUTING.md

### Stage 4: 打包与发布
8. **打包脚本完善**
   - 完善 `scripts/package.py`
   - 添加Windows/macOS/Linux启动脚本
   - 版本号统一更新

## 提交策略
每完成一个Stage就提交并推送到GitHub，commit message清晰描述变更内容。

## 当前时间锚点
- 开发周期: v0.2.0
- 目标: 功能完整、文档完善、测试覆盖、可安装使用
