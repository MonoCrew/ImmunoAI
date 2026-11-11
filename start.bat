@echo off
REM ==============================================================================
REM ARGUS: Real-Time Intruder Detection System - Unified Interactive CLI Launcher
REM Works on Windows with standard Python & pip (Conda optional)
REM ==============================================================================
title Argus Intruder Detection System
color 0B

cd /d "%~dp0"

:detect_env
REM Check for Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    cls
    echo ============================================================
    echo   [ERROR] Python was not found in your system PATH!
    echo ============================================================
    echo Please install Python 3.10+ from https://www.python.org/
    echo NOTE: Ensure you check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

REM Determine Environment
set "ENV_NAME=System Python (pip)"
if defined CONDA_DEFAULT_ENV (
    set "ENV_NAME=Conda (%CONDA_DEFAULT_ENV%)"
) else if defined VIRTUAL_ENV (
    set "ENV_NAME=Virtualenv"
) else (
    if not exist ".venv" (
        echo Setting up isolated project environment (.venv)...
        python -m venv .venv 2>nul
    )
    if exist ".venv\Scripts\activate.bat" (
        call .venv\Scripts\activate.bat
        set "ENV_NAME=Local .venv"
    )
)

:menu
cls
echo ============================================================
echo        ARGUS // INTRUDER DETECTION ^& ALERT SYSTEM           
echo                  Autonomous Vision Sentinel                 
echo ============================================================
echo   Platform: Windows ^| Environment: %ENV_NAME%
echo ------------------------------------------------------------
echo   [1] 🚀 Start Security Server (Single-Page App on :8000)
echo   [2] ⚡ Start React Dev Mode  (Backend :8000 + Vite :5173)
echo   [3] 📦 Install / Update Dependencies (Python ^& Node.js)
echo   [4] 🧪 Run Diagnostic ^& Hardware Check
echo   [5] ❌ Exit
echo ------------------------------------------------------------
set /p CHOICE="  Enter choice [1-5]: "

if "%CHOICE%"=="1" goto start_server
if "%CHOICE%"=="2" goto start_dev
if "%CHOICE%"=="3" goto install_deps
if "%CHOICE%"=="4" goto run_diagnostics
if "%CHOICE%"=="5" goto exit_app

echo [ERROR] Invalid selection. Please enter 1, 2, 3, 4, or 5.
timeout /t 1 >nul
goto menu

:start_server
cls
echo Checking dependencies...
python -c "import fastapi, uvicorn, cv2, ultralytics, pydantic" >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo ============================================================
    echo  [!] SERVER START FAILED: Required dependencies are missing!
    echo ============================================================
    echo Missing packages detected (fastapi, opencv, or ultralytics).
    echo.
    set /p INSTALL_CONFIRM="Would you like to install them now? (Y/N): "
    if /i "%INSTALL_CONFIRM%"=="Y" (
        goto install_deps
    ) else (
        goto menu
    )
)

echo [OK] All dependencies verified.
echo.
echo ============================================================
echo    ARGUS: INTRUDER DETECTION SYSTEM IS RUNNING (WINDOWS)     
echo ============================================================
echo   Web Dashboard:    http://localhost:8000
echo   Video Stream:     http://localhost:8000/video_feed
echo   WebSocket Feed:   ws://localhost:8000/ws
echo   Mode:             Passive Standby (Arm/Disarm in UI)
echo ------------------------------------------------------------
echo Press Ctrl+C anytime to stop the server.
echo.

REM Open browser after 2 seconds
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:8000"

python app.py
echo.
echo Server stopped.
pause
goto menu

:start_dev
cls
echo Checking dependencies...
python -c "import fastapi, uvicorn, cv2, ultralytics, pydantic" >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Missing Python dependencies. Please run Option [3] first.
    pause
    goto menu
)

where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Node.js and npm are required for Vite HMR Dev Mode.
    echo Please install Node.js from https://nodejs.org or use Option [1].
    pause
    goto menu
)

echo ============================================================
echo    LAUNCHING DUAL DEV MODE (BACKEND + VITE HMR)
echo ============================================================
echo   Backend API:        http://localhost:8000
echo   React Vite Dev UI:  http://localhost:5173 (Live HMR)
echo.

start "Argus Backend (:8000)" cmd /k "if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat & python app.py"
cd frontend
start "Argus React Frontend (:5173)" cmd /k "npm run dev"
cd ..

start "" cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:5173"

echo Servers launched in separate windows. Close windows to stop.
pause
goto menu

:install_deps
cls
echo ============================================================
echo    INSTALLING DEPENDENCIES (PYTHON ^& NODE.JS)
echo ============================================================
echo.
echo [1/3] Updating pip and installing Python packages...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [WARNING] Retrying install with --user flag...
    python -m pip install --user -r requirements.txt
)
echo [OK] Python dependencies ready.

echo.
echo [2/3] Checking YOLOv8 weights (yolov8n.pt)...
if not exist "yolov8n.pt" (
    echo Downloading YOLOv8 weights...
    python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
)
echo [OK] YOLOv8 weights ready.

echo.
echo [3/3] Checking Frontend build...
if exist "static\dist\index.html" (
    echo [OK] Pre-built React Single-Page App found in static\dist\.
)

where npm >nul 2>nul
if %errorlevel% equ 0 (
    echo Node.js detected. Building latest frontend assets...
    cd frontend
    call npm install
    call npm run build
    cd ..
    echo [OK] React frontend built successfully.
) else (
    echo [NOTE] npm not detected. Using pre-compiled React bundle (Node.js is not required).
)

echo.
echo [SUCCESS] Dependencies installed successfully!
pause
goto menu

:run_diagnostics
cls
echo ============================================================
echo    ARGUS SYSTEM DIAGNOSTIC ^& HARDWARE SCAN (WINDOWS)
echo ============================================================
echo.
echo 1. Python Version:
python --version
echo.
echo 2. Environment Type: %ENV_NAME%
echo.
echo 3. YOLOv8 Weights:
if exist "yolov8n.pt" (
    echo    [OK] yolov8n.pt is present.
) else (
    echo    [MISSING] Run Option [3] to download.
)
echo.
echo 4. React Single-Page Bundle:
if exist "static\dist\index.html" (
    echo    [OK] static\dist\index.html is ready.
) else (
    echo    [MISSING] Run Option [3] to compile.
)
echo.
echo 5. Vision Pipeline Module Test:
python -c "import cv2, ultralytics; print('[OK] OpenCV:', cv2.__version__, '| Ultralytics:', ultralytics.__version__)" 2>nul
if %errorlevel% neq 0 (
    echo    [ERROR] Vision modules failed to load.
)
echo.
pause
goto menu

:exit_app
cls
echo Exiting Argus Sentinel. Stay safe!
timeout /t 1 >nul
exit /b 0
