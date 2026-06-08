# 贡献指南

首先，感谢你考虑为 Bitmap Vector Studio 做出贡献！❤️

无论是修复 bug、添加功能、改进文档，还是分享使用经验，你的每一份贡献都让这个项目变得更好。

---

## 📋 目录

- [开发环境搭建](#开发环境搭建)
- [代码风格](#代码风格)
- [提交规范](#提交规范)
- [测试要求](#测试要求)
- [PR 流程](#pr-流程)
- [行为准则](#行为准则)

---

## 开发环境搭建

### 1. 克隆仓库

```bash
git clone https://github.com/jammyfu/bitmap-vector-studio.git
cd bitmap-vector-studio
```

### 2. 创建虚拟环境

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

### 3. 安装开发依赖

```bash
pip install -U pip
pip install -e ".[dev]"
```

这会同时安装运行时依赖（VTracer、Pillow、Streamlit 等）和开发依赖（pytest、ruff）。

### 4. 验证环境

```bash
# 运行测试
pytest

# 检查代码风格
ruff check src tests
ruff format --check src tests

# 启动 GUI（可选）
streamlit run app.py
```

---

## 代码风格

本项目使用 **Ruff** 进行代码格式化和风格检查，配置见 `pyproject.toml`。

### 关键规则

| 项目 | 配置 |
|---|---|
| 行长度 | **100 字符** |
| 目标目录 | `src/`、`tests/` |
| 引号 | 优先使用双引号 |
| 导入排序 | 自动排序（I 规则集） |

### 常用命令

```bash
# 检查风格问题
ruff check src tests

# 自动修复可修复的问题
ruff check --fix src tests

# 格式化代码
ruff format src tests
```

### 编码约定

- **类型注解**：所有公共函数和类必须使用类型注解
- **文档字符串**：模块、类、公共函数必须包含 docstring（Google 风格或简洁描述）
- **异常处理**：CLI 层捕获异常并打印友好错误信息，不暴露内部堆栈
- **路径处理**：统一使用 `pathlib.Path`，避免字符串拼接路径
- **跨平台**：Windows/macOS/Linux 路径和进程调用需考虑平台差异

---

## 提交规范

我们推荐使用 [Conventional Commits](https://www.conventionalcommits.org/zh-hans/v1.0.0/) 规范编写提交信息，这有助于自动生成 CHANGELOG 和版本号。

### 格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 类型说明

| 类型 | 含义 |
|---|---|
| `feat` | 新功能 |
| `fix` | 修复 bug |
| `docs` | 文档更新 |
| `style` | 代码风格调整（不影响功能） |
| `refactor` | 重构（既不修复 bug 也不添加功能） |
| `perf` | 性能优化 |
| `test` | 测试相关 |
| `chore` | 构建/工具/依赖更新 |

### 示例

```
feat(presets): 添加扫描件专用 scan 预设

- 提高滤斑点阈值至 8
- 默认启用降噪
- 限制最大输入边长为 3000px

fix(gui): 修复叠加对比滑块在 Firefox 下的拖拽问题

docs(readme): 更新 CLI 参数表格和安装说明
```

---

## 测试要求

### 测试框架

- 使用 **pytest**
- 测试文件放在 `tests/` 目录，命名格式 `test_*.py`
- 配置见 `pyproject.toml` 的 `[tool.pytest.ini_options]`

### 编写测试

```python
# tests/test_example.py
from vector_studio.models import TraceOptions

def test_trace_options_default_values():
    opts = TraceOptions()
    assert opts.colormode == "color"
    assert opts.color_precision == 6

def test_trace_options_validation():
    with pytest.raises(ValueError, match="color_precision"):
        TraceOptions(color_precision=10).validate()
```

### 测试覆盖要求

- 新增功能必须包含对应的单元测试
- 修复 bug 时优先添加能复现该 bug 的回归测试
- 模型校验逻辑必须全覆盖
- CLI 命令可使用 `typer.testing.CliRunner` 测试

### 运行测试

```bash
# 运行全部测试
pytest

# 运行特定测试文件
pytest tests/test_presets.py

# 显示详细输出
pytest -v

# 生成覆盖率报告（需安装 pytest-cov）
pytest --cov=vector_studio --cov-report=html
```

---

## PR 流程

### 1. 创建分支

```bash
git checkout -b feat/your-feature-name
# 或
git checkout -b fix/issue-description
```

### 2. 开发与提交

- 编写代码和测试
- 确保所有测试通过：`pytest`
- 确保代码风格合规：`ruff check src tests`
- 使用 Conventional Commits 规范提交

### 3. 更新文档

如果你的改动影响用户可见的行为，请同步更新：

- `README.md`（功能说明、CLI 参考）
- `CHANGELOG.md`（在 `[Unreleased]` 下添加）
- `docs/` 下的相关文档

### 4. 提交 PR

- PR 标题使用 Conventional Commits 格式
- 在描述中说明改动内容、动机、测试方式
- 关联相关 Issue（如有）：`Fixes #123`
- 确保 CI 检查全部通过

### 5. 代码审查

- 维护者会在 3 个工作日内进行审查
- 根据反馈进行修改并推送更新
- 审查通过后由维护者合并

---

## 行为准则

### 我们的承诺

为了营造一个开放和友好的环境，我们作为贡献者和维护者承诺：无论年龄、体型、身体健全与否、民族、性征、性别认同与表达、经验水平、国籍、个人外貌、种族、宗教或性取向如何，参与我们项目的每个人都享有不受骚扰的体验。

### 我们的标准

有助于创造积极环境的行为包括：

- 使用友好和包容的语言
- 尊重不同的观点和经验
- 优雅地接受建设性批评
- 关注对社区最有利的事情
- 对其他社区成员表示同理心

不可接受的行为包括：

- 使用带有性暗示的语言或图像，以及不受欢迎的性关注或性挑逗
- 发表挑衅、侮辱/贬损的评论，进行人身或政治攻击
- 公开或私下骚扰他人
- 未经明确许可发布他人的私人信息
- 其他在专业环境中被合理认为不恰当的行为

### 执行

项目维护者有权利和责任删除、编辑或拒绝不符合本行为准则的评论、提交、代码、wiki 编辑、问题和其他贡献。维护者有权利暂时或永久禁止任何他们认为有不恰当、威胁、冒犯或有害行为的贡献者。

---

## 💬 提问与讨论

- **Bug 报告**：使用 GitHub Issues，提供复现步骤、系统环境、错误日志
- **功能建议**：使用 GitHub Issues，描述使用场景和期望行为
- **一般讨论**：使用 GitHub Discussions

再次感谢你的贡献！🎉
