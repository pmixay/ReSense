#!/usr/bin/env bash
# Persistent web runtime. Environment is supplied by resense-web.service.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
STATE="${RESENSE_DEPLOY_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}/resense}"
export PYTHONPATH="$REPO:$REPO/webapp/backend:$REPO/ros2_ws/src/resense_ros${PYTHONPATH:+:$PYTHONPATH}"
cd "$REPO"
exec "$STATE/venv/bin/python" -m resense_web
