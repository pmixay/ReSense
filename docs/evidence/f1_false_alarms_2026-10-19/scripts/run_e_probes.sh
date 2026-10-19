#!/bin/bash
# run_e_probes.sh <tag> <repo> <tool: range|measure> : the judge's dynamic probes (run_range_extra.sh E1-E6) on background A
REPO=$2; TOOL=$3; TAG=$1
export PATH=/home/user/venv/rs/bin:$PATH RESENSE_REPO=$REPO PYTHONPATH=$REPO:$REPO/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
SP=/tmp/claude-0/-home-user-ReSense/314e4672-57bf-5bc8-aad1-a40ec29bc1c0/scratchpad/f1; export SP F1_SET=""
OUT=$SP/probes/$TAG; mkdir -p $OUT
if [ $TOOL = range ]; then T=$REPO/docs/evidence/judgement_2026-10-13/scripts/range_test.py; else T=/home/user/ReSense-f1/docs/evidence/f1_false_alarms_2026-10-19/scripts/measure_probe.py; fi
C=/data/decoded_f1/roundT_squareT_pressureGate_squareT; I=$SP/probes/icp_roundT_squareT_pressureGate_squareT.json
while read -r n args; do
  python $T $C $I $OUT/$n $args > $OUT/$n.log 2>&1
done <<'LIST'
E1_cross150 --obj 0.5,0.5,1.75 --start 150 --d0 150 --end 340 --lat -4 --vy 1.0
E2_cross80 --obj 0.5,0.5,1.75 --start 220 --d0 80 --end 340 --lat -3 --vy 1.0
E3_recede8 --obj 0.6,0.6,1.0 --start 230 --d0 100 --end 340 --vx 8
E3_recede5 --obj 0.6,0.6,1.0 --start 230 --d0 100 --end 340 --vx 5
E4_appear60 --obj 0.5,0.5,1.75 --start 150 --d0 230 --end 340 --appear 60
E4_appear100 --obj 0.5,0.5,1.75 --start 150 --d0 230 --end 340 --appear 100
E5_pole_side --obj 0.3,0.3,2.8 --start 150 --d0 230 --end 340 --lat 0.7
E5_pole_c --obj 0.3,0.3,2.8 --start 150 --d0 230 --end 340
E6_cable_low_c --obj 0.05,0.05,2.6 --start 150 --d0 230 --end 340 --base 0.2
LIST
echo PROBES_DONE $TAG
