#!/bin/bash
# Switch-off runs of the shipped source (cc6226e = 5fa865b detector), overrides only:
#   R3 off: tracking.cable_confirm_time_s=0     H1 off: cluster.column_core_margin=0
# phase 1: gate R3 off || gate H1 off;  phase 2: X3 R3 off || X3 H1 off;
# phase 3 (reproduction controls): gate default || X3 default.
set -u
W=/home/user/wt_ship; D=/home/user/data; O=/home/user/p4r/runs; L=$O/logs; mkdir -p $O $L
export PATH=/home/user/venv/rs/bin:$PATH OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 RESENSE_REPO=$W PYTHONPATH=$W
BASE=$W/docs/evidence/results/regression_baseline_2026-09-29_shell_off.json
R3="tracking.cable_confirm_time_s=0"; H1="cluster.column_core_margin=0"
gate() { # tag [--set x]
  local tag=$1; shift
  ( cd $W && python scripts/regression_gate.py --cache $D/cache --jobs 2 --work $O/gate_$tag \
      --baseline $BASE --out $O/gate_$tag.json "$@" ) > $L/gate_$tag.log 2>&1
  echo "gate $tag exit $? $(date -u +%T)"
}
x3() { # tag override
  local tag=$1 ov=$2
  ( cd $W && P4_X3_SET="$ov" python scripts/robustness_battery.py --repo $W --cache $D/decoded \
      --out $O/x3_$tag.json -j 2 --reference /home/user/out/x3/x3_l16.json \
      --resource-adapter /home/user/p4r/scripts/x3_override ) > $L/x3_$tag.log 2>&1
  echo "x3 $tag exit $? $(date -u +%T)"
}
date -u +"start %T"
gate r3off --set $R3 & gate h1off --set $H1 & wait
x3 r3off "$R3" & x3 h1off "$H1" & wait
gate default & x3 default "" & wait
echo RUNS_DONE $(date -u +%T)
