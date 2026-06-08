# Bitmap Vector Studio 推进计划 v2.0

## 项目现状
- v1.2.0 已完成并推送到 GitHub: https://github.com/jammyfu/bitmap-vector-studio
- 18 个 Git 提交
- 40 个 Python 源文件 + 42 个测试文件 + 11 篇文档
- Tauri 桌面应用完整可用
- 版本 1.2.0

## 目标版本: v2.0.0 — AI 原生与实时协作

### Stage 1: AI 原生（可并行）
1. **本地 AI 模型推理**
   - 文件: `src/vector_studio/ai_onnx.py`
   - 功能: ONNX Runtime 实时图像分割、风格迁移、超分辨率
   - 支持模型: UNet分割、StyleTransfer、ESRGAN超分
   - 模型自动下载和管理
   - 纯CPU运行，可选GPU加速

2. **多引擎智能编排**
   - 文件: `src/vector_studio/engine_orchestrator.py`
   - 功能: 根据素材类型自动选择最优引擎组合
   - AI辅助决策：用轻量级模型分析图片，推荐最佳引擎+参数
   - 引擎流水线：预处理引擎A -> 转换引擎B -> 后处理引擎C

### Stage 2: 实时协作（可并行）
3. **实时协作编辑**
   - 文件: `src/vector_studio/collaboration.py`
   - 功能: WebSocket 多人同步编辑同一项目
   - 操作同步：参数调整、预览更新、文件上传
   - 冲突解决：乐观锁 + 操作日志回放
   - 权限管理：房主/编辑者/观察者

4. **跨设备同步**
   - 文件: `src/vector_studio/sync_service.py`
   - 功能: 桌面端 ↔ 网页端 ↔ API 服务端状态同步
   - 实时同步：工作区、预设、配置、历史
   - 离线支持：本地缓存 + 上线后同步

### Stage 3: 动画与工作流（可并行）
5. **矢量动画导出**
   - 文件: `src/vector_studio/animation.py`
   - 功能: SVG 动画生成、Lottie 格式导出
   - 动画类型：路径绘制动画、颜色渐变动画、变形动画
   - 导出格式：SVG SMIL、Lottie JSON、CSS动画

6. **智能批处理工作流**
   - 文件: `src/vector_studio/workflow.py`
   - 功能: 可视化节点编辑器
   - 节点类型：输入、转换、优化、导出、AI处理
   - 工作流保存/加载/分享
   - 条件分支和循环支持

### Stage 4: 云端生态
7. **云端预设与插件市场**
   - 文件: `src/vector_studio/cloud_market.py`
   - 功能: 用户账号体系、付费插件支持
   - 积分/订阅系统
   - 开发者收益分成

### Stage 5: GUI 与 CLI 集成
8. **Streamlit GUI v2.0 升级**
   - AI模型选择面板
   - 协作房间管理
   - 动画预览和导出
   - 工作流编辑器

9. **CLI 增强**
   - `vector-studio ai` 命令组
   - `vector-studio collab` 命令组
   - `vector-studio animate` 命令组
   - `vector-studio workflow` 命令组

### Stage 6: 测试与文档
10. **测试增强**
    - 新增模块测试覆盖
11. **文档更新**
    - README 更新 v2.0 功能
    - CHANGELOG 更新
    - ROADMAP 标记完成

## 提交策略
每完成一个 Stage 就提交并推送到 GitHub。

## 当前时间锚点
- 开发周期: v2.0.0
- 目标: AI原生、实时协作、动画、工作流
