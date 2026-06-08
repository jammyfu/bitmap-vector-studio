# 安装指南

本文档提供 Bitmap Vector Studio 的详细安装说明，涵盖不同操作系统和安装场景。

---

## 📋 目录

- [系统要求](#系统要求)
- [Python 环境](#python-环境)
- [依赖安装](#依赖安装)
- [VTracer 安装](#vtracer-安装)
- [可选依赖](#可选依赖)
- [常见问题排查](#常见问题排查)

---

## 系统要求

### 最低配置

| 项目 | 要求 |
|---|---|
| Python | 3.9+ |
| 操作系统 | Windows 10 / macOS 11 / Linux (glibc 2.31+) |
| 内存 | 4 GB RAM |
| 磁盘空间 | 100 MB（安装）+ 转换缓存空间 |
| 网络 | 安装时需要（从 PyPI 下载依赖） |

### 推荐配置

| 项目 | 建议 |
|---|---|
| Python | 3.11 或 3.12 |
| 内存 | 8 GB+（处理高分辨率图片） |
| 处理器 | 多核 CPU（矢量化计算密集型） |

---

## Python 环境

### 检查 Python 版本

```bash
python --version
# 或
python3 --version
```

如果版本低于 3.9，请先升级 Python：

- **Windows**：从 [python.org](https://www.python.org/downloads/) 下载安装程序
- **macOS**：`brew install python@3.12`
- **Linux**：`sudo apt install python3.12 python3.12-venv`

### 创建虚拟环境（强烈推荐）

虚拟环境可以避免依赖冲突，是 Python 开发的最佳实践。

```bash
# 进入项目目录
cd bitmap-vector-studio

# 创建虚拟环境
python -m venv .venv
```

### 激活虚拟环境

**Windows (PowerShell)**

```powershell
.venv\Scripts\Activate.ps1
```

> 若遇到执行策略错误：
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

**Windows (CMD)**

```cmd
.venv\Scripts\activate.bat
```

**macOS / Linux (Bash/Zsh)**

```bash
source .venv/bin/activate
```

**macOS / Linux (Fish)**

```fish
source .venv/bin/activate.fish
```

激活成功后，命令行提示符前会显示 `(.venv)`。

---

## 依赖安装

### 方式一：通过 pyproject.toml 安装（推荐）

```bash
pip install -U pip
pip install -e .
```

这会安装所有运行时依赖，并将 `vector-studio` 命令注册到 PATH。

### 方式二：通过 requirements.txt 安装

```bash
pip install -U pip
pip install -r requirements.txt
```

> 注意：此方式不会将项目本身安装为可编辑包，CLI 命令 `vector-studio` 可能不可用。建议配合 `pip install -e .` 使用。

### 方式三：开发模式安装

如果你计划修改代码或运行测试：

```bash
pip install -e ".[dev]"
```

这会额外安装 `pytest` 和 `ruff`。

### 验证安装

```bash
# 检查 CLI 是否可用
vector-studio --help

# 检查 Python 包是否可导入
python -c "from vector_studio.tracer import trace_image; print('OK')"

# 运行测试
pytest
```

---

## VTracer 安装

VTracer 是核心矢量化引擎，本项目通过 `vtracer` Python 包调用。

### Python 包方式（默认）

`pip install -e .` 会自动安装 `vtracer>=0.6.15`，无需额外操作。

验证：

```bash
python -c "import vtracer; print(vtracer.__version__)"
```

### VTracer CLI（可选）

VTracer 也提供独立的命令行工具，可作为后备方案：

```bash
# 通过 cargo 安装（需要 Rust 工具链）
cargo install vtracer

# 验证
vtracer --help
```

> 一般情况下不需要单独安装 VTracer CLI，Python 绑定已足够。

---

## 可选依赖

### CairoSVG（已包含在默认依赖中）

用于 PDF 和 PNG 导出。安装项目时已自动包含 `cairosvg>=2.7`。

如果系统缺少底层库，可能需要额外安装：

**Ubuntu/Debian**

```bash
sudo apt install libcairo2-dev libffi-dev
```

**macOS**

```bash
brew install cairo libffi
```

**Windows**

Windows 上 CairoSVG 通常通过预编译 wheel 安装，无需额外系统依赖。

### Inkscape（系统级安装）

用于 EPS 导出和 SVG 后处理。

**Windows**

1. 从 [inkscape.org](https://inkscape.org/release/) 下载安装程序
2. 安装时勾选「添加到系统 PATH」
3. 验证：`inkscape --version`

**macOS**

```bash
brew install --cask inkscape
```

**Linux**

```bash
# Ubuntu/Debian
sudo apt install inkscape

# Fedora
sudo dnf install inkscape

# Arch
sudo pacman -S inkscape
```

### 外部编辑器（可选）

Bitmap Vector Studio 支持一键打开以下编辑器，安装后会自动检测：

- **Adobe Illustrator**：从 Adobe Creative Cloud 安装
- **Affinity Designer**：从 [affinity.serif.com](https://affinity.serif.com/) 购买安装
- **Figma**：桌面版从 [figma.com](https://www.figma.com/downloads/) 下载
- **CorelDRAW**：从 [coreldraw.com](https://www.coreldraw.com/) 购买安装
- **Vectr**：从 [vectr.com](https://vectr.com/) 下载
- **Boxy SVG**：从 [boxy-svg.com](https://boxy-svg.com/) 购买安装

---

## 常见问题排查

### `pip install` 失败 / 构建错误

**现象**：安装 `vtracer` 或 `cairosvg` 时出现编译错误。

**解决**：

```bash
# 升级 pip、setuptools、wheel
pip install -U pip setuptools wheel

# 重新安装
pip install -e .
```

### `vector-studio` 命令未找到

**现象**：安装后运行 `vector-studio` 提示命令不存在。

**解决**：

1. 确认虚拟环境已激活（提示符前有 `(.venv)`）
2. 确认安装成功：`pip list | grep bitmap-vector-studio`
3. 尝试用 Python 模块方式运行：`python -m vector_studio.cli`
4. 或直接使用 `python src/vector_studio/cli.py`

### Streamlit 启动后浏览器空白

**现象**：运行 `streamlit run app.py` 后浏览器显示空白或加载失败。

**解决**：

1. 检查终端输出的本地地址（通常是 `http://localhost:8501`）
2. 尝试手动在浏览器中打开该地址
3. 检查防火墙是否拦截了 8501 端口
4. 尝试指定其他端口：`streamlit run app.py --server.port 8502`

### VTracer 转换报错

**现象**：`trace_image()` 抛出异常。

**解决**：

1. 检查输入图片格式是否受支持（PNG、JPG、WEBP、BMP、TIFF）
2. 检查图片文件是否损坏：用图片查看器打开确认
3. 尝试降低分辨率：`--max-input-side 1200`
4. 查看完整错误堆栈，确认是 VTracer 问题还是预处理问题

### EPS 导出失败

**现象**：`--export-eps` 报错或没有生成 EPS 文件。

**解决**：

1. 确认 Inkscape 已安装：`inkscape --version`
2. 确认 Inkscape 在 PATH 中：`which inkscape`（macOS/Linux）或 `where inkscape`（Windows）
3. 若使用 Snap/Flatpak 安装的 Inkscape，确保别名正确

### 外部编辑器检测不到

**现象**：GUI 中「外部编辑器」区域显示「未检测到可用的外部矢量编辑器」。

**解决**：

1. 确认编辑器已安装
2. 对于 Windows，检查注册表或常见安装路径
3. 对于 macOS，确认 `.app` 在 `/Applications` 中
4. 对于 Linux，确保可执行文件在 PATH 中
5. 手动指定编辑器路径的功能将在未来版本支持

### 历史记录文件损坏

**现象**：历史记录面板显示异常或加载失败。

**解决**：

```bash
# 删除历史记录文件（会丢失所有历史）
rm ~/.bitmap_vector_studio/history.jsonl

# 或仅清空历史
python -c "from vector_studio.history import clear_history; clear_history()"
```

---

## 🆘 获取帮助

如果以上方法无法解决你的问题：

1. 查看 [README.md](../README.md) 的常见问题部分
2. 搜索 [GitHub Issues](https://github.com/jammyfu/bitmap-vector-studio/issues)
3. 创建新的 Issue，提供以下信息：
   - 操作系统和版本
   - Python 版本
   - 安装方式（pip / 源码）
   - 完整的错误日志
   - 复现步骤
