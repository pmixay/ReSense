#!/usr/bin/env bash
# Shared fail-fast check for acceptance scripts that need a running Docker daemon.

require_docker_daemon() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: Docker CLI is not installed; ROS/Docker acceptance cannot run." >&2
    return 3
  fi
  local diagnostic
  if ! diagnostic="$(docker info --format '{{.ServerVersion}}' 2>&1)"; then
    echo "ERROR: Docker daemon is unavailable; ROS/Docker acceptance was not run." >&2
    echo "       Start Docker Desktop/Engine and retry. No FPS or latency was measured." >&2
    echo "       Docker diagnostic:" >&2
    echo "$diagnostic" >&2
    return 3
  fi
}
