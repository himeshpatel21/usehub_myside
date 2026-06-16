#!/usr/bin/env bash
# Local development setup — installs deps, builds images, starts services, opens the app.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

DEV_DIR="$ROOT/.dev"
BACKEND_PID="$DEV_DIR/backend.pid"
FRONTEND_PID="$DEV_DIR/frontend.pid"
BACKEND_LOG="$DEV_DIR/backend.log"
FRONTEND_LOG="$DEV_DIR/frontend.log"

FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"

info() { printf '\n\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\n\033[1;33mwarning:\033[0m %s\n' "$*" >&2; }
die()  { printf '\n\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }

command_exists() { command -v "$1" >/dev/null 2>&1; }

check_prerequisites() {
  info "Checking prerequisites"

  command_exists docker || die "Docker is required. See https://docs.docker.com/get-docker/"
  docker compose version >/dev/null 2>&1 || die "Docker Compose is required (docker compose plugin)."

  if command_exists python3; then
    PYTHON=python3
  elif command_exists python3.12; then
    PYTHON=python3.12
  else
    die "Python 3.12+ is required."
  fi

  "$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)' \
    || die "Python 3.12+ is required (found $($PYTHON --version 2>&1))."

  command_exists node || die "Node.js is required."
  NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]')"
  if [[ "$NODE_MAJOR" -lt 20 ]]; then
    die "Node.js 20+ is required (found $(node --version))."
  fi

  command_exists npm || die "npm is required."
  command_exists curl || die "curl is required."
}

setup_env() {
  info "Copying environment file"
  if [[ -f backend/.env ]]; then
    warn "backend/.env already exists — skipping copy"
  else
    cp .env.example backend/.env
    echo "Created backend/.env from .env.example"
  fi
}

build_docker_images() {
  info "Building Docker images (backend, frontend)"
  docker compose build backend frontend
}

start_docker_services() {
  info "Starting Postgres, Redis, and MinIO"
  docker compose up -d --wait db redis minio

  info "Initializing MinIO bucket"
  docker compose run --rm minio-init
}

setup_backend() {
  info "Installing backend dependencies"
  (cd backend && "$PYTHON" -m pip install -e ".[dev]")

  info "Running database migrations"
  (cd backend && alembic upgrade head)

  info "Seeding tool catalog"
  (cd backend && "$PYTHON" app/db/seed.py)
}

setup_frontend() {
  info "Installing frontend dependencies"
  (cd frontend && npm install)
}

stop_process() {
  local pid_file="$1"
  local name="$2"
  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(cat "$pid_file")"
    if kill -0 "$pid" 2>/dev/null; then
      warn "Stopping previous $name (pid $pid)"
      kill "$pid" 2>/dev/null || true
      sleep 1
      kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$pid_file"
  fi
}

stop_existing_dev_servers() {
  stop_process "$BACKEND_PID" "backend"
  stop_process "$FRONTEND_PID" "frontend"
}

wait_for_http() {
  local url="$1"
  local label="$2"
  local max_attempts="${3:-90}"
  local attempt=1

  while (( attempt <= max_attempts )); do
    if curl -sf -o /dev/null "$url"; then
      return 0
    fi
    sleep 1
    (( attempt++ )) || true
  done

  die "$label did not become ready at $url (see logs in $DEV_DIR/)"
}

start_dev_servers() {
  mkdir -p "$DEV_DIR"
  stop_existing_dev_servers

  info "Starting backend ($BACKEND_URL)"
  (
    cd "$ROOT/backend"
    nohup uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 \
      >>"$BACKEND_LOG" 2>&1 &
    echo $! >"$BACKEND_PID"
  )

  info "Starting frontend ($FRONTEND_URL)"
  (
    cd "$ROOT/frontend"
    nohup npm run dev -- --hostname 127.0.0.1 --port 3000 \
      >>"$FRONTEND_LOG" 2>&1 &
    echo $! >"$FRONTEND_PID"
  )

  info "Waiting for backend"
  wait_for_http "${BACKEND_URL}/api/v1/health" "Backend"

  info "Waiting for frontend"
  wait_for_http "$FRONTEND_URL" "Frontend"
}

open_browser() {
  local url="${1:-$FRONTEND_URL/login}"
  info "Opening browser at $url"

  if command_exists wslview; then
    wslview "$url" >/dev/null 2>&1 && return 0
  fi
  if command_exists xdg-open; then
    xdg-open "$url" >/dev/null 2>&1 && return 0
  fi
  if command_exists open; then
    open "$url" >/dev/null 2>&1 && return 0
  fi
  if command_exists cmd.exe; then
    cmd.exe /c start "" "$url" >/dev/null 2>&1 && return 0
  fi

  warn "Could not open a browser automatically. Visit: $url"
}

print_summary() {
  cat <<EOF

Setup complete — dev servers are running in the background.

  App:       $FRONTEND_URL
  Login:     $FRONTEND_URL/login  (Development login)
  API:       $BACKEND_URL
  API docs:  $BACKEND_URL/api/docs

  Dev login: username max  |  password mustermann
  (override via DEV_LOGIN_* in backend/.env)

Logs:  $BACKEND_LOG
       $FRONTEND_LOG

Stop servers: kill \$(cat $BACKEND_PID) \$(cat $FRONTEND_PID)
Or re-run ./install.sh (restarts them).

For OAuth later, add Google/GitHub credentials to backend/.env (see README).
EOF
}

main() {
  check_prerequisites
  setup_env
  build_docker_images
  start_docker_services
  setup_backend
  setup_frontend
  start_dev_servers
  open_browser
  print_summary
}

main "$@"
