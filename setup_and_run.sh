#!/usr/bin/env bash
# Setup and run the Adaptive IT Learning Path Guide (backend + frontend) on Linux/macOS.
# Mirrors setup_and_run.ps1 for Windows.
set -euo pipefail

BACKEND_PORT=8000
FRONTEND_PORT=4200
AUTO_INSTALL=0

usage() {
  cat <<EOF
Usage: $0 [--backend-port PORT] [--frontend-port PORT] [--auto-install]

  --backend-port PORT   Port for the FastAPI backend (default: 8000)
  --frontend-port PORT  Port for the Angular dev server (default: 4200)
  --auto-install        Attempt to install missing Python3/Node.js via the
                         system package manager (apt, dnf, or brew). Requires
                         sudo on Linux. Off by default.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --backend-port) BACKEND_PORT="$2"; shift 2 ;;
    --frontend-port) FRONTEND_PORT="$2"; shift 2 ;;
    --auto-install) AUTO_INSTALL=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 1 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
VENV_DIR="$BACKEND_DIR/venv"
PYTHON_BIN="$VENV_DIR/bin/python"

log() { echo "[setup] $*"; }

have_cmd() { command -v "$1" >/dev/null 2>&1; }

detect_pkg_manager() {
  if have_cmd apt-get; then echo "apt"; return; fi
  if have_cmd dnf; then echo "dnf"; return; fi
  if have_cmd brew; then echo "brew"; return; fi
  echo ""
}

ensure_python() {
  if have_cmd python3; then return; fi
  if [[ "$AUTO_INSTALL" -ne 1 ]]; then
    echo "python3 is not installed. Install it (e.g. 'sudo apt-get install -y python3 python3-venv python3-pip')" \
         " or re-run with --auto-install." >&2
    exit 1
  fi
  local pm; pm="$(detect_pkg_manager)"
  case "$pm" in
    apt) sudo apt-get update && sudo apt-get install -y python3 python3-venv python3-pip ;;
    dnf) sudo dnf install -y python3 python3-pip ;;
    brew) brew install python3 ;;
    *) echo "No supported package manager found (apt/dnf/brew). Install Python 3 manually." >&2; exit 1 ;;
  esac
  if ! have_cmd python3; then
    echo "Python installation attempted but python3 is still not on PATH." >&2
    exit 1
  fi
}

# Angular 22 requires one of these Node ranges; older Node (including 18/20) cannot run it.
node_version_ok() {
  local ver="$1"
  python3 - "$ver" <<'EOF'
import sys
try:
    major, minor, patch = (int(x) for x in sys.argv[1].split('.')[:3])
except ValueError:
    sys.exit(1)
ok = (
    (major == 22 and (minor, patch) >= (22, 3))
    or (major == 24 and minor >= 15)
    or (major >= 26)
)
sys.exit(0 if ok else 1)
EOF
}

print_node_upgrade_help() {
  cat >&2 <<'EOF'
Required Node.js version: ^22.22.3, ^24.15.0, or >=26.0.0 (Angular 22's minimum).
Most Linux package managers (including apt on Ubuntu/Debian) ship an older Node.js
that does NOT satisfy this, so --auto-install will not fix this by itself.

Recommended: install/switch via nvm (https://github.com/nvm-sh/nvm):
  nvm install 22.23.2
  nvm use 22.23.2

Or download a binary directly from https://nodejs.org/.
EOF
}

ensure_node() {
  if have_cmd node && have_cmd npm; then
    local current_ver
    current_ver="$(node --version | sed 's/^v//')"
    if node_version_ok "$current_ver"; then
      return
    fi
    echo "Found Node.js v$current_ver, but this project requires a newer version." >&2
    print_node_upgrade_help
    exit 1
  fi

  if [[ "$AUTO_INSTALL" -ne 1 ]]; then
    echo "node/npm is not installed." >&2
    print_node_upgrade_help
    exit 1
  fi

  local pm; pm="$(detect_pkg_manager)"
  case "$pm" in
    apt) sudo apt-get update && sudo apt-get install -y nodejs npm ;;
    dnf) sudo dnf install -y nodejs npm ;;
    brew) brew install node ;;
    *) echo "No supported package manager found (apt/dnf/brew). Install Node.js manually." >&2; exit 1 ;;
  esac
  if ! (have_cmd node && have_cmd npm); then
    echo "Node.js installation attempted but node/npm is still not on PATH." >&2
    exit 1
  fi
  local installed_ver
  installed_ver="$(node --version | sed 's/^v//')"
  if ! node_version_ok "$installed_ver"; then
    echo "Your package manager installed Node.js v$installed_ver, which is too old." >&2
    print_node_upgrade_help
    exit 1
  fi
}

ensure_backend_env() {
  local env_path="$BACKEND_DIR/.env"
  if [[ -f "$env_path" ]]; then return; fi
  log "Creating backend/.env with a generated JWT secret (fill in GOOGLE_API_KEY manually)..."
  local secret
  secret="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
  {
    echo "GOOGLE_API_KEY="
    echo "JWT_SECRET_KEY=$secret"
  } > "$env_path"
}

[[ -d "$BACKEND_DIR" ]] || { echo "backend folder not found: $BACKEND_DIR" >&2; exit 1; }
[[ -d "$FRONTEND_DIR" ]] || { echo "frontend folder not found: $FRONTEND_DIR" >&2; exit 1; }

ensure_python
ensure_node

log "Setting up Python environment..."
if [[ ! -x "$PYTHON_BIN" ]]; then
  python3 -m venv "$VENV_DIR"
fi

"$PYTHON_BIN" -m pip install --upgrade pip
"$PYTHON_BIN" -m pip install -r "$BACKEND_DIR/requirements.txt"

log "Setting up frontend dependencies..."
(
  cd "$FRONTEND_DIR"
  if [[ -f package-lock.json ]]; then
    npm ci
  else
    npm install
  fi
)

ensure_backend_env
if ! grep -q "^GOOGLE_API_KEY=.\+" "$BACKEND_DIR/.env"; then
  log "Warning: GOOGLE_API_KEY is empty in backend/.env. The AI tutor chat will not work until you set it."
fi

LOG_DIR="$SCRIPT_DIR/.run"
mkdir -p "$LOG_DIR"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"

log "Starting backend on port $BACKEND_PORT (log: $BACKEND_LOG)..."
(
  cd "$BACKEND_DIR"
  "$PYTHON_BIN" -m uvicorn app.main:app --reload --host 0.0.0.0 --port "$BACKEND_PORT"
) > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

log "Starting frontend on port $FRONTEND_PORT (log: $FRONTEND_LOG)..."
(
  cd "$FRONTEND_DIR"
  npm start -- --port "$FRONTEND_PORT"
) > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!

cleanup() {
  log "Stopping backend (pid $BACKEND_PID) and frontend (pid $FRONTEND_PID)..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

log "Backend:  http://localhost:$BACKEND_PORT/docs"
log "Frontend: http://localhost:$FRONTEND_PORT"
log "Press Ctrl+C to stop both servers."

wait "$BACKEND_PID" "$FRONTEND_PID"
