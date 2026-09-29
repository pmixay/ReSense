#!/usr/bin/env bash
# The ReSense web prototype (webapp/, contract webapp/API.md): the FastAPI backend serving the built
# React frontend on one port.
#
#   ./scripts/run_webapp.sh                      # http://localhost:8080/
#   RESENSE_WEB_PORT=9000 ./scripts/run_webapp.sh
#   ./scripts/run_webapp.sh --install            # first run with internet: pip + npm dependencies
#   ./scripts/run_webapp.sh --build --reload     # rebuild the frontend; the rest goes to the server
#
# Installs nothing unless --install is given. Builds webapp/frontend/dist when it is missing or
# older than the sources (or with --build) and npm and node_modules are there; without a build the API still works and "/"
# explains how to build. Options:
#   --install   pip install -e . -e webapp/backend, npm ci in webapp/frontend (needs the internet)
#   --build     rebuild the frontend even if dist exists
#   other arguments are passed to `python -m resense_web` (--host, --reload, --log-level ...)
# Environment:
#   PYTHON             interpreter (default: $VIRTUAL_ENV/bin/python, else python3)
#   RESENSE_WEB_PORT   port (default 8080); RESENSE_WEB_HOST bind address (default 0.0.0.0)
#   RESENSE_DATA       the «Папка на сервере» root (default /data/for_hackathon if it exists, else /data)
#   RESENSE_WEB_DATA   database, uploads, recordings, runs (default webapp/data)
set -euo pipefail
cd "$(dirname "$0")/.."
REPO="$(pwd)"
FRONTEND="$REPO/webapp/frontend"

INSTALL=0
BUILD=0
SERVER_ARGS=()
for arg in "$@"; do
  case "$arg" in
    --install) INSTALL=1 ;;
    --build) BUILD=1 ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) SERVER_ARGS+=("$arg") ;;
  esac
done

if [ -n "${PYTHON:-}" ]; then
  PY="$PYTHON"
elif [ -n "${VIRTUAL_ENV:-}" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
  PY="$VIRTUAL_ENV/bin/python"
else
  PY="python3"
fi
command -v "$PY" >/dev/null 2>&1 || { echo "ERROR: python interpreter '$PY' not found (set PYTHON=...)" >&2; exit 2; }

if [ "$INSTALL" = 1 ]; then
  echo "== pip install -e . -e webapp/backend ($PY)"
  "$PY" -m pip install -e "$REPO" -e "$REPO/webapp/backend"
fi

# resense_web runs from the checkout even when it is not pip-installed (its worker does the same)
export PYTHONPATH="$REPO/webapp/backend${PYTHONPATH:+:$PYTHONPATH}"
if ! "$PY" -c 'import resense, fastapi, uvicorn, rosbags, resense_web' 2>/dev/null; then
  echo "ERROR: $PY lacks the backend dependencies (resense, fastapi, uvicorn, rosbags)." >&2
  echo "       Run once with internet: $0 --install   (or: $PY -m pip install -e . -e webapp/backend)" >&2
  exit 2
fi

# rebuild when asked, when there is no build, or when a source file is newer than the build
STALE=""
if [ -f "$FRONTEND/dist/index.html" ]; then
  STALE="$(find "$FRONTEND/src" "$FRONTEND/index.html" "$FRONTEND/package.json" "$FRONTEND/vite.config.ts" \
             -newer "$FRONTEND/dist/index.html" -print -quit 2>/dev/null || true)"
  [ -n "$STALE" ] && echo "== the frontend build is older than $STALE: rebuilding"
fi
if [ ! -f "$FRONTEND/dist/index.html" ] || [ "$BUILD" = 1 ] || [ -n "$STALE" ]; then
  if ! command -v npm >/dev/null 2>&1; then
    echo "WARNING: npm not found: serving the API only (\"/\" explains how to build the frontend)" >&2
  else
    if [ "$INSTALL" = 1 ]; then
      echo "== npm ci (webapp/frontend)"
      (cd "$FRONTEND" && npm ci)
    fi
    if [ -d "$FRONTEND/node_modules" ]; then
      echo "== npm run build (webapp/frontend)"
      (cd "$FRONTEND" && npm run build)
    else
      echo "WARNING: webapp/frontend/node_modules is missing: run with --install (needs the internet)" >&2
      echo "         or 'npm ci' in webapp/frontend; serving the API only for now" >&2
    fi
  fi
fi

if [ -z "${RESENSE_DATA:-}" ]; then
  if [ -d /data/for_hackathon ]; then RESENSE_DATA=/data/for_hackathon; else RESENSE_DATA=/data; fi
fi
export RESENSE_DATA
PORT="${RESENSE_WEB_PORT:-8080}"

echo "== ReSense web: http://localhost:$PORT/"
LAN_IP="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
[ -n "$LAN_IP" ] && echo "   in the local network: http://$LAN_IP:$PORT/"
echo "   server folder: $RESENSE_DATA$([ -d "$RESENSE_DATA" ] || echo ' (missing)')  ·  data: ${RESENSE_WEB_DATA:-$REPO/webapp/data}"
echo "   stop: Ctrl+C"
exec "$PY" -m resense_web --port "$PORT" ${SERVER_ARGS[@]+"${SERVER_ARGS[@]}"}
