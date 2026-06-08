$ErrorActionPreference = 'Stop'

$packageName = 'bitmap-vector-studio'
$toolsDir = "$(Split-Path -Parent $MyInvocation.MyCommand.Definition)"

# Ensure Python 3.9+ is available
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "Python is not found in PATH. Please install Python 3.9+ first." -ForegroundColor Red
    exit 1
}

$pyVersion = & python --version 2>&1
if ($pyVersion -notmatch "Python 3\.(9|[1-9][0-9])") {
    Write-Host "Python 3.9+ is required. Found: $pyVersion" -ForegroundColor Red
    exit 1
}

# Install from PyPI
Write-Host "Installing bitmap-vector-studio from PyPI..." -ForegroundColor Cyan
& python -m pip install --upgrade bitmap-vector-studio[api,smart]

if ($LASTEXITCODE -ne 0) {
    Write-Host "Installation failed." -ForegroundColor Red
    exit 1
}

Write-Host "bitmap-vector-studio installed successfully." -ForegroundColor Green
Write-Host "Run 'vector-studio --help' to get started." -ForegroundColor Green
