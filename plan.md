# Bitmap Vector Studio 推进计划 v1.2

## 项目现状
- v1.1.0 已完成并推送到 GitHub: https://github.com/jammyfu/bitmap-vector-studio
- 16 个 Git 提交
- 36 个 Python 源文件 + 33 个测试文件 + 9 篇文档
- Tauri 桌面应用完整可用
- 版本 1.1.0

## 目标版本: v1.2.0 — 稳定性与生态扩展

### Stage 1: 多引擎支持与生态（可并行）
1. **多矢量化引擎支持**
   - 文件: `src/vector_studio/engines.py`
   - 功能: 支持 potrace、autotrace 等作为备选后端
   - 自动选择最佳引擎（根据图片类型）
   - 引擎对比和评分

2. **插件 SDK 完善**
   - 文件: `src/vector_studio/plugin_sdk.py`
   - 功能: 类型提示、调试工具、示例模板生成
   - 插件验证器（检查插件是否符合规范）
   - 插件开发脚手架（一键生成新插件模板）

3. **云端同步预览**
   - 文件: `src/vector_studio/cloud_sync.py`
   - 功能: 转换结果上传到临时云存储
   - 生成分享链接（QR码）
   - 跨设备查看转换结果

4. **社区贡献者工具链**
   - 文件: `src/vector_studio/community_tools.py`
   - 功能: 预设验证器、插件审核工具、文档生成器
   - 贡献指南生成

### Stage 2: 测试覆盖率提升
5. **测试覆盖率提升到 90%+**
   - 补充缺失的测试用例
   - 集成测试增强
   - 性能基准测试
   - 端到端测试

### Stage 3: GUI 与 CLI 集成
6. **Streamlit GUI v1.2 升级**
   - 引擎选择器（VTracer / Potrace / AutoTrace）
   - 插件开发工具
   - 云端分享功能

7. **CLI 增强**
   - `vector-studio engine list` — 列出可用引擎
   - `vector-studio engine benchmark` — 引擎对比测试
   - `vector-studio plugin scaffold <name>` — 生成插件模板
   - `vector-studio cloud share <svg>` — 上传到云端
   - `vector-studio validate preset <file>` — 验证预设

### Stage 4: 测试与文档
8. **文档更新**
   - README 更新 v1.2 功能
   - CHANGELOG 更新
   - ROADMAP 标记完成

## 提交策略
每完成一个 Stage 就提交并推送到 GitHub。

## 当前时间锚点
- 开发周期: v1.2.0
- 目标: 更稳定、更开放、更易扩展
