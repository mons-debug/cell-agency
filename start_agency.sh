#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
#  Cell Agency — Master Startup Script
#  Starts all 4 MCP servers + OpenClaw gateway
#
#  Usage:
#    ./start_agency.sh           — start everything
#    ./start_agency.sh --check   — health check only, no start
#    ./start_agency.sh --stop    — graceful shutdown of all servers
#    ./start_agency.sh --restart — stop + start all servers
#    ./start_agency.sh --status  — show server PIDs and status
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail

AGENCY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="$AGENCY_DIR/memory/pids"
LOG_DIR="$AGENCY_DIR/memory/logs"
ENV_FILE="$AGENCY_DIR/.env"

# ── Colours ────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; RESET='\033[0m'
ok()   { echo -e "${GREEN}✅${RESET} $*"; }
warn() { echo -e "${YELLOW}⚠️ ${RESET} $*"; }
err()  { echo -e "${RED}❌${RESET} $*"; }
info() { echo -e "${BLUE}ℹ️ ${RESET} $*"; }

echo -e "\n${BOLD}Cell Agency — Startup${RESET}"
echo "═══════════════════════════════════════"
echo "Dir: $AGENCY_DIR"
echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# ── Parse args ─────────────────────────────────────────────────────
ACTION="${1:-start}"

# ── Load env vars ──────────────────────────────────────────────────
load_env() {
    if [ -f "$ENV_FILE" ]; then
        set -a
        # shellcheck source=/dev/null
        source "$ENV_FILE"
        set +a
        ok "Environment loaded from .env"
    else
        err ".env file not found at $ENV_FILE"
        echo "   Copy .env.example to .env and fill in your values"
        exit 1
    fi
}

# ── Check required env vars ────────────────────────────────────────
check_env() {
    local required=("ANTHROPIC_API_KEY" "TELEGRAM_BOT_TOKEN" "TELEGRAM_OWNER_ID")
    local optional_warn=("GEMINI_API_KEY" "SERPER_API_KEY" "INSTAGRAM_ACCESS_TOKEN"
                         "META_ACCESS_TOKEN" "META_AD_ACCOUNT_ID")
    local missing=()

    echo -e "${BOLD}Checking environment variables...${RESET}"
    for var in "${required[@]}"; do
        if [ -z "${!var:-}" ]; then
            missing+=("$var")
            err "  MISSING (required): $var"
        else
            ok "  $var"
        fi
    done

    for var in "${optional_warn[@]}"; do
        if [ -z "${!var:-}" ]; then
            warn "  $var (optional — some features disabled)"
        fi
    done

    if [ ${#missing[@]} -gt 0 ]; then
        echo ""
        err "${#missing[@]} required env var(s) missing — cannot start"
        exit 1
    fi
    echo ""
}

# ── Python detection ───────────────────────────────────────────────
find_python() {
    # Try uv run first, then pyenv, then system python
    if command -v uv &>/dev/null; then
        echo "uv run python"
        return
    fi
    if [ -f "$HOME/.pyenv/shims/python3" ]; then
        echo "$HOME/.pyenv/shims/python3"
        return
    fi
    echo "python3"
}

PYTHON=$(find_python)
info "Python: $PYTHON"

# ── MCP server management ──────────────────────────────────────────
MCP_SERVERS=("agency" "social" "ads" "design")
MCP_SCRIPTS=(
    "mcp-servers/agency_server.py"
    "mcp-servers/social_server.py"
    "mcp-servers/ads_server.py"
    "mcp-servers/design_server.py"
)

mkdir -p "$PID_DIR" "$LOG_DIR"

is_running() {
    local server="$1"
    local pid_file="$PID_DIR/${server}.pid"
    if [ -f "$pid_file" ]; then
        local pid
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            return 0  # running
        fi
    fi
    return 1  # not running
}

start_server() {
    local server="$1"
    local script="$2"
    local script_path="$AGENCY_DIR/$script"
    local pid_file="$PID_DIR/${server}.pid"
    local log_file="$LOG_DIR/${server}.log"

    if is_running "$server"; then
        local pid
        pid=$(cat "$pid_file")
        ok "  $server already running (pid $pid)"
        return
    fi

    if [ ! -f "$script_path" ]; then
        err "  $server script not found: $script_path"
        return
    fi

    # Append startup marker to log
    {
        echo ""
        echo "════════════════════════════════════════"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting $server"
        echo "════════════════════════════════════════"
    } >> "$log_file"

    # Start in background, detached from this session
    nohup $PYTHON "$script_path" >> "$log_file" 2>&1 &
    local pid=$!
    echo "$pid" > "$pid_file"

    # Brief wait then check it didn't immediately crash
    sleep 0.5
    if kill -0 "$pid" 2>/dev/null; then
        ok "  $server started (pid $pid) → $log_file"
    else
        err "  $server crashed immediately — check $log_file"
        rm -f "$pid_file"
    fi
}

stop_server() {
    local server="$1"
    local pid_file="$PID_DIR/${server}.pid"

    if ! is_running "$server"; then
        info "  $server not running"
        rm -f "$pid_file"
        return
    fi

    local pid
    pid=$(cat "$pid_file")
    kill -TERM "$pid" 2>/dev/null || true
    sleep 0.3
    # Force kill if still alive
    if kill -0 "$pid" 2>/dev/null; then
        kill -KILL "$pid" 2>/dev/null || true
    fi
    rm -f "$pid_file"
    ok "  $server stopped (pid $pid)"
}

show_status() {
    echo -e "${BOLD}MCP Server Status${RESET}"
    echo "─────────────────────────────────────"
    for i in "${!MCP_SERVERS[@]}"; do
        local server="${MCP_SERVERS[$i]}"
        local pid_file="$PID_DIR/${server}.pid"
        if is_running "$server"; then
            local pid
            pid=$(cat "$pid_file")
            ok "  $server (pid $pid)"
        elif [ -f "$pid_file" ]; then
            err "  $server — CRASHED (stale pid file)"
        else
            warn "  $server — not running"
        fi
    done
    echo ""
}

# ── Actions ────────────────────────────────────────────────────────

case "$ACTION" in
    --check)
        load_env
        check_env
        echo -e "${BOLD}Running health check...${RESET}"
        $PYTHON -c "
import sys; sys.path.insert(0, '.')
from infra.health_check import load_health_checker
hc = load_health_checker()
r  = hc.full_check()
print(r.to_markdown())
"
        ;;

    --stop)
        echo -e "${BOLD}Stopping all MCP servers...${RESET}"
        for server in "${MCP_SERVERS[@]}"; do
            stop_server "$server"
        done
        ok "All servers stopped"
        ;;

    --restart)
        echo -e "${BOLD}Restarting all MCP servers...${RESET}"
        for server in "${MCP_SERVERS[@]}"; do
            stop_server "$server"
        done
        sleep 1
        load_env
        for i in "${!MCP_SERVERS[@]}"; do
            start_server "${MCP_SERVERS[$i]}" "${MCP_SCRIPTS[$i]}"
        done
        echo ""
        show_status
        ;;

    --status)
        load_env
        show_status
        ;;

    start|"")
        load_env
        check_env

        echo -e "${BOLD}Starting MCP servers...${RESET}"
        for i in "${!MCP_SERVERS[@]}"; do
            start_server "${MCP_SERVERS[$i]}" "${MCP_SCRIPTS[$i]}"
        done
        echo ""
        show_status

        echo -e "${BOLD}Starting OpenClaw gateway...${RESET}"
        # Add pyenv to PATH if available
        if [ -d "$HOME/.pyenv" ]; then
            export PYENV_ROOT="$HOME/.pyenv"
            export PATH="$PYENV_ROOT/bin:$PYENV_ROOT/shims:$PATH"
        fi

        if command -v openclaw &>/dev/null; then
            ok "OpenClaw found — starting gateway"
            echo ""
            echo -e "${BOLD}Cell Agency is running 🚀${RESET}"
            echo "═══════════════════════════════════════"
            echo "Telegram bot: active"
            echo "MCP servers:  4 running"
            echo "Logs:         memory/logs/"
            echo "PIDs:         memory/pids/"
            echo ""
            echo "Use Ctrl+C to stop the gateway (MCP servers keep running)"
            echo "Use ./start_agency.sh --stop to stop MCP servers"
            echo ""
            exec openclaw gateway run
        else
            warn "openclaw not found in PATH — MCP servers started but gateway not launched"
            echo ""
            info "To start the gateway manually, run:"
            echo "     openclaw gateway run"
            echo ""
            echo -e "${BOLD}Cell Agency MCP servers are running 🚀${RESET}"
        fi
        ;;

    *)
        echo "Usage: $0 [--check|--stop|--restart|--status]"
        exit 1
        ;;
esac
