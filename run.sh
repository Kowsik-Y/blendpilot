#!/usr/bin/env bash
# ==============================================================================
#  BlendPilot AI — All-in-One Services Launcher (Next.js + FastAPI + Blender)
# ==============================================================================

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Colors for output
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${CYAN}${BOLD}"
cat << "EOF"
===============================================================
       ____  _                 _ ____  _ _       _      _    ___ 
      | __ )| | ___ _ __   __| |  _ \(_) | ___ | |_   / \  |_ _|
      |  _ \| |/ _ \ '_ \ / _` | |_) | | |/ _ \| __| / _ \  | | 
      | |_) | |  __/ | | | (_| |  __/| | | (_) | |_ / ___ \ | | 
      |____/|_|\___|_| |_|\__,_|_|   |_|_|\___/ \__/_/   \_\___|
      
     Autonomous 10-Agent Copilot for Blender 3D Modeling
===============================================================
EOF
echo -e "${NC}"

# ── 1. Python Environment Check ──────────────────────────────
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
if [ ! -f "$VENV_PYTHON" ]; then
    echo -e "${YELLOW}[!] Python virtual environment (.venv) not found. Setting up...${NC}"
    python3 -m venv "$PROJECT_DIR/.venv"
    "$PROJECT_DIR/.venv/bin/pip" install --upgrade pip
    if [ -f "$PROJECT_DIR/pyproject.toml" ]; then
        "$PROJECT_DIR/.venv/bin/pip" install -e .
    fi
fi

# ── 2. Node.js & Next.js Dependencies Check ─────────────────
if [ -d "$PROJECT_DIR/ui" ]; then
    if [ ! -d "$PROJECT_DIR/ui/node_modules" ]; then
        echo -e "${YELLOW}[!] Node modules not found in ui/. Installing...${NC}"
        (cd "$PROJECT_DIR/ui" && npm install)
    fi
fi

# ── 3. Blender Binary Detection ──────────────────────────────
BLENDER_BIN=""
if [ -n "$BLENDER_PATH" ] && [ -x "$BLENDER_PATH" ]; then
    BLENDER_BIN="$BLENDER_PATH"
elif [ -x "/Applications/Blender.app/Contents/MacOS/Blender" ]; then
    BLENDER_BIN="/Applications/Blender.app/Contents/MacOS/Blender"
elif command -v blender >/dev/null 2>&1; then
    BLENDER_BIN="$(command -v blender)"
fi

# Track child PIDs for clean exit
PIDS=()

cleanup() {
    echo -e "\n${YELLOW}[*] Shutting down all BlendPilot services...${NC}"
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
        fi
    done
    echo -e "${GREEN}[✔] All services stopped cleanly. Goodbye!${NC}"
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# ── 4. Start Blender Bridge Server ───────────────────────────
if [ -n "$BLENDER_BIN" ]; then
    echo -e "${GREEN}[+] Starting Blender Bridge Server (${BLENDER_BIN})...${NC}"
    "$VENV_PYTHON" "$PROJECT_DIR/scripts/start_blender_bridge.py" --host 127.0.0.1 --port 9876 &
    BLENDER_PID=$!
    PIDS+=($BLENDER_PID)
    echo -e "${GREEN}[✔] Blender Bridge running on http://127.0.0.1:9876 (PID: ${BLENDER_PID})${NC}"
else
    echo -e "${YELLOW}[!] Blender not found in standard paths. Operating in simulated fallback mode.${NC}"
fi

# ── 5. Start FastAPI Backend API ────────────────────────────
echo -e "${GREEN}[+] Starting BlendPilot FastAPI Backend API on port 8000...${NC}"
"$VENV_PYTHON" -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
PIDS+=($BACKEND_PID)

# ── 6. Start Next.js Frontend ───────────────────────────────
if [ -d "$PROJECT_DIR/ui" ]; then
    echo -e "${GREEN}[+] Starting Next.js Frontend Dev Server on port 3000...${NC}"
    (cd "$PROJECT_DIR/ui" && npm run dev) &
    NEXT_PID=$!
    PIDS+=($NEXT_PID)
fi

sleep 2

echo -e "\n${BOLD}${GREEN}===============================================================${NC}"
echo -e "${BOLD}${GREEN} ✔ All BlendPilot Services are Live and Connected!${NC}"
echo -e "${BOLD}${CYAN}   🌐 Next.js Frontend UI:   ${NC}${BOLD}http://localhost:3000${NC}"
echo -e "${BOLD}${CYAN}   🚀 3D Studio Workspace:  ${NC}${BOLD}http://localhost:3000/studio${NC}"
echo -e "${BOLD}${CYAN}   📡 FastAPI Backend API:   ${NC}${BOLD}http://localhost:8000/docs${NC}"
echo -e "${BOLD}${CYAN}   🔌 Blender Bridge:       ${NC}${BOLD}http://127.0.0.1:9876${NC}"
echo -e "${BOLD}${GREEN}===============================================================${NC}"
echo -e "${YELLOW}Press [Ctrl+C] anytime to stop all services.${NC}\n"

# Automatically open Next.js UI in the browser
if command -v open >/dev/null 2>&1; then
    open "http://localhost:3000/studio"
elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "http://localhost:3000/studio"
fi

# Wait on all background processes
wait
