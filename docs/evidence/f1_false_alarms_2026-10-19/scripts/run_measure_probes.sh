#!/bin/bash
# run_measure_probes.sh <tag> ["k=v;k=v"] : B5 probes with the read-only low-cluster record and optional overrides
source /tmp/claude-0/-home-user-ReSense/314e4672-57bf-5bc8-aad1-a40ec29bc1c0/scratchpad/f1/env.sh
TAG=$1; export F1_SET="$2"; OUT=$SP/probes/$TAG; mkdir -p $OUT; echo "$F1_SET" > $OUT/F1_SET
M=$RESENSE_REPO/docs/evidence/f1_false_alarms_2026-10-19/scripts/measure_probe.py
C=/data/decoded_f1/roundT_squareT_pressureGate_squareT
I=$SP/probes/icp_roundT_squareT_pressureGate_squareT.json
python $M $C $I $OUT/A_lowbox_rail --obj 0.3,0.3,0.15 --start 150 --d0 230 --end 340 > $OUT/A_lowbox_rail.log 2>&1
python $M $C $I $OUT/A_box10_railL --obj 0.3,0.3,0.1 --lat 0.795 --start 150 --d0 230 --end 340 > $OUT/A_box10_railL.log 2>&1
python $M $C $I $OUT/A_box10_railR --obj 0.3,0.3,0.1 --lat -0.795 --start 150 --d0 230 --end 340 > $OUT/A_box10_railR.log 2>&1
echo PROBES_DONE $TAG
