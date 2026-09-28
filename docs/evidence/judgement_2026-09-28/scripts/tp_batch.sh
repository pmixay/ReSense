#!/usr/bin/env bash
# transplant.py for one target bag and several windows: tp_batch.sh <bag> <start> [<start> ...]
cd "$(dirname "$0")"
bag=$1; shift
mkdir -p transplant
for s in "$@"; do
  python3 transplant.py "$bag" "$s" 60,80,100,130,160,200 > "transplant/${bag}_$s.json" 2> "transplant/${bag}_$s.log"
done
