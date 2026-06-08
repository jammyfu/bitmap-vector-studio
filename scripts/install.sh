#!/usr/bin/env bash
# install.sh — Cross-platform one-liner installer for Bitmap Vector Studio
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/jammyfu/bitmap-vector-studio/main/scripts/install.sh | bash
set -euo pipefail

PKG_NAME="bitmap-vector-studio"
REPO="jammyfu/bitmap-vector-studio"
MIN_PYTHON_MAJOR=3
MIN_PYTHON_MINOR=9

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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
    info "Detected OS: ${OS}"
}

check_python() {
    if command -v python3 &>/dev/null; then
        PYTHON=python3
    elif command -v python &>/dev/null; then
        PYTHON=python
    else
        err "Python is not installed. Please install Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+ first."
        exit 1
    fi

    PY_VERSION=$(${PYTHON} --version 2>&1 | awk '{print $2}')
    PY_MAJOR=$(echo "${PY_VERSION}" | cut -d. -f1)
    PY_MINOR=$(echo "${PY_VERSION}" | cut -d. -f2)

    info "Found Python ${PY_VERSION}"

    if [ "${PY_MAJOR}" -lt ${MIN_PYTHON_MAJOR} ] || { [ "${PY_MAJOR}" -eq ${MIN_PYTHON_MAJOR} ] && [ "${PY_MINOR}" -lt ${MIN_PYTHON_MINOR} ]; }; then
        err "Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+ is required. Found ${PY_VERSION}."
        exit 1
    fi
    ok "Python version is sufficient"
}

install_system_deps() {
    info "Installing system dependencies (Cairo)..."
    case "${OS}" in
        Linux)
            if command -v apt-get &>/dev/null; then
                sudo apt-get update -qq
                sudo apt-get install -y -qq libcairo2 libffi8 || true
            elif command -v dnf &>/dev/null; then
                sudo dnf install -y cairo libffi || true
            elif command -v pacman &>/dev/null; then
                sudo pacman -S --noconfirm cairo libffi || true
            else
                warn "Could not detect package manager. Please install Cairo manually."
            fi
            ;;
        macOS)
            if command -v brew &>/dev/null; then
                brew install cairo libffi || true
            else
                warn "Homebrew not found. Please install Cairo manually."
            fi
            ;;
        Windows)
            warn "Windows: please ensure Cairo is available (e.g., via MSYS2 or prebuilt wheels)."
            ;;
        *)
            warn "Unknown OS. Please install Cairo manually."
            ;;
    esac
    ok "System dependencies installed (or already present)"
}

install_package() {
    info "Installing ${PKG_NAME} from PyPI..."
    ${PYTHON} -m pip install --upgrade pip
    ${PYTHON} -m pip install --upgrade "${PKG_NAME}[api,smart]"
    ok "Package installed"
}

verify_installation() {
    info "Verifying installation..."
    if command -v vector-studio &>/dev/null; then
        vector-studio --help >/dev/null 2>&1 || true
        ok "vector-studio CLI is available"
    else
        warn "vector-studio not found in PATH. You may need to add Python user scripts to PATH."
        ${PYTHON} -m vector_studio.cli --help >/dev/null 2>&1 || true
    fi
}

main() {
    info "Bitmap Vector Studio Installer"
    detect_os
    check_python
    install_system_deps
    install_package
    verify_installation
    ok "Installation complete! Run 'vector-studio --help' to get started."
}

main "$@"
