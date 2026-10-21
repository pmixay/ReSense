#!/bin/bash
# Regenerate out/*.txt from the committed raw outputs under runs/ (run from the repository root, venv active,
# RESENSE_REPO / PYTHONPATH = this checkout). Trees: ctl = v1.2.0 3b73bbe, k2 = 944acc7 (K2 on), preg2 = 79f132b
# (K2 + clear distance), comb = fae6dbc (all phase-1 lanes).
set -u
E=docs/evidence/integration_1.3_2026-10-21; S=$E/scripts; R=$E/runs; O=$E/out; T=$(mktemp -d); mkdir -p $O
for f in $R/falcon/*.jsonl.xz $R/markers/*.jsonl.xz $R/setO/*.jsonl.xz; do xz -dc $f > $T/$(basename $f .xz); done
{
  echo "## control (v1.2.0) manual record vs P4's committed l16 record (every shared field)"
  python $S/rows_diff.py docs/evidence/l16_acceptance_2026-10-20/out/falcon/l16.jsonl.xz $T/ctl_manual.jsonl --skip mount_rotation --skip track_detail | tail -2
  echo "## K2 review scorer, manual path, control vs combined"
  python docs/evidence/k1_k2_review_2026-10-21/scripts/score_falcon.py $T/ctl_manual.jsonl $T/comb_manual.jsonl
  for p in manual ros; do
    echo "## STOP frames, $p, control vs combined"; python $S/stop_diff.py $T/ctl_$p.jsonl $T/comb_$p.jsonl
    for pr in "ctl k2" "k2 preg2" "preg2 comb" "ctl comb"; do set -- $pr
      echo "## rows, $p, $1 vs $2 (clear skipped, reported as lowered / raised)"; python $S/rows_diff.py $T/$1_$p.jsonl $T/$2_$p.jsonl --skip clear | tail -2; done
  done
  echo "## positive control of rows_diff (one planted change)"; python $S/rows_diff.py $T/preg2_ros.jsonl $T/comb_ros.jsonl --inject | tail -1
} > $O/falcon.txt 2>&1
python - $T > $O/falcon_clear.txt <<'PY'
import json, sys
T = sys.argv[1]
for p in ("manual", "ros"):
    for a_, b_ in (("ctl", "comb"), ("k2", "preg2")):
        A = [json.loads(l) for l in open(f"{T}/{a_}_{p}.jsonl")]; B = [json.loads(l) for l in open(f"{T}/{b_}_{p}.jsonl")]
        z = [b["i"] for a, b in zip(A, B) if b["clear"] == 0 and a["clear"] != 0]
        over = lambda R: sum(1 for r in R if r["decision"] == "STOP" and r["dets"] and r["clear"] > min(d["d"] for d in r["dets"]) + 1e-9)
        print(f"{p} {a_}->{b_}: clear -> 0 on {len(z)} rows {z[0]}-{z[-1]} contiguous {z == list(range(z[0], z[-1] + 1))}, "
              f"decisions {dict((d, sum(B[i]['decision'] == d for i in z)) for d in ('GO', 'CAUTION', 'STOP'))}; "
              f"lowered {sum(b['clear'] < a['clear'] for a, b in zip(A, B))} raised {sum(b['clear'] > a['clear'] for a, b in zip(A, B))}; "
              f"STOP rows with clear beyond the nearest STOP detection {over(A)} -> {over(B)}; 4411-4414 {[(b['i'], b['clear'], b['decision']) for b in B[4411:4415]]}")
PY
{
  for b in tunnels platform switch; do
    xz -dc docs/evidence/synth_markers_2026-10-19/out/markers_$b.jsonl.xz > $T/mk_$b.jsonl
    echo "## $b: per marked object, control (A) vs combined (B)"; python -I docs/evidence/n5_markers_2026-10-20/scripts/per_object.py $T/mk_$b.jsonl $T/ctl_$b.jsonl $T/comb_$b.jsonl
    python $S/stop_diff.py $T/ctl_$b.jsonl $T/comb_$b.jsonl | head -3
    for pr in "ctl k2" "k2 preg2" "preg2 comb" "ctl comb"; do set -- $pr
      echo "## rows $b $1 vs $2"; python $S/rows_diff.py $T/$1_$b.jsonl $T/$2_$b.jsonl --skip clear | tail -2; done
  done
  echo "## positive control"; python $S/rows_diff.py $T/preg2_tunnels.jsonl $T/comb_tunnels.jsonl --inject | tail -1
} > $O/markers.txt 2>&1
{
  python $S/clear_past_object.py labels/cloud_with_fake_obj.json $T/ctl_cloud_with_fake_obj.jsonl $T/comb_cloud_with_fake_obj.jsonl
  python $S/stop_diff.py $T/ctl_cloud_with_fake_obj.jsonl $T/comb_cloud_with_fake_obj.jsonl | head -3
  python $S/rows_diff.py $T/ctl_cloud_with_fake_obj.jsonl $T/comb_cloud_with_fake_obj.jsonl --skip clear_distance --skip candidate_distance | tail -2
} > $O/setO.txt 2>&1
rm -rf $T; echo outputs written
