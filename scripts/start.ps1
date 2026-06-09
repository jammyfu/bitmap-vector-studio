#!/usr/bin/env pwsh
# Bitmap Vector Studio 一键启动脚本 (PowerShell)
# 支持: Windows PowerShell 5.1+ / PowerShell 7+

$ErrorActionPreference = "Stop"

$PROJECT_NAME = "Bitmap Vector Studio"
$VERSION = "3.0.0"

# 颜色输出
$Red = "`e[0;31m"
$Green = "`e[0;32m"
$Yellow = "`e[1;33m"
$Cyan = "`e[0;36m"
$NC = "`e[0m"

function Write-Info { param([string]$msg) Write-Host "${Cyan}[INFO]${NC} $msg" }
function Write-Ok { param([string]$msg) Write-Host "${Green}[OK]${NC}   $msg" }
function Write-Warn { param([string]$msg) Write-Host "${Yellow}[WARN]${NC} $msg" }
function Write-Err { param([string]$msg) Write-Host "${Red}[ERR]${NC}  $msg" }

Write-Host "🎨 ${PROJECT_NAME} 启动器 v${VERSION}"
Write-Host "================================"

# 检查 Python
function Check-Python {
    $pythonCmd = $null
    if (Get-Command python3 -ErrorAction SilentlyContinue) {
        $pythonCmd = "python3"
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        $pythonCmd = "python"
    } else {
        Write-Err "Python 未安装"
        Write-Host "   请安装 Python 3.9+ : https://python.org"
        Write-Host "   或使用 .\scripts\install-deps.ps1 自动检测安装"
        exit 1
    }

    $pyVersion = & $pythonCmd --version 2>&1
    $pyVersion = $pyVersion -replace "Python ", ""
    $parts = $pyVersion.Split(".")
    $major = [int]$parts[0]
    $minor = [int]$parts[1]

    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 9)) {
        Write-Err "Python 3.9+ 是必需的，当前版本: $pyVersion"
        exit 1
    }

    Write-Ok "Python: $pyVersion"
    return $pythonCmd
}

# 检查 Node.js
function Check-Node {
    if (Get-Command node -ErrorAction SilentlyContinue) {
        $nodeVersion = node --version
        Write-Ok "Node.js: $nodeVersion"
    } else {
        Write-Warn "Node.js 未安装 (仅桌面端需要)"
        Write-Host "   下载: https://nodejs.org (推荐 LTS 18+)"
    }
}

# 检查 Rust
function Check-Rust {
    if (Get-Command rustc -ErrorAction SilentlyContinue) {
        $rustVersion = rustc --version
        Write-Ok "Rust: $rustVersion"
    } else {
        Write-Warn "Rust 未安装 (仅桌面端打包需要)"
        Write-Host "   下载: https://rustup.rs"
    }
}

# 检查虚拟环境
function Activate-Venv {
    if (Test-Path ".venv\Scripts\Activate.ps1") {
        Write-Info "激活虚拟环境 (.venv)..."
        & .venv\Scripts\Activate.ps1
    } elseif (Test-Path "venv\Scripts\Activate.ps1") {
        Write-Info "激活虚拟环境 (venv)..."
        & venv\Scripts\Activate.ps1
    }
}

# 安装 Python 依赖
function Install-PythonDeps {
    param([string]$Python)
    Write-Host ""
    Write-Info "安装 Python 依赖..."
    try {
        & $Python -m pip install -e ".[api,smart]" --quiet 2>$null
    } catch {
        Write-Warn "pip 安装失败，尝试升级 pip..."
        & $Python -m pip install --upgrade pip --quiet
        & $Python -m pip install -e ".[api,smart]" --quiet
    }
    Write-Ok "Python 依赖安装完成"
}

# 启动 Streamlit GUI
function Start-Streamlit {
    param([string]$Python)
    Write-Host ""
    Write-Info "启动 Streamlit GUI..."
    Write-Host "   地址: http://localhost:8501"
    & $Python -m streamlit run app.py
}

# 启动 API 服务
function Start-Api {
    param([string]$Python)
    Write-Host ""
    Write-Info "启动 API 服务..."
    Write-Host "   地址: http://localhost:8000"
    Write-Host "   文档: http://localhost:8000/docs"
    & $Python -m vector_studio.cli api --host 0.0.0.0 --port 8000
}

# 启动桌面端开发服务器
function Start-Desktop {
    Write-Host ""
    Write-Info "启动桌面端开发服务器..."
    Set-Location desktop
    if (-not (Test-Path "node_modules")) {
        Write-Info "安装 Node 依赖..."
        npm install
    }
    npm run tauri:dev
}

# 主菜单
function Show-Menu {
    Write-Host ""
    Write-Host "请选择启动方式:"
    Write-Host "  1) Streamlit GUI (网页版)"
    Write-Host "  2) API 服务 (RESTful)"
    Write-Host "  3) 桌面端开发模式 (Tauri + React)"
    Write-Host "  4) 检查环境并安装依赖"
    Write-Host "  5) 退出"
    Write-Host ""
    $choice = Read-Host "输入选项 [1-5]"

    switch ($choice) {
        "1" {
            $py = Check-Python
            Activate-Venv
            Install-PythonDeps -Python $py
            Start-Streamlit -Python $py
        }
        "2" {
            $py = Check-Python
            Activate-Venv
            Install-PythonDeps -Python $py
            Start-Api -Python $py
        }
        "3" {
            Check-Node
            Start-Desktop
        }
        "4" {
            $py = Check-Python
            Check-Node
            Check-Rust
            Install-PythonDeps -Python $py
        }
        "5" {
            Write-Host "再见!"
            exit 0
        }
        default {
            Write-Err "无效选项"
            Show-Menu
        }
    }
}

# 命令行参数模式
switch ($args[0]) {
    "streamlit" {
        $py = Check-Python
        Activate-Venv
        Install-PythonDeps -Python $py
        Start-Streamlit -Python $py
    }
    "api" {
        $py = Check-Python
        Activate-Venv
        Install-PythonDeps -Python $py
        Start-Api -Python $py
    }
    "desktop" {
        Check-Node
        Start-Desktop
    }
    "check" {
        Check-Python
        Check-Node
        Check-Rust
    }
    default {
        Show-Menu
    }
}
