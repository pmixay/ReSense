#!/usr/bin/env bash
# Offline run without ROS (reads the bag with the pure-python `rosbags` reader).
#   ./scripts/run_offline.sh /path/to/for_hackathon/roundT_doubleT results.jsonl [render_dir]
set -euo pipefail
BAG="$1"; OUT="${2:-results.jsonl}"; RENDER="${3:-}"
if [ -n "$RENDER" ]; then
  resense run --bag "$BAG" --out "$OUT" --render "$RENDER"
else
  resense run --bag "$BAG" --out "$OUT"
fi
