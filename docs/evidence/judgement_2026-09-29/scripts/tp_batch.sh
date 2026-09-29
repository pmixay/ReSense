#!/usr/bin/env bash
# transplant.py for one target bag and several windows: tp_batch.sh <bag> <start> [<start> ...]
cd "$(dirname "$0")"
bag=$1; shift
# 29.09: TPOUT = output directory (default transplant/ next to the script, as 28.09)
out=${TPOUT:-transplant}
mkdir -p "$out"
for s in "$@"; do
  python3 transplant.py "$bag" "$s" 60,80,100,130,160,200 > "$out/${bag}_$s.json" 2> "$out/${bag}_$s.log"
done
