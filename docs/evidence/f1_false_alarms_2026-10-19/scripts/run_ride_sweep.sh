#!/bin/bash
# run_ride_sweep.sh <tag>:<set;set> ... : one-detector ride replays, sequentially
source /tmp/claude-0/-home-user-ReSense/314e4672-57bf-5bc8-aad1-a40ec29bc1c0/scratchpad/f1/env.sh
R=$RESENSE_REPO/docs/evidence/f1_false_alarms_2026-10-19/scripts/replay.py
for spec in "$@"; do
  tag=${spec%%:*}; sets=${spec#*:}; args=()
  IFS=';' read -ra kv <<< "$sets"; for s in "${kv[@]}"; do [ -n "$s" ] && args+=(--set "$s"); done
  [ -s $SP/ride/$tag.meta.json ] && continue
  python $R --bag new_data --out $SP/ride/$tag --lowref "${args[@]}" > $SP/ride/$tag.log 2>&1
  echo "DONE $tag"
done
