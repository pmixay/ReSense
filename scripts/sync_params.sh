#!/usr/bin/env bash
# Keep the ROS parameter file in sync with the canonical configs/default.yaml.
#   ./scripts/sync_params.sh          # copy configs/default.yaml -> ros2_ws/.../config/detector.yaml
#   ./scripts/sync_params.sh --check  # exit 1 if the two differ (used by CI)
set -euo pipefail
cd "$(dirname "$0")/.."
SRC=configs/default.yaml
DST=ros2_ws/src/resense_ros/config/detector.yaml
if [ "${1:-}" = "--check" ]; then
  if diff -q "$SRC" "$DST" >/dev/null; then
    echo "parameter files in sync"
  else
    echo "ERROR: $DST differs from $SRC — run ./scripts/sync_params.sh and commit" >&2
    diff -u "$SRC" "$DST" >&2 || true
    exit 1
  fi
else
  cp "$SRC" "$DST"
  echo "copied $SRC -> $DST"
fi
