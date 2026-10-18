#!/usr/bin/env bash
# RViz + interactive player; supports several bags and explicit sensor profiles.
# scripts/run_demo.sh BAG [rate] or scripts/run_demo.sh --sensor-profile pandar128 BAG1 --sensor-profile falcon_ros BAG2
# LIBGL_ALWAYS_SOFTWARE=1 scripts/run_demo.sh BAG 0.5  # software OpenGL
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ARGS=()
if [ "${RVIZ:-1}" != 0 ]; then ARGS+=(--rviz); fi
if [ "${LIBGL_ALWAYS_SOFTWARE:-0}" = 1 ]; then ARGS+=(--software-rendering); fi
if [ -t 0 ] && [ -t 1 ]; then ARGS+=(--interactive); fi
if [ "$#" = 2 ] && [[ "$2" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
  exec "$HERE/play_bag.sh" "${ARGS[@]}" --rate "$2" "$1"
fi
exec "$HERE/play_bag.sh" "${ARGS[@]}" "$@"
