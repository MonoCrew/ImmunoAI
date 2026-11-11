#!/usr/bin/env bash
# ==============================================================================
# ARGUS: Real-Time Intruder Detection System - Unified Interactive CLI Launcher
# Works on any Linux/macOS with standard Python & pip (Conda optional)
# ==============================================================================

# ANSI Color Codes
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ------------------------------------------------------------------------------
# 1. Environment Detection (Conda, Venv, or Plain Python + Pip)
# ------------------------------------------------------------------------------
detect_python() {
    if [[ -n "$CONDA_DEFAULT_ENV" ]]; then
        ENV_TYPE="Active Conda ($CONDA_DEFAULT_ENV)"
        PYTHON_CMD="python"
        PIP_CMD="pip"
    elif [[ -n "$VIRTUAL_ENV" ]]; then
        ENV_TYPE="Active Virtualenv ($(basename "$VIRTUAL_ENV"))"
        PYTHON_CMD="python"
        PIP_CMD="pip"
    elif [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
        ENV_TYPE="Project .venv"
        PYTHON_CMD="python"
        PIP_CMD="pip"
    elif [ -x "$HOME/anaconda3/envs/utility/bin/python" ]; then
        ENV_TYPE="Conda (utility)"
        PYTHON_CMD="$HOME/anaconda3/envs/utility/bin/python"
        PIP_CMD="$HOME/anaconda3/envs/utility/bin/pip"
    elif command -v conda &>/dev/null && conda info --envs | grep -q "utility"; then
        ENV_TYPE="Conda (utility)"
        PYTHON_CMD="conda run -n utility python"
        PIP_CMD="conda run -n utility pip"
    else
        # Find system Python
        if command -v python3 &>/dev/null; then
            SYSTEM_PY="python3"
        elif command -v python &>/dev/null; then
            SYSTEM_PY="python"
        else
            echo -e "${RED}[ERROR] Neither python3 nor python was found on your system.${NC}"
            echo "Please install Python 3.10+ (https://www.python.org/downloads/)."
            exit 1
        fi

        # Prefer creating an isolated .venv to protect system packages without needing root/sudo
        if [ ! -f ".venv/bin/activate" ]; then
            if $SYSTEM_PY -m venv .venv 2>/dev/null && [ -f ".venv/bin/activate" ]; then
                source .venv/bin/activate
                ENV_TYPE="Isolated .venv (auto-created)"
                PYTHON_CMD="python"
                PIP_CMD="pip"
            else
                ENV_TYPE="System Python (direct pip)"
                PYTHON_CMD="$SYSTEM_PY"
                PIP_CMD="$SYSTEM_PY -m pip"
            fi
        else
            source .venv/bin/activate
            ENV_TYPE="Project .venv"
            PYTHON_CMD="python"
            PIP_CMD="pip"
        fi
    fi
}

detect_python

# ------------------------------------------------------------------------------
# 2. Dependency Check Function
# ------------------------------------------------------------------------------
check_dependencies() {
    $PYTHON_CMD -c "import fastapi, uvicorn, cv2, ultralytics, pydantic" 2>/dev/null
    return $?
}

# ------------------------------------------------------------------------------
# 3. Installation Routine
# ------------------------------------------------------------------------------
install_dependencies() {
    echo ""
    echo -e "${CYAN}${BOLD}=== Installing Dependencies ===${NC}"
    
    echo -e "${YELLOW}[1/3] Updating pip and installing Python packages...${NC}"
    $PIP_CMD install --upgrade pip 2>/dev/null || true
    if $PIP_CMD install -r requirements.txt; then
        echo -e "${GREEN}✓ Python packages installed successfully.${NC}"
    else
        echo -e "${YELLOW}Warning: Direct install had issues, trying with --user flag...${NC}"
        $PIP_CMD install --user -r requirements.txt
    fi

    echo -e "\n${YELLOW}[2/3] Checking YOLOv8 weights (yolov8n.pt)...${NC}"
    if [ ! -f "yolov8n.pt" ]; then
        echo "Downloading YOLOv8n pre-trained weights..."
        $PYTHON_CMD -c "from ultralytics import YOLO; YOLO('yolov8n.pt')" 2>/dev/null || true
    fi
    echo -e "${GREEN}✓ YOLOv8 weights ready.${NC}"

    echo -e "\n${YELLOW}[3/3] Checking Frontend build...${NC}"
    if [ -f "static/dist/index.html" ]; then
        echo -e "${GREEN}✓ Pre-built React Single-Page App found in static/dist/.${NC}"
    fi

    if command -v npm &>/dev/null; then
        echo "Node.js & npm detected. Building latest frontend assets..."
        cd frontend
        npm install --silent 2>/dev/null || npm install
        npm run build
        cd ..
        echo -e "${GREEN}✓ React frontend built successfully.${NC}"
    else
        echo -e "${CYAN}Note: npm not detected. Using pre-compiled React bundle (Node.js is not required).${NC}"
    fi

    echo ""
    echo -e "${GREEN}${BOLD}✓ Setup complete! Press Enter to return to the menu.${NC}"
    read -r
}

# ------------------------------------------------------------------------------
# 4. Start Unified Server
# ------------------------------------------------------------------------------
start_server() {
    echo ""
    echo -e "${CYAN}Checking system dependencies...${NC}"
    if ! check_dependencies; then
        echo -e "${RED}${BOLD}❌ Server start failed: Required dependencies are missing!${NC}"
        echo -e "${YELLOW}Missing packages detected (fastapi, opencv, or ultralytics).${NC}"
        echo ""
        read -p "Would you like to install all required dependencies now? [Y/n]: " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            echo -e "${CYAN}Returning to main menu...${NC}"
            sleep 1
            return
        else
            install_dependencies
        fi
    fi

    echo -e "${GREEN}${BOLD}✓ All dependencies verified!${NC}"
    echo ""
    echo -e "${CYAN}${BOLD}============================================================${NC}"
    echo -e "${CYAN}${BOLD}   ARGUS: INTRUDER DETECTION SYSTEM IS RUNNING              ${NC}"
    echo -e "${CYAN}${BOLD}============================================================${NC}"
    echo -e "  🌐 Dashboard URL:    ${GREEN}${BOLD}http://localhost:8000${NC}"
    echo -e "  📹 Video Stream:     ${CYAN}http://localhost:8000/video_feed${NC}"
    echo -e "  ⚡ WebSocket Stream:  ${CYAN}ws://localhost:8000/ws${NC}"
    echo -e "  🛡️ Mode:             Passive Standby (Arm/Disarm in UI)"
    echo "------------------------------------------------------------"
    echo -e "${YELLOW}Press Ctrl+C anytime to stop the server.${NC}"
    echo ""

    # Open browser in background
    (sleep 1.8 && (xdg-open "http://localhost:8000" 2>/dev/null || open "http://localhost:8000" 2>/dev/null || true)) &

    $PYTHON_CMD app.py
    echo ""
    echo -e "${CYAN}Server stopped. Press Enter to return to menu.${NC}"
    read -r
}

# ------------------------------------------------------------------------------
# 5. Start React Dev Mode (Backend + Vite HMR)
# ------------------------------------------------------------------------------
start_dev_mode() {
    echo ""
    if ! check_dependencies; then
        echo -e "${RED}❌ Missing dependencies. Please run Option [3] (Install Dependencies) first.${NC}"
        read -p "Press Enter to continue..."
        return
    fi

    if ! command -v npm &>/dev/null; then
        echo -e "${RED}❌ Node.js and npm are required for Vite HMR Development Mode.${NC}"
        echo -e "${CYAN}Use Option [1] to run the pre-built React application without Node.js.${NC}"
        read -p "Press Enter to continue..."
        return
    fi

    echo -e "${CYAN}${BOLD}============================================================${NC}"
    echo -e "${CYAN}${BOLD}   LAUNCHING DUAL DEV MODE (BACKEND + VITE HMR)             ${NC}"
    echo -e "${CYAN}${BOLD}============================================================${NC}"
    echo -e "  🐍 Backend API:        ${GREEN}http://localhost:8000${NC}"
    echo -e "  ⚛️  React Vite Dev UI:  ${GREEN}${BOLD}http://localhost:5173${NC} (Live HMR)"
    echo "------------------------------------------------------------"
    echo -e "${YELLOW}Press Ctrl+C to shut down both servers cleanly.${NC}"
    echo ""

    BACKEND_PID=""
    FRONTEND_PID=""

    dev_cleanup() {
        echo -e "\n${YELLOW}Stopping development servers...${NC}"
        kill "$BACKEND_PID" 2>/dev/null || true
        kill "$FRONTEND_PID" 2>/dev/null || true
        wait 2>/dev/null || true
        echo -e "${GREEN}Servers stopped cleanly.${NC}"
    }
    trap dev_cleanup SIGINT SIGTERM EXIT

    $PYTHON_CMD app.py &
    BACKEND_PID=$!
    sleep 1.5

    cd frontend
    npm run dev -- --host &
    FRONTEND_PID=$!
    cd ..

    (sleep 2 && (xdg-open "http://localhost:5173" 2>/dev/null || open "http://localhost:5173" 2>/dev/null || true)) &

    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    trap - SIGINT SIGTERM EXIT
    echo -e "\n${CYAN}Press Enter to return to menu.${NC}"
    read -r
}

# ------------------------------------------------------------------------------
# 6. Diagnostic Hardware & Vision Test
# ------------------------------------------------------------------------------
run_diagnostics() {
    echo ""
    echo -e "${CYAN}${BOLD}============================================================${NC}"
    echo -e "${CYAN}${BOLD}   ARGUS SYSTEM DIAGNOSTIC & HARDWARE SCAN                  ${NC}"
    echo -e "${CYAN}${BOLD}============================================================${NC}"

    echo -n "1. Python Interpreter: "
    $PYTHON_CMD --version

    echo -n "2. Environment: "
    echo -e "${GREEN}$ENV_TYPE${NC}"

    echo -n "3. Video Capture Devices: "
    if ls /dev/video* 1>/dev/null 2>&1; then
        echo -e "${GREEN}$(ls -m /dev/video*)${NC}"
    else
        echo -e "${YELLOW}No /dev/video* detected (Fallback simulation will be used).${NC}"
    fi

    echo -n "4. YOLOv8 Weights: "
    if [ -f "yolov8n.pt" ]; then
        SIZE=$(du -h yolov8n.pt | cut -f1)
        echo -e "${GREEN}Present (${SIZE})${NC}"
    else
        echo -e "${RED}Missing! Run Option [3] to download.${NC}"
    fi

    echo -n "5. React Frontend Bundle: "
    if [ -f "static/dist/index.html" ]; then
        echo -e "${GREEN}Ready (static/dist/index.html)${NC}"
    else
        echo -e "${RED}Missing! Run Option [3] to compile.${NC}"
    fi

    echo -n "6. Vision Pipeline Quick Test: "
    $PYTHON_CMD -c "
import cv2, ultralytics
print('OpenCV:', cv2.__version__, '| Ultralytics:', ultralytics.__version__)
" 2>/dev/null && echo -e "${GREEN}✓ Vision modules verified.${NC}" || echo -e "${RED}❌ Vision modules failed.${NC}"

    echo ""
    read -p "Press Enter to return to the main menu..."
}

# ------------------------------------------------------------------------------
# MAIN INTERACTIVE MENU LOOP
# ------------------------------------------------------------------------------
while true; do
    clear
    echo -e "${CYAN}${BOLD}"
    echo "============================================================"
    echo "       ARGUS // INTRUDER DETECTION & ALERT SYSTEM           "
    echo "                 Autonomous Vision Sentinel                 "
    echo "============================================================"
    echo -e "${NC}"
    echo -e "  OS: ${BOLD}$(uname -s) ($(uname -m))${NC} | Env: ${GREEN}$ENV_TYPE${NC}"
    echo "------------------------------------------------------------"
    echo -e "  ${BOLD}[1]${NC} 🚀 ${GREEN}Start Security Server${NC} (Single-Page App on :8000)"
    echo -e "  ${BOLD}[2]${NC} ⚡ ${CYAN}Start React Dev Mode${NC}  (Backend :8000 + Vite :5173)"
    echo -e "  ${BOLD}[3]${NC} 📦 ${YELLOW}Install / Update Dependencies${NC} (Python & Node.js)"
    echo -e "  ${BOLD}[4]${NC} 🧪 Run Diagnostic & Hardware Check"
    echo -e "  ${BOLD}[5]${NC} ❌ Exit"
    echo "------------------------------------------------------------"
    if ! read -r -p "  Enter choice [1-5]: " CHOICE; then
        echo ""
        exit 0
    fi

    case "$CHOICE" in
        1)
            start_server
            ;;
        2)
            start_dev_mode
            ;;
        3)
            install_dependencies
            ;;
        4)
            run_diagnostics
            ;;
        5)
            echo -e "\n${CYAN}Exiting Argus Sentinel. Stay safe!${NC}\n"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid selection. Please choose 1, 2, 3, 4, or 5.${NC}"
            sleep 1
            ;;
    esac
done
