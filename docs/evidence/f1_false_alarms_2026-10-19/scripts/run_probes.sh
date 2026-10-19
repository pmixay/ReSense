#!/bin/bash
# run_probes.sh <tag> [extra --set ignored]: the B5 probes through the judge's range_test.py with RESENSE_REPO's detector
source /tmp/claude-0/-home-user-ReSense/314e4672-57bf-5bc8-aad1-a40ec29bc1c0/scratchpad/f1/env.sh
TAG=$1; OUT=$SP/probes/$TAG; mkdir -p $OUT
J=$RESENSE_REPO/docs/evidence/judgement_2026-10-13/scripts
C=/data/decoded_f1/roundT_squareT_pressureGate_squareT
I=$SP/probes/icp_roundT_squareT_pressureGate_squareT.json
python $J/range_test.py $C $I $OUT/A_lowbox_rail --obj 0.3,0.3,0.15 --start 150 --d0 230 --end 340 > $OUT/A_lowbox_rail.log 2>&1
python $J/range_test.py $C $I $OUT/A_box10_railL --obj 0.3,0.3,0.1 --lat 0.795 --start 150 --d0 230 --end 340 > $OUT/A_box10_railL.log 2>&1 &
python $J/range_test.py $C $I $OUT/A_box10_railR --obj 0.3,0.3,0.1 --lat -0.795 --start 150 --d0 230 --end 340 > $OUT/A_box10_railR.log 2>&1
wait
echo PROBES_DONE $TAG
