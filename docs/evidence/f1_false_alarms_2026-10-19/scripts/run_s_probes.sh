#!/bin/bash
# run_s_probes.sh <tag> ["k=v;k=v"] : the judge's standing-train probes (run_range_matrix.sh S_*) with optional overrides
source /tmp/claude-0/-home-user-ReSense/314e4672-57bf-5bc8-aad1-a40ec29bc1c0/scratchpad/f1/env.sh
TAG=$1; export F1_SET="$2"; OUT=$SP/probes/$TAG; mkdir -p $OUT; echo "$F1_SET" > $OUT/F1_SET
M=$RESENSE_REPO/docs/evidence/f1_false_alarms_2026-10-19/scripts/measure_probe.py
C=/data/decoded_f1/squareT_platform_squareT_switch
I=$SP/probes/icp_squareT_platform_squareT_switch.json
for d in 60 100 150; do
  python $M $C $I $OUT/S_person_$d --obj 0.5,0.5,1.75 --start 360 --d0 $d --end 620 > $OUT/S_person_$d.log 2>&1
  python $M $C $I $OUT/S_cube05_$d --obj 0.5,0.5,0.5 --start 360 --d0 $d --end 620 > $OUT/S_cube05_$d.log 2>&1
done
echo PROBES_DONE $TAG
