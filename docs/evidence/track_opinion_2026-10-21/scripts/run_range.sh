#!/bin/bash
# H5 (PROTOCOL §3): the judge's range test, person 0.5x0.5x1.75 and cube 1.0, on A and C, in one tree.
#   run_range.sh <tree> <out dir>     (node-decoded caches in /data/decoded, ICP odometry as below)
T=$1; O=$2; mkdir -p "$O"
. /data/venv/bin/activate
export RESENSE_REPO=$T PYTHONPATH=$T:$T/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
R=$T/docs/evidence/judgement_2026-10-13/scripts/range_test.py
A=/data/decoded/roundT_squareT_pressureGate_squareT; C=/data/decoded/roundT_pressureGate_roundT
IA=$T/docs/evidence/p4_review_r3_h1_2026-10-20/out/aaxis/icp_roundT_squareT_pressureGate_squareT.json
IC=/data/range/icp_roundT_pressureGate_roundT.json
run() { python "$R" "$@" > "$O/$(basename "$3").log" 2>&1; echo "$3 exit $?"; }
run $A $IA $O/A_person --obj 0.5,0.5,1.75 --start 150 --d0 230 --end 340 &
run $A $IA $O/A_cube1 --obj 1.0,1.0,1.0 --start 150 --d0 230 --end 340 &
wait
run $C $IC $O/C_person --obj 0.5,0.5,1.75 --start 0 --d0 230 &
run $C $IC $O/C_cube1 --obj 1.0,1.0,1.0 --start 0 --d0 230 &
wait
