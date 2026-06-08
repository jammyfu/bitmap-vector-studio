@echo off
setlocal enabledelayedexpansion

REM Bitmap Vector Studio Desktop Build Script (Windows)
REM Builds the Tauri desktop application for Windows.

echo === Bitmap Vector Studio Desktop Build ===
echo Platform: Windows

REM Check prerequisites
where node >nul 2>nul
if errorlevel 1 (
    echo Error: Node.js not found. Please install Node.js 20+.
    exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
    echo Error: npm not found.
    exit /b 1
)

where cargo >nul 2>nul
if errorlevel 1 (
    echo Error: Rust / cargo not found. Please install Rust.
    exit /b 1
)

REM Verify Node version
for /f "tokens=1 delims=." %%a in ('node -v') do (
    set NODE_MAJOR=%%a
)
set NODE_MAJOR=%NODE_MAJOR:~1%
if %NODE_MAJOR% LSS 18 (
    echo Error: Node.js 18+ required.
    exit /b 1
)

REM Install frontend dependencies
echo [1/3] Installing frontend dependencies...
cd desktop
call npm install
if errorlevel 1 (
    echo Error: npm install failed.
    exit /b 1
)

REM Build frontend
echo [2/3] Building frontend...
call npm run build
if errorlevel 1 (
    echo Error: npm run build failed.
    exit /b 1
)

REM Build Tauri app
echo [3/3] Building Tauri app...
cargo tauri build
if errorlevel 1 (
    echo Error: cargo tauri build failed.
    exit /b 1
)

echo.
echo === Build complete ===
echo Artifacts located in: desktop\src-tauri\target\release\bundle\
