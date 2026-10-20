#!/bin/bash
# H1 author claim A-axis (82 -> 114/177): the judge's range_test.py, the author's arguments
# (--obj 0.3,0.3,2.8 --start 150 --d0 230 --end 340 on roundT_squareT_pressureGate_squareT), ICP from the judge's
# icp_odometry.py (open3d 0.19.0). Default config first (writes the baseline track file), then H1 off through the
# X3 override adapter (same baseline, so the same placement).
set -u
W=/home/user/wt_ship; O=/home/user/p4r/aaxis; C=/home/user/data/decoded/roundT_squareT_pressureGate_squareT
export PATH=/home/user/venv/rs/bin:$PATH OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 RESENSE_REPO=$W
RT=$W/docs/evidence/judgement_2026-10-13/scripts/range_test.py
A="--obj 0.3,0.3,2.8 --start 150 --d0 230 --end 340"
PYTHONPATH=$W python $RT $C $O/icp_roundT_squareT_pressureGate_squareT.json $O/A-axis-default $A > $O/default.log 2>&1; echo "default exit $?"
P4_X3_SET="cluster.column_core_margin=0" PYTHONPATH=$W:/home/user/p4r/scripts/x3_override python $RT $C $O/icp_roundT_squareT_pressureGate_squareT.json $O/A-axis-h1off $A > $O/h1off.log 2>&1; echo "h1off exit $?"
echo AAXIS_DONE
