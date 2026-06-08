# Bitmap Vector Studio 设计系统

> **Less is More** — v3.0 UI 重构设计令牌与组件规范

---

## 前言：Less is More 设计哲学

Bitmap Vector Studio v3.0 的 UI 重构基于「Less is More」设计哲学，核心目标是在不牺牲功能的前提下，将界面复杂度降至最低，让用户专注于创作本身。

### 智能默认优先

系统应在用户未做任何操作时，已做出最合理的决策。上传图片后自动分析并推荐最佳预设，高置信度时自动应用，无需用户手动选择。

### 渐进式披露

仅展示当前场景下最必要的控件。核心参数始终可见，高级功能默认折叠，专家功能隐藏在抽屉或命令面板中。界面复杂度随用户熟练度自然增长。

### 上下文感知

界面状态应反映当前任务上下文。无文件时显示引导态；处理中显示进度；完成后展示结果。控件可用性随状态自动调整，避免无效操作。

### 单焦点原则

同一时刻只引导用户关注一个核心任务。中央画布占据视觉中心，控制元素围绕核心任务排列，消除 competing visual hierarchies。

### 留白即信息

留白不是未使用的空间，而是有意的信息组织。区块间充足的呼吸空间帮助用户自然分组理解界面结构，减少认知负荷。

---

## 色彩系统

### 浅色模式（默认）

| 令牌 | 色值 | 用途 |
|---|---|---|
| `--bg-primary` | `#faf9f7` | 页面主背景，暖白色 |
| `--bg-secondary` | `#f0eeeb` | 次要背景，侧边栏/队列区 |
| `--bg-elevated` | `#ffffff` | 卡片、面板、浮层背景 |
| `--text-primary` | `#1a1a1a` | 主文字、标题 |
| `--text-secondary` | `#6b6b6b` | 次要文字、描述、占位符 |
| `--accent` | `#c45c26` | 主强调色，暖橙色，用于主按钮、聚焦环、活动状态 |
| `--accent-hover` | `#a84d1f` | 强调色悬停态 |
| `--success` | `#2d6a4f` | 成功状态、完成提示 |
| `--warning` | `#b35900` | 警告状态、需注意信息 |
| `--error` | `#c0392b` | 错误状态、失败提示 |
| `--border` | `#e5e3df` | 边框、分割线、分隔符 |

### 暗黑模式

| 令牌 | 色值 | 用途 |
|---|---|---|
| `--bg-primary` | `#1a1a1a` | 页面主背景 |
| `--bg-secondary` | `#242424` | 次要背景 |
| `--bg-elevated` | `#2d2d2d` | 卡片、面板背景 |
| `--text-primary` | `#f5f5f5` | 主文字 |
| `--text-secondary` | `#a0a0a0` | 次要文字 |
| `--accent` | `#e07a45` | 主强调色（提高亮度保证对比度） |
| `--accent-hover` | `#f0905a` | 强调色悬停态 |
| `--success` | `#4ade80` | 成功状态 |
| `--warning` | `#fbbf24` | 警告状态 |
| `--error` | `#f87171` | 错误状态 |
| `--border` | `#3d3d3d` | 边框、分割线 |

### 色彩使用原则

- **强调色克制使用**：暖橙色仅用于主按钮、当前活动项、聚焦环和关键操作，不超过界面 5% 面积
- **背景层级**：通过 `--bg-primary` → `--bg-secondary` → `--bg-elevated` 建立清晰的空间层级
- **文字对比**：主文字与背景对比度 ≥ 7:1，次要文字 ≥ 4.5:1
- **状态色独立**：成功/警告/错误不依赖强调色，确保色盲用户可通过图标区分

---

## 间距系统

### 基础间距令牌

| 令牌 | 值 | 用途 |
|---|---|---|
| `--space-xs` | `4px` | 图标内边距、紧凑行间距 |
| `--space-sm` | `8px` | 按钮内图标间距、小标签内边距 |
| `--space-md` | `16px` | 组件内部间距、表单字段间距 |
| `--space-lg` | `24px` | 卡片内边距、面板内边距 |
| `--space-xl` | `32px` | 区块间距、模块分隔 |
| `--space-2xl` | `48px` | 大区块间距、页面级分隔 |

### 间距原则

- **区块最小间距**：相邻功能区块之间至少 `32px`，确保视觉分组清晰
- **组件内部间距**：同一组件内元素间距统一为 `16px`，子元素间可降至 `8px`
- **对齐网格**：所有元素对齐 4px 基础网格，避免奇数间距
- **密度模式**：紧凑模式下间距缩减 25%，适用于小窗口或高密度列表

---

## 字体系统

### 字体栈

```css
--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
--font-mono: 'JetBrains Mono', 'Fira Code', 'SF Mono', monospace;
```

### 字号规范

| 层级 | 字号 | 字重 | 行高 | 字间距 | 用途 |
|---|---|---|---|---|---|
| 页面标题 | `24px` | `600` | `1.3` | `-0.02em` | 页面主标题 |
| 区块标题 | `18px` | `600` | `1.4` | `-0.01em` | 面板标题、卡片标题 |
| 正文 | `16px` | `400` | `1.6` | `0` | 描述文字、参数标签 |
| 辅助文字 | `14px` | `400` | `1.5` | `0` | 次要说明、提示信息 |
| 标签/徽章 | `12px` | `500` | `1.4` | `0.01em` | 小标签、状态徽章、按钮内文字 |

### 字体原则

- **中文优化**：中文字体优先使用系统字体（PingFang SC / Microsoft YaHei），避免加载外部中文字体文件
- **字重限制**：仅使用 400（Regular）和 600（SemiBold）两种字重，保持界面简洁
- **行高舒适**：中文正文行高 1.6，确保阅读舒适度
- **大写克制**：英文标签避免全大写，仅使用首字母大写或句首大写

---

## 圆角系统

| 令牌 | 值 | 用途 |
|---|---|---|
| `--radius-sm` | `4px` | 标签、小按钮、徽章、输入框内图标容器 |
| `--radius-md` | `8px` | 按钮、输入框、下拉选择器、小卡片 |
| `--radius-lg` | `12px` | 卡片、面板、抽屉、提示框 |
| `--radius-xl` | `16px` | 模态框、大卡片、悬浮面板 |
| `--radius-full` | `9999px` | 圆形按钮、头像、状态指示点 |

### 圆角原则

- **内外一致**：容器圆角与内部元素圆角保持比例关系，内部元素圆角不超过容器
- **方向性圆角**：底部滑出抽屉仅顶部使用 `radius-lg`，底部保持直角
- **按钮统一**：所有按钮统一使用 `radius-md`（`8px`），包括图标按钮和文字按钮

---

## 阴影系统（克制）

| 令牌 | 值 | 用途 |
|---|---|---|
| `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.04)` | 卡片默认态、内嵌元素 |
| `--shadow-md` | `0 4px 12px rgba(0,0,0,0.06)` | 卡片悬浮态、下拉菜单、抽屉 |
| `--shadow-lg` | `0 8px 24px rgba(0,0,0,0.08)` | 模态框、Toast、Command Palette |

### 阴影原则

- **无阴影优先**：静态卡片不使用阴影，通过边框和背景色区分层级
- **悬浮触发阴影**：仅交互元素在悬浮或激活时提升阴影层级
- **暗黑模式调整**：暗黑模式下阴影透明度降低 30%，避免过重的黑色投影
- **不使用阴影表达高度**：阴影仅用于区分层级，不用于按钮按压态（改用背景色变化）

---

## 组件规范

### Button

三种变体：

| 变体 | 背景 | 文字 | 边框 | 用途 |
|---|---|---|---|---|
| **Primary** | `--accent` | `#ffffff` | 无 | 主操作：转换、保存、应用 |
| **Secondary** | `--bg-elevated` | `--text-primary` | `--border` | 次要操作：取消、重置、更多选项 |
| **Ghost** | 透明 | `--text-secondary` | 无 | 工具操作：图标按钮、切换开关、导航 |

**尺寸规范**：
- 高度：`40px`（标准）、`32px`（紧凑）
- 圆角：`8px`
- 内边距：`16px` 水平（文字按钮）、`8px`（图标按钮）
- 图标与文字间距：`8px`

**状态**：
- 默认 → 悬浮：背景色变深（Primary: `--accent-hover`，Secondary: `--bg-secondary`）
- 聚焦：`2px` 实线 outline，`--accent` 色，偏移 `2px`
- 禁用：透明度 `0.4`，cursor: not-allowed
- 加载中：文字替换为旋转图标，禁用点击

### Input

**尺寸规范**：
- 高度：`40px`
- 圆角：`8px`
- 内边距：`12px` 水平
- 边框：`1px solid --border`

**状态**：
- 聚焦：`2px` 实线边框，`--accent` 色，内部无阴影
- 错误：边框 `--error`，下方显示 `12px` 错误文字
- 禁用：背景 `--bg-secondary`，文字 `--text-secondary`

### Select

- 与输入框同高（`40px`），统一视觉高度
- 自定义下拉面板：`radius-lg`，`shadow-md`，最大高度 `240px`
- 选中项左侧显示 `--accent` 色竖条指示器（`2px` 宽）
- 分组标题使用 `12px` 辅助文字，`--text-secondary` 色

### Card

- 圆角：`12px`
- 背景：`--bg-elevated`
- 默认无阴影，悬浮时应用 `--shadow-md`
- 内边距：`24px`
- 边框：`1px solid --border`（可选，用于弱层级卡片）

### Drawer（高级参数抽屉）

- 底部滑出，占据视口高度 `60%`（移动端 `80%`）
- 顶部圆角：`12px`
- 背景：`--bg-elevated`
- 阴影：`--shadow-lg`
- 头部固定，内容区可滚动
- 关闭方式：点击遮罩、向下滑动、Esc 键

### Toast

- 位置：顶部居中，距离顶部 `24px`
- 背景：`--bg-elevated`
- 圆角：`12px`
- 阴影：`--shadow-lg`
- 自动消失：`3s`（成功）/ `5s`（错误）
- 动画：从上方滑入（`translateY(-16px)` → `0`），消失时淡出

---

## 布局规范

### 桌面端布局

采用「单栏聚焦 + 底部控制带」架构：

```
┌─────────────────────────────────────────────┐
│  Logo    Command Palette    设置  主题        │  ← TopBar (56px)
├─────────────────────────────────────────────┤
│                                             │
│                                             │
│           中央预览画布                         │  ← MainCanvas
│                                             │
│      并排对比 / 叠加对比滑块                    │
│                                             │
│                                             │
├─────────────────────────────────────────────┤
│  预设  │  核心参数1  核心参数2  核心参数3  │  │  ← ControlBar (72px)
│  选择  │  核心参数4  │      [开始转换]      │
├─────────────────────────────────────────────┤
│  ▼ 文件队列 (可折叠)                          │  ← QueueBar (可折叠)
│  img1  img2  img3 ...                        │
└─────────────────────────────────────────────┘
```

### 响应式断点

| 断点 | 宽度 | 布局调整 |
|---|---|---|
| **桌面** | `≥1024px` | 完整布局，底部控制带展开 |
| **紧凑** | `768px - 1023px` | 控制带参数收拢为图标+下拉，队列栏默认折叠 |
| **移动端** | `<768px` | 控制带变为底部固定窄条，抽屉全屏，画布全高 |

### 最大内容宽度

- 画布区域：无限制，自适应窗口
- 控制带内容：最大 `1200px`，居中排列
- 抽屉内容：最大 `720px`，居中排列

---

## 交互规范

### 过渡动画

| 令牌 | 时长 | 缓动 | 用途 |
|---|---|---|---|
| `--transition-fast` | `0.15s` | `ease-out` | 按钮悬浮、颜色变化、图标切换 |
| `--transition-base` | `0.2s` | `ease-in-out` | 面板展开、抽屉滑出、下拉菜单 |
| `--transition-slow` | `0.3s` | `cubic-bezier(0.4, 0, 0.2, 1)` | 页面切换、模态框出现、大布局变化 |

### 悬浮反馈

- **按钮**：背景色变化，不使用阴影放大或位移
- **卡片**：应用 `--shadow-md`，边框色变为 `--accent` 的 20% 透明度
- **列表项**：背景变为 `--bg-secondary`
- **图标按钮**：背景填充 `--bg-secondary`，图标色变为 `--text-primary`

### 聚焦状态

- 所有可交互元素必须有可见聚焦态
- 聚焦环：`2px` outline，`--accent` 色，偏移 `2px`
- 输入框聚焦：边框变为 `--accent`，无 outline 环（避免双层视觉）
- 键盘导航时显示聚焦环，鼠标点击后隐藏（`:focus-visible`）

### 减少动画支持

```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

- 尊重系统减少动画设置
- 必要的状态变化保留即时切换（无动画）
- 加载动画替换为静态图标

---

## 图标规范

- 图标库：Lucide React
- 图标尺寸：`16px`（标准）、`20px`（导航/工具栏）、`24px`（空状态/大图标）
- 描边宽度：`1.5px`（标准）、`2px`（强调）
- 图标与文字组合时，图标垂直居中于文字行高
- 图标按钮最小点击区域：`40px × 40px`

---

## Z-Index 层级

| 层级 | 值 | 用途 |
|---|---|---|
| 基础内容 | `0` | 页面主体、画布 |
| 控制带 | `10` | 底部 ControlBar、顶部 TopBar |
| 悬浮面板 | `20` | 下拉菜单、工具提示 |
| 抽屉 | `30` | 底部 AdvancedDrawer |
| 遮罩层 | `40` | 模态框、抽屉的遮罩背景 |
| 模态框 | `50` | 对话框、确认框 |
| Toast | `60` | 全局通知 |
| Command Palette | `70` | 命令面板（最高优先级） |

---

## 设计令牌使用示例

### CSS 变量定义

```css
:root {
  /* 背景 */
  --bg-primary: #faf9f7;
  --bg-secondary: #f0eeeb;
  --bg-elevated: #ffffff;

  /* 文字 */
  --text-primary: #1a1a1a;
  --text-secondary: #6b6b6b;

  /* 强调 */
  --accent: #c45c26;
  --accent-hover: #a84d1f;

  /* 状态 */
  --success: #2d6a4f;
  --warning: #b35900;
  --error: #c0392b;

  /* 边框 */
  --border: #e5e3df;

  /* 间距 */
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;
  --space-2xl: 48px;

  /* 圆角 */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  --radius-full: 9999px;

  /* 阴影 */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.04);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.06);
  --shadow-lg: 0 8px 24px rgba(0,0,0,0.08);

  /* 过渡 */
  --transition-fast: 0.15s ease-out;
  --transition-base: 0.2s ease-in-out;
  --transition-slow: 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg-primary: #1a1a1a;
    --bg-secondary: #242424;
    --bg-elevated: #2d2d2d;
    --text-primary: #f5f5f5;
    --text-secondary: #a0a0a0;
    --accent: #e07a45;
    --accent-hover: #f0905a;
    --success: #4ade80;
    --warning: #fbbf24;
    --error: #f87171;
    --border: #3d3d3d;
  }
}
```

### React / Tailwind 使用

```tsx
// 按钮示例
<button className="
  h-10 px-4 rounded-md
  bg-[#c45c26] text-white
  hover:bg-[#a84d1f]
  focus:outline-none focus:ring-2 focus:ring-[#c45c26] focus:ring-offset-2
  transition-colors duration-150
">
  开始转换
</button>

// 卡片示例
<div className="
  rounded-xl bg-white
  border border-[#e5e3df]
  hover:shadow-md
  transition-shadow duration-200
  p-6
">
  卡片内容
</div>
```

---

## 版本记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v3.0.0 | 2026-06 | 初始设计系统，Less is More 重构 |
