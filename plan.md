# Bitmap Vector Studio 推进计划 v0.3

## 项目现状
- v0.2.0 已完成并推送到 GitHub: https://github.com/jammyfu/bitmap-vector-studio
- 170 个测试全部通过
- 具备：GUI增强、预设管理、历史记录、外部编辑器、SVG图层命名

## 目标版本: v0.3.0 — 质量优化与智能处理

### Stage 1: 智能预处理（可并行）
1. **智能背景透明处理**
   - 文件: `src/vector_studio/smart_background.py`
   - 功能: 自动检测Logo/图标的主背景色并移除，生成透明PNG
   - 算法: 四角采样+边缘颜色聚类，判断背景色， flood fill移除

2. **OpenCV增强预处理**
   - 文件: `src/vector_studio/enhance.py`
   - 功能: 边缘增强、扫描件去噪、对比度自适应、锐化
   - 集成到 `preprocess.py` 作为可选增强步骤

3. **智能预设推荐**
   - 文件: `src/vector_studio/smart_recommend.py`
   - 功能: 分析图片特征（颜色数、边缘密度、透明度、分辨率）推荐最佳预设
   - 输出: 推荐预设名 + 置信度 + 理由

### Stage 2: SVG后处理优化
4. **SVG路径合并与颜色合并**
   - 文件: `src/vector_studio/svg_optimizer.py`
   - 功能: 合并相同颜色的相邻路径、简化路径数据、颜色量化
   - 文件评分: 基于路径数、文件大小、颜色数给出质量评分

5. **批量参数搜索**
   - 文件: `src/vector_studio/param_search.py`
   - 功能: 对单张图片用多组参数批量试跑，按评分自动挑选最优结果
   - 评分维度: 文件大小、路径数、视觉保真度（SSIM近似）

### Stage 3: 批量任务队列
6. **任务队列与进度系统**
   - 文件: `src/vector_studio/task_queue.py`
   - 功能: 异步批量转换队列、进度跟踪、失败重试、并发控制
   - 集成到CLI和GUI

### Stage 4: GUI集成
7. **Streamlit GUI v0.3升级**
   - 智能推荐按钮（分析图片后自动推荐预设）
   - 背景透明自动检测开关
   - 批量队列进度条
   - 参数搜索面板（一键多参数试跑）
   - SVG优化后处理选项

### Stage 5: 测试与文档
8. **测试增强**
   - 新增模块的测试覆盖
9. **文档更新**
   - README更新v0.3功能
   - CHANGELOG更新
   - ROADMAP标记完成

## 提交策略
每完成一个Stage就提交并推送到GitHub。

## 当前时间锚点
- 开发周期: v0.3.0
- 目标: 智能处理、质量优化、批量效率提升
