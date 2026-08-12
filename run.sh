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

# Track service process groups owned by this invocation, including any reused
# healthy services so Ctrl+C can stop everything the launcher attached to.
STOP_TARGETS=()
CLEANED_UP=0

register_stop_target() {
    local target="$1"
    if [ -n "$target" ] && [[ ! " ${STOP_TARGETS[*]} " =~ " ${target} " ]]; then
        STOP_TARGETS+=("$target")
    fi
}

register_port_owner() {
    local port="$1"
    local pid
    pid="$(lsof -ti tcp:"$port" 2>/dev/null | head -n 1 || true)"
    if [ -n "$pid" ]; then
        local pgid
        pgid="$(ps -o pgid= -p "$pid" 2>/dev/null | tr -d ' ' || true)"
        if [ -n "$pgid" ]; then
            register_stop_target "-$pgid"
        else
            register_stop_target "$pid"
        fi
    fi
}

is_healthy() {
    curl --silent --show-error --fail --max-time 2 "$1" >/dev/null 2>&1
}

wait_for_service() {
    local url="$1"
    local label="$2"
    local attempts=20

    while [ "$attempts" -gt 0 ]; do
        if is_healthy "$url"; then
            return 0
        fi
        sleep 0.5
        attempts=$((attempts - 1))
    done

    echo -e "${RED}[✘] ${label} did not become healthy at ${url}.${NC}"
    return 1
}

cleanup() {
    if [ "$CLEANED_UP" -eq 1 ]; then
        return 0
    fi
    CLEANED_UP=1

    echo -e "\n${YELLOW}[*] Shutting down all BlendPilot services...${NC}"
    for target in "${STOP_TARGETS[@]}"; do
        target="${target#-}" # Remove leading dash if any
        if kill -0 "$target" 2>/dev/null; then
            pkill -P "$target" 2>/dev/null || true
            kill -TERM "$target" 2>/dev/null || true
        fi
    done
    sleep 0.5
    for target in "${STOP_TARGETS[@]}"; do
        target="${target#-}"
        if kill -0 "$target" 2>/dev/null; then
            kill -KILL "$target" 2>/dev/null || true
        fi
    done
    
    # Bulletproof cleanup for ports just in case a child process detached
    for port in 3000 8000 8001 9876; do
        pid=$(lsof -ti tcp:$port 2>/dev/null | head -n 1)
        if [ -n "$pid" ]; then
            kill -9 "$pid" 2>/dev/null || true
        fi
    done

    echo -e "${GREEN}[✔] All services stopped cleanly. Goodbye!${NC}"
}
trap cleanup SIGINT SIGTERM EXIT

# ── 4. Start Blender Bridge Server ───────────────────────────
if is_healthy "http://127.0.0.1:9876/health"; then
    echo -e "${GREEN}[✔] Reusing Blender Bridge at http://127.0.0.1:9876${NC}"
    register_port_owner 9876
elif [ -n "$BLENDER_BIN" ]; then
    echo -e "${GREEN}[+] Starting Blender Bridge Server (${BLENDER_BIN})...${NC}"
    "$VENV_PYTHON" "$PROJECT_DIR/scripts/start_blender_bridge.py" --host 127.0.0.1 --port 9876 &
    BLENDER_PID=$!
    register_stop_target "-$BLENDER_PID"
    if ! wait_for_service "http://127.0.0.1:9876/health" "Blender Bridge"; then
        exit 1
    fi
    echo -e "${GREEN}[✔] Blender Bridge running on http://127.0.0.1:9876 (PID: ${BLENDER_PID})${NC}"
else
    echo -e "${YELLOW}[!] Blender not found in standard paths. Operating in simulated fallback mode.${NC}"
fi

# ── 5. Start FastAPI Backend API ────────────────────────────
if is_healthy "http://127.0.0.1:8000/api/health"; then
    echo -e "${GREEN}[✔] Reusing FastAPI Backend at http://localhost:8000${NC}"
    register_port_owner 8000
else
    echo -e "${GREEN}[+] Starting BlendPilot FastAPI Backend API on port 8000...${NC}"
    "$VENV_PYTHON" -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    register_stop_target "-$BACKEND_PID"
    if ! wait_for_service "http://127.0.0.1:8000/api/health" "FastAPI Backend"; then
        exit 1
    fi
fi

# ── 6. Start Next.js Frontend ───────────────────────────────
if [ -d "$PROJECT_DIR/ui" ]; then
    if is_healthy "http://127.0.0.1:3000"; then
        echo -e "${GREEN}[✔] Reusing Next.js Frontend at http://localhost:3000${NC}"
        register_port_owner 3000
    else
        echo -e "${GREEN}[+] Starting Next.js Frontend Dev Server on port 3000...${NC}"
        (cd "$PROJECT_DIR/ui" && npm run dev) &
        NEXT_PID=$!
        register_stop_target "-$NEXT_PID"
        if ! wait_for_service "http://127.0.0.1:3000" "Next.js Frontend"; then
            exit 1
        fi
fi
fi

# ── 7. Start MkDocs Documentation ───────────────────────────
if [ -f "$PROJECT_DIR/mkdocs.yml" ]; then
    if is_healthy "http://127.0.0.1:8001"; then
        echo -e "${GREEN}[✔] Reusing MkDocs Documentation at http://localhost:8001${NC}"
        register_port_owner 8001
    else
        echo -e "${GREEN}[+] Starting MkDocs Documentation Server on port 8001...${NC}"
        "$VENV_PYTHON" -m mkdocs serve -a 127.0.0.1:8001 >/dev/null 2>&1 &
        MKDOCS_PID=$!
        register_stop_target "-$MKDOCS_PID"
        if ! wait_for_service "http://127.0.0.1:8001" "MkDocs Documentation"; then
            exit 1
        fi
    fi
fi

echo -e "\n${BOLD}${GREEN}===============================================================${NC}"
echo -e "${BOLD}${GREEN} ✔ All BlendPilot Services are Live and Connected!${NC}"
echo -e "${BOLD}${CYAN}   🌐 Next.js Frontend UI:   ${NC}${BOLD}http://localhost:3000${NC}"
echo -e "${BOLD}${CYAN}   🚀 3D Studio Workspace:  ${NC}${BOLD}http://localhost:3000/studio${NC}"
echo -e "${BOLD}${CYAN}   📡 FastAPI Backend API:   ${NC}${BOLD}http://localhost:8000/docs${NC}"
echo -e "${BOLD}${CYAN}   🔌 Blender Bridge:       ${NC}${BOLD}http://127.0.0.1:9876${NC}"
echo -e "${BOLD}${CYAN}   📚 Documentation:        ${NC}${BOLD}http://localhost:8001${NC}"
echo -e "${BOLD}${GREEN}===============================================================${NC}"
echo -e "${YELLOW}Press [Ctrl+C] anytime to stop all services.${NC}\n"

# Automatically open Next.js UI in the browser
if command -v open >/dev/null 2>&1; then
    open "http://localhost:3000/"
elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "http://localhost:3000/"
fi

# Wait on all background processes
wait
