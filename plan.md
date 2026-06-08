# Bitmap Vector Studio 推进计划 v0.5

## 项目现状
- v0.4.0 已完成并推送到 GitHub: https://github.com/jammyfu/bitmap-vector-studio
- 331 个测试全部通过
- 具备：插件系统、Web API、Docker、配置管理、智能预处理、SVG优化

## 目标版本: v0.5.0 — AI 辅助与实时交互

### Stage 1: 实时交互（可并行）
1. **实时预览系统**
   - 文件: `src/vector_studio/live_preview.py`
   - 功能: 调整参数时实时生成低分辨率预览SVG，无需点击转换
   - 技术: 使用缩略图快速转换 + 缓存机制
   - GUI集成: Streamlit参数变化时自动触发预览更新

2. **局部重描摹**
   - 文件: `src/vector_studio/region_trace.py`
   - 功能: 用户圈选区域，仅重新生成某一块SVG
   - 技术: 裁剪区域 -> 单独转换 -> 合并回原始SVG
   - GUI集成: 支持矩形/圆形/多边形选区

### Stage 2: AI辅助处理
3. **AI语义简化**
   - 文件: `src/vector_studio/ai_simplify.py`
   - 功能: 对复杂照片先做语义简化（边缘保留平滑、颜色量化、噪声去除）
   - 技术: 纯Pillow/NumPy实现（无需深度学习框架），可选ONNX模型
   - 策略: 双边滤波效果模拟、超像素分割、颜色聚类

4. **OCR文字识别与保留**
   - 文件: `src/vector_studio/ai_ocr.py`
   - 功能: 检测图片中的文字区域，保留文字结构
   - 技术: 可选依赖pytesseract/easyocr，未安装时跳过
   - 输出: 文字区域坐标 + 识别文本，用于后续SVG中文字层处理

### Stage 3: 生态扩展
5. **预设市场**
   - 文件: `src/vector_studio/market.py`
   - 功能: 在线预设分享与下载平台（GitHub Gist/Repo作为后端）
   - 功能: 浏览热门预设、下载、评分、上传自己的预设
   - CLI: `vector-studio market list/search/install/publish`

### Stage 4: GUI与CLI集成
6. **Streamlit GUI v0.5升级**
   - 实时预览面板（参数变化自动更新）
   - 局部重描摹工具（选区+转换）
   - AI增强开关（语义简化、OCR）
   - 预设市场浏览器

7. **CLI增强**
   - `vector-studio trace --live-preview` 实时预览模式
   - `vector-studio trace --region x,y,w,h` 局部转换
   - `vector-studio trace --ai-simplify` AI语义简化
   - `vector-studio trace --ocr` OCR文字保留

### Stage 5: 测试与文档
8. **测试增强**
   - 新增模块测试覆盖
9. **文档更新**
   - README更新v0.5功能
   - CHANGELOG更新
   - ROADMAP标记完成

## 提交策略
每完成一个Stage就提交并推送到GitHub。

## 当前时间锚点
- 开发周期: v0.5.0
- 目标: AI辅助、实时交互、生态扩展
