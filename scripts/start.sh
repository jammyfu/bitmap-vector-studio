#!/bin/bash
# Bitmap Vector Studio 一键启动脚本
# 支持: macOS / Linux / Windows (Git Bash / WSL)

set -euo pipefail

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

PROJECT_NAME="Bitmap Vector Studio"
VERSION="3.0.0"

echo "🎨 ${PROJECT_NAME} 启动器 v${VERSION}"
echo "================================"

# 检查 Python
check_python() {
  if command -v python3 &> /dev/null; then
    PYTHON=python3
  elif command -v python &> /dev/null; then
    PYTHON=python
  else
    echo -e "${RED}❌ Python 未安装${NC}"
    echo "   请安装 Python 3.9+ : https://python.org"
    echo "   或使用 ./scripts/install-deps.sh 自动检测安装"
    exit 1
  fi

  PY_VERSION=$($PYTHON --version 2>&1 | awk '{print $2}')
  PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
  PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

  if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 9 ]; }; then
    echo -e "${RED}❌ Python 3.9+ 是必需的，当前版本: $PY_VERSION${NC}"
    exit 1
  fi

  echo -e "${GREEN}✅ Python: $PY_VERSION${NC}"
}

# 检查 Node.js
check_node() {
  if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✅ Node.js: $NODE_VERSION${NC}"
  else
    echo -e "${YELLOW}⚠️  Node.js 未安装 (仅桌面端需要)${NC}"
    echo "   下载: https://nodejs.org (推荐 LTS 18+)"
  fi
}

# 检查 Rust
check_rust() {
  if command -v rustc &> /dev/null; then
    RUST_VERSION=$(rustc --version)
    echo -e "${GREEN}✅ Rust: $RUST_VERSION${NC}"
  else
    echo -e "${YELLOW}⚠️  Rust 未安装 (仅桌面端打包需要)${NC}"
    echo "   下载: https://rustup.rs"
  fi
}

# 检查虚拟环境
activate_venv() {
  if [[ -d ".venv" && -f ".venv/bin/activate" ]]; then
    echo -e "${CYAN}📦 激活虚拟环境 (.venv)...${NC}"
    # shellcheck source=/dev/null
    source ".venv/bin/activate"
  elif [[ -d "venv" && -f "venv/bin/activate" ]]; then
    echo -e "${CYAN}📦 激活虚拟环境 (venv)...${NC}"
    # shellcheck source=/dev/null
    source "venv/bin/activate"
  fi
}

# 安装 Python 依赖
install_python_deps() {
  echo ""
  echo "📦 安装 Python 依赖..."
  $PYTHON -m pip install -e ".[api,smart]" --quiet 2>/dev/null || {
    echo -e "${YELLOW}⚠️  pip 安装失败，尝试升级 pip...${NC}"
    $PYTHON -m pip install --upgrade pip --quiet
    $PYTHON -m pip install -e ".[api,smart]" --quiet
  }
  echo -e "${GREEN}✅ Python 依赖安装完成${NC}"
}

# 启动 Streamlit GUI
start_streamlit() {
  echo ""
  echo "🚀 启动 Streamlit GUI..."
  echo "   地址: http://localhost:8501"
  $PYTHON -m streamlit run app.py
}

# 启动 API 服务
start_api() {
  echo ""
  echo "🚀 启动 API 服务..."
  echo "   地址: http://localhost:8000"
  echo "   文档: http://localhost:8000/docs"
  $PYTHON -m vector_studio.cli api --host 0.0.0.0 --port 8000
}

# 启动桌面端开发服务器
start_desktop() {
  echo ""
  echo "🚀 启动桌面端开发服务器..."
  cd desktop
  if [ ! -d "node_modules" ]; then
    echo "📦 安装 Node 依赖..."
    npm install
  fi
  npm run tauri:dev
}

# 主菜单
show_menu() {
  echo ""
  echo "请选择启动方式:"
  echo "  1) Streamlit GUI (网页版)"
  echo "  2) API 服务 (RESTful)"
  echo "  3) 桌面端开发模式 (Tauri + React)"
  echo "  4) 检查环境并安装依赖"
  echo "  5) 退出"
  echo ""
  read -rp "输入选项 [1-5]: " choice

  case $choice in
    1) check_python; activate_venv; install_python_deps; start_streamlit ;;
    2) check_python; activate_venv; install_python_deps; start_api ;;
    3) check_node; start_desktop ;;
    4) check_python; check_node; check_rust; install_python_deps ;;
    5) echo "再见!"; exit 0 ;;
    *) echo -e "${RED}无效选项${NC}"; show_menu ;;
  esac
}

# 命令行参数模式
if [ "${1:-}" = "streamlit" ]; then
  check_python; activate_venv; install_python_deps; start_streamlit
elif [ "${1:-}" = "api" ]; then
  check_python; activate_venv; install_python_deps; start_api
elif [ "${1:-}" = "desktop" ]; then
  check_node; start_desktop
elif [ "${1:-}" = "check" ]; then
  check_python; check_node; check_rust
else
  show_menu
fi
