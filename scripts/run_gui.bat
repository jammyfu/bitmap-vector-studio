@echo off
setlocal EnableDelayedExpansion

:: Bitmap Vector Studio - Windows GUI Launcher
:: Version: 0.2.0

set "PROJECT_NAME=Bitmap Vector Studio"
set "VERSION=0.2.0"

:: Display startup info
echo ============================================
echo   %PROJECT_NAME% v%VERSION%
echo ============================================
echo.

:: Check if app.py exists in current directory
if not exist "app.py" (
    echo [ERROR] app.py not found in current directory.
    echo Please run this script from the project root directory.
    pause
    exit /b 1
)

:: Detect and activate virtual environment if present
if exist ".venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment (.venv)...
    call ".venv\Scripts\activate.bat"
) else if exist "venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment (venv)...
    call "venv\Scripts\activate.bat"
) else (
    echo [INFO] No virtual environment found, using system Python.
)

:: Check if streamlit is installed
python -c "import streamlit" 2>nul
if errorlevel 1 (
    echo [ERROR] streamlit is not installed.
    echo Please install dependencies first:
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

:: Launch the GUI
echo [INFO] Starting Streamlit GUI...
echo.
streamlit run app.py

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to start the GUI. Please check the error message above.
    pause
    exit /b 1
)

endlocal
