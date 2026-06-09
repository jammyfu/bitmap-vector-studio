#!/bin/bash
# install-deps.sh — 跨平台依赖安装脚本
# 自动检测平台并安装 Python、Node.js、Rust（如缺失则提示）
# 支持: macOS / Linux / Windows (Git Bash / WSL)

set -euo pipefail

PKG_NAME="bitmap-vector-studio"
MIN_PYTHON_MAJOR=3
MIN_PYTHON_MINOR=9
MIN_NODE_MAJOR=18

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() { printf "${CYAN}[INFO]${NC} %s\n" "$*"; }
ok()   { printf "${GREEN}[OK]${NC}   %s\n" "$*"; }
warn() { printf "${YELLOW}[WARN]${NC} %s\n" "$*"; }
err()  { printf "${RED}[ERR]${NC}  %s\n" "$*" >&2; }

detect_os() {
    case "$(uname -s)" in
        Linux*)     OS=Linux;;
        Darwin*)    OS=macOS;;
        CYGWIN*|MINGW*|MSYS*) OS=Windows;;
        *)          OS=Unknown;;
    esac
    info "检测到操作系统: ${OS}"
}

check_python() {
    if command -v python3 &>/dev/null; then
        PYTHON=python3
    elif command -v python &>/dev/null; then
        PYTHON=python
    else
        err "Python 未安装。请安装 Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+"
        case "${OS}" in
            Linux)
                info "安装提示:"
                info "  Ubuntu/Debian: sudo apt update && sudo apt install python3 python3-pip python3-venv"
                info "  Fedora:        sudo dnf install python3 python3-pip"
                info "  Arch:          sudo pacman -S python python-pip"
                ;;
            macOS)
                info "安装提示: brew install python@3.11"
                ;;
            Windows)
                info "安装提示: 从 https://python.org 下载安装程序，或运行: winget install Python.Python.3.11"
                ;;
        esac
        return 1
    fi

    PY_VERSION=$(${PYTHON} --version 2>&1 | awk '{print $2}')
    PY_MAJOR=$(echo "${PY_VERSION}" | cut -d. -f1)
    PY_MINOR=$(echo "${PY_VERSION}" | cut -d. -f2)

    info "发现 Python ${PY_VERSION}"

    if [ "${PY_MAJOR}" -lt ${MIN_PYTHON_MAJOR} ] || { [ "${PY_MAJOR}" -eq ${MIN_PYTHON_MAJOR} ] && [ "${PY_MINOR}" -lt ${MIN_PYTHON_MINOR} ]; }; then
        err "需要 Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+，当前版本 ${PY_VERSION}"
        return 1
    fi
    ok "Python 版本满足要求"
}

check_node() {
    if command -v node &>/dev/null; then
        NODE_VERSION=$(node --version | sed 's/v//')
        NODE_MAJOR=$(echo "${NODE_VERSION}" | cut -d. -f1)
        info "发现 Node.js ${NODE_VERSION}"
        if [ "${NODE_MAJOR}" -lt ${MIN_NODE_MAJOR} ]; then
            warn "Node.js ${NODE_VERSION} 版本较低，推荐 ${MIN_NODE_MAJOR}+"
        else
            ok "Node.js 版本满足要求"
        fi
    else
        warn "Node.js 未安装 (仅桌面端开发需要)"
        case "${OS}" in
            Linux)
                info "安装提示:"
                info "  Ubuntu/Debian: curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install -y nodejs"
                info "  Fedora:        sudo dnf install nodejs"
                info "  Arch:          sudo pacman -S nodejs npm"
                ;;
            macOS)
                info "安装提示: brew install node@20"
                ;;
            Windows)
                info "安装提示: 从 https://nodejs.org 下载 LTS 安装程序，或运行: winget install OpenJS.NodeJS.LTS"
                ;;
        esac
    fi
}

check_rust() {
    if command -v rustc &>/dev/null; then
        RUST_VERSION=$(rustc --version)
        ok "Rust: ${RUST_VERSION}"
    else
        warn "Rust 未安装 (仅桌面端打包需要)"
        case "${OS}" in
            Linux|macOS)
                info "安装提示: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
                ;;
            Windows)
                info "安装提示: 从 https://rustup.rs 下载 rustup-init.exe"
                ;;
        esac
    fi
}

install_system_deps() {
    info "安装系统依赖 (Cairo)..."
    case "${OS}" in
        Linux)
            if command -v apt-get &>/dev/null; then
                sudo apt-get update -qq
                sudo apt-get install -y -qq libcairo2-dev libffi-dev build-essential curl || true
            elif command -v dnf &>/dev/null; then
                sudo dnf install -y cairo-devel libffi-devel gcc curl || true
            elif command -v pacman &>/dev/null; then
                sudo pacman -S --noconfirm cairo libffi base-devel curl || true
            else
                warn "无法检测包管理器，请手动安装 Cairo"
            fi
            ;;
        macOS)
            if command -v brew &>/dev/null; then
                brew install cairo libffi || true
            else
                warn "未找到 Homebrew，请手动安装 Cairo"
            fi
            ;;
        Windows)
            warn "Windows: 请确保 Cairo 可用 (通常通过预编译 wheel 已包含)"
            ;;
        *)
            warn "未知操作系统，请手动安装 Cairo"
            ;;
    esac
    ok "系统依赖处理完成"
}

install_python_deps() {
    info "安装 Python 依赖..."
    ${PYTHON} -m pip install --upgrade pip setuptools wheel
    ${PYTHON} -m pip install -e ".[api,smart]"
    ok "Python 依赖安装完成"
}

verify_installation() {
    info "验证安装..."
    if command -v vector-studio &>/dev/null; then
        vector-studio --help >/dev/null 2>&1 || true
        ok "vector-studio CLI 可用"
    else
        warn "vector-studio 未在 PATH 中找到，尝试通过 Python 模块运行..."
        ${PYTHON} -m vector_studio.cli --help >/dev/null 2>&1 || true
    fi

    # 验证 streamlit
    if ${PYTHON} -c "import streamlit" 2>/dev/null; then
        ok "Streamlit 已安装"
    else
        warn "Streamlit 未安装"
    fi

    # 验证 fastapi
    if ${PYTHON} -c "import fastapi" 2>/dev/null; then
        ok "FastAPI 已安装"
    else
        warn "FastAPI 未安装 (API 服务需要)"
    fi
}

main() {
    info "Bitmap Vector Studio 依赖安装脚本"
    detect_os

    if ! check_python; then
        err "Python 检查失败，无法继续安装依赖"
        exit 1
    fi

    check_node
    check_rust
    install_system_deps
    install_python_deps
    verify_installation
    ok "全部完成! 运行 './scripts/start.sh' 启动应用"
}

main "$@"
