#!/bin/bash
# the 6-start table from the far-range review's own scorers (evalrows.py: first / held STOP, episodes, false episodes;
# person_frames.py: GO with the person inside the reported clear and monitored range), v1.2.0 (base) vs final (fin)
R=/home/user/ReSense/docs/evidence/falcon_far_range_review_2026-10-21/scripts; D=${1:-/data/acc/starts}; T=$(mktemp -d)
printf "%-6s | %-40s | %-40s\n" start "v1.2.0 first / held m, eps (false), GO-in" "final first / held m, eps (false), GO-in"
for s in 0 600 1200 1800 2100 2400; do
  for w in base fin; do
    python $R/evalrows.py $D/s${s}__$w.jsonl --json $T/e_$w.json > /dev/null
    python $R/person_frames.py $D/s${s}__$w.jsonl $D/s${s}__$w.jsonl --names a,b --json $T/p_$w.json > /dev/null
  done
  python3 - $T $s <<'PY'
import json, sys
T, s = sys.argv[1], sys.argv[2]
out = []
for w in ("base", "fin"):
    e = json.load(open(f"{T}/e_{w}.json")); p = json.load(open(f"{T}/p_{w}.json"))["a"]; m = e["targets"]["main_approach"]
    out.append(f"{m['first_stop_x']} / {m['held_stop_x']}, {e['stop_episodes']} ({e['false_episodes']}), {p['go_with_person_inside_clear_and_monitored']}")
print(f"{s:6s} | {out[0]:40s} | {out[1]:40s}")
PY
done
rm -rf $T
