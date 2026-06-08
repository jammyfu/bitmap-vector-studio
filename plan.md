# Bitmap Vector Studio — "Less is More" UI重构规划

## 设计哲学

> **"Less is More"** — 每个像素都应有其存在的理由。

### 核心原则
1. **智能默认优先**：系统自动选择最佳设置，用户只需确认或微调
2. **渐进式披露**：高级功能默认隐藏，需要时再展开
3. **上下文感知**：界面根据输入内容自动调整显示的功能
4. **单焦点原则**：同一时间只呈现一个主要操作路径
5. **留白即信息**：充足的间距让重要内容自然突出

### 视觉原则
- 低饱和度暖色调，拒绝蓝紫渐变
- 充足的留白（最小间距16px，区块间距32px）
- 清晰的字体层次（3级：标题/正文/辅助）
- 圆角统一（8px标准，4px紧凑，16px卡片）
- 阴影克制（仅用于层级区分，不使用装饰性阴影）

---

## 当前问题诊断

| 问题 | 严重程度 | 影响 |
|------|---------|------|
| App.tsx God Component (737行, 40+ state) | 🔴 高 | 维护困难，功能耦合 |
| ParamPanel 参数过载 (529行) | 🔴 高 | 用户面对数十个参数，决策疲劳 |
| 功能平铺堆砌 (AI/动画/协作/工作流/云分享) | 🔴 高 | 界面噪音大，核心功能被淹没 |
| Props Drilling 严重 | 🟡 中 | 代码可读性差 |
| 两套CSS主题并存 | 🟡 中 | 维护负担 |
| Streamlit 2809行单文件 | 🟡 中 | 难以维护 |
| 三栏布局小屏体验差 | 🟡 中 | 移动端/小窗口体验不佳 |

---

## 重构阶段

### Stage 1: 桌面应用核心重构（2-3周）

#### 1.1 状态管理重构
- 引入 **Zustand** 替代 props drilling
- 按域拆分 Store：
  - `useAppStore` — 全局状态（主题、环境检测）
  - `useQueueStore` — 文件队列管理
  - `useConvertStore` — 转换流程状态
  - `useSettingsStore` — 用户设置
  - `useAdvancedStore` — 高级功能状态（AI/动画/协作等）

#### 1.2 新布局架构
```
┌─────────────────────────────────────────────┐
│  [Logo]  [Command Palette 🔍]  [⚙️] [👤]   │  ← 极简顶部栏
├─────────────────────────────────────────────┤
│                                             │
│           🖼️  中央预览画布                    │  ← 核心视觉区
│           (并排/叠加对比)                    │
│                                             │
├─────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────┐   │
│  │ 预设    │  │ 核心参数 │  │ 操作    │   │  ← 底部控制带
│  │ [海报▼] │  │ [简化]  │  │ [转换]  │   │
│  └─────────┘  └─────────┘  └─────────┘   │
│         ▼ 高级参数（默认折叠）               │
├─────────────────────────────────────────────┤
│  📁 文件队列（可折叠）  │  📊 状态           │  ← 底部信息区
└─────────────────────────────────────────────┘
```

**关键变化**：
- 三栏 → 单栏聚焦 + 底部控制带
- 参数面板从右侧移至底部，减少视觉跳跃
- 文件队列可折叠为底部标签栏
- 顶部栏仅保留Logo、Command Palette、设置、用户

#### 1.3 智能默认系统
- **自动预设推荐**：上传图片后自动分析并推荐最佳预设（高置信度时自动应用）
- **一键转换**：默认参数下，用户只需"上传 → 确认 → 下载"三步
- **参数智能折叠**：仅显示3个核心参数（颜色模式、曲线模式、优化级别），其余折叠

#### 1.4 Command Palette
- `Cmd/Ctrl + K` 唤起
- 统一入口：搜索预设、命令、文件、设置
- 替代分散的 Market/Plugins/History/Settings 按钮

#### 1.5 组件拆分
- `App.tsx` → 拆分为 `stores/` + `pages/MainPage.tsx`
- `ParamPanel.tsx` → `CoreParams.tsx` + `AdvancedDrawer.tsx`
- `Sidebar.tsx` → `QueueBar.tsx`（可折叠底部栏）
- 删除 `Header.tsx`（功能并入顶部栏）

### Stage 2: Streamlit GUI 轻量化（1周）

#### 2.1 多页结构
使用 `st.navigation` 拆分为：
- **转换**（主页面，三步流程）
- **批量**（独立页面）
- **历史**（独立页面）
- **设置**（独立页面）

#### 2.2 核心页面简化
```
[上传图片区域]  ← 大文件拖拽区

[🤖 智能推荐: 海报预设]  ← 一行显示推荐

[颜色模式 ▼]  [曲线模式 ▼]  [优化 ▼]  ← 三个核心参数

[▶ 开始转换]  [⬇ 下载SVG]

▼ 高级参数（默认折叠）
```

#### 2.3 删除冗余
- 移除与桌面端重复的高级功能面板
- 保留核心转换 + 批量 + 历史

### Stage 3: CLI 体验优化（3-4天）

#### 3.1 命令精简
- 将25+命令组收敛为6个核心组：
  - `convert` — 转换（合并 trace + batch + generate）
  - `config` — 配置
  - `plugin` — 插件
  - `market` — 市场
  - `account` — 账号
  - `help` — 帮助

#### 3.2 智能输出
- 默认输出简洁（仅进度条 + 结果路径）
- `--verbose` 显示详细信息
- 添加 `--quiet` 静默模式
- 错误信息一行化，去除冗余表格

#### 3.3 交互优化
- `vector-studio convert input.png` — 无参数时自动推荐预设
- 添加 `vector-studio quick input.png` — 一键转换（智能默认）

### Stage 4: 统一设计系统（1周）

#### 4.1 设计令牌
```css
/* 色彩 */
--color-bg-primary: #faf9f7;      /* 暖白背景 */
--color-bg-secondary: #f0eeeb;    /* 次要背景 */
--color-bg-elevated: #ffffff;     /* 卡片背景 */
--color-text-primary: #1a1a1a;   /* 主文字 */
--color-text-secondary: #6b6b6b;  /* 次要文字 */
--color-accent: #c45c26;          /* 暖橙强调色 */
--color-accent-hover: #a84d1f;    /* 悬停 */
--color-success: #2d6a4f;         /* 成功 */
--color-warning: #b35900;         /* 警告 */
--color-error: #c0392b;           /* 错误 */
--color-border: #e5e3df;          /* 边框 */

/* 间距 */
--space-xs: 4px;
--space-sm: 8px;
--space-md: 16px;
--space-lg: 24px;
--space-xl: 32px;
--space-2xl: 48px;

/* 字体 */
--font-sans: "Inter", -apple-system, sans-serif;
--font-mono: "JetBrains Mono", monospace;
--text-xs: 12px;
--text-sm: 14px;
--text-base: 16px;
--text-lg: 20px;
--text-xl: 24px;

/* 圆角 */
--radius-sm: 4px;
--radius-md: 8px;
--radius-lg: 12px;
--radius-xl: 16px;
```

#### 4.2 组件规范
- `Button` — 三种变体：Primary / Secondary / Ghost
- `Input` — 统一高度40px，聚焦环2px
- `Select` — 自定义下拉，与输入框同高
- `Card` — 圆角12px，阴影仅用于悬浮
- `Drawer` — 底部滑出，用于高级参数
- `Toast` — 顶部居中，自动消失

#### 4.3 CSS架构
- 删除 `App.css`（确认废弃）
- `global.css` → 仅保留CSS变量和基础重置
- 组件样式 → CSS Modules 或 Tailwind
- 新增 `design-tokens.css`

---

## 文件变更计划

### 新增文件
```
desktop/src/stores/
  appStore.ts
  queueStore.ts
  convertStore.ts
  settingsStore.ts
  advancedStore.ts

desktop/src/components/
  CommandPalette.tsx      # 统一搜索入口
  CoreParams.tsx          # 3个核心参数
  AdvancedDrawer.tsx      # 高级参数抽屉
  QueueBar.tsx            # 可折叠底部队列
  TopBar.tsx              # 极简顶部栏
  MainCanvas.tsx          # 中央预览画布
  SmartRecommend.tsx      # 智能推荐提示

desktop/src/styles/
  design-tokens.css       # 设计令牌
  tailwind.config.js      # Tailwind配置

desktop/src/pages/
  MainPage.tsx            # 主页面

app_pages/
  01_Convert.py           # Streamlit多页
  02_Batch.py
  03_History.py
  04_Settings.py

docs/
  DESIGN_SYSTEM.md        # 设计系统文档
```

### 修改文件
```
desktop/src/App.tsx       # 大幅简化，仅路由+Provider
desktop/src/main.tsx      # 添加Zustand Provider
desktop/src/styles/global.css  # 精简为令牌+重置
desktop/src/components/Layout.tsx  # 适配新布局
desktop/src/components/ParamPanel.tsx  # 拆分为Core+Advanced
desktop/src/components/Sidebar.tsx  # 改为QueueBar
desktop/src/components/PreviewPane.tsx  # 改为MainCanvas

app.py                    # 重构为多页入口
src/vector_studio/cli.py  # 精简命令结构

README.md                 # 更新界面截图和说明
```

### 删除/归档文件
```
desktop/src/components/Header.tsx       # 功能并入TopBar
desktop/src/styles/App.css              # 确认废弃后删除
desktop/src/components/StatusBar.tsx    # 功能并入QueueBar
```

---

## 验证清单

- [ ] 桌面应用启动正常
- [ ] 核心三步流程（上传→确认→下载）< 5秒
- [ ] 参数面板默认只显示3个参数
- [ ] Command Palette 可搜索所有功能
- [ ] 文件队列可折叠/展开
- [ ] 响应式：窗口<1024px时自动切换为紧凑模式
- [ ] Streamlit 多页导航正常
- [ ] CLI `vector-studio quick` 一键转换成功
- [ ] 所有现有测试通过
- [ ] 设计文档已更新

---

## 时间线

| 阶段 | 预计时间 | 关键交付 |
|------|---------|---------|
| Stage 1: 桌面核心重构 | 2-3周 | 新布局+Zustand+智能默认 |
| Stage 2: Streamlit轻量化 | 1周 | 多页结构+简化流程 |
| Stage 3: CLI优化 | 3-4天 | 精简命令+智能输出 |
| Stage 4: 设计系统 | 1周 | 统一令牌+组件规范+文档 |
| **总计** | **4-5周** | **完整UI重构** |

---

*规划完成。按Stage顺序推进，每完成一个Stage提交到GitHub。*
