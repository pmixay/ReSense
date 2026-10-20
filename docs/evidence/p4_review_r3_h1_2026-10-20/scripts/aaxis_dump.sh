#!/bin/bash
# The A-axis probe under the read-only hooks, dumping the processed cloud at k = 300, 310, 322 for H1 on (default)
# and H1 off (override through the X3 adapter), for the pictures.
W=/home/user/wt_ship; O=/home/user/p4r/aaxis
export OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 RESENSE_REPO=$W
RT=$W/docs/evidence/judgement_2026-10-13/scripts/range_test.py
C=/home/user/data/decoded/roundT_squareT_pressureGate_squareT
A="--obj 0.3,0.3,2.8 --start 150 --d0 230 --end 323"
mkdir -p $O/dump_on $O/dump_off
cd $W
P4_DUMP=300,310,322 P4_DUMP_DIR=$O/dump_on PYTHONPATH=$W /home/user/venv/rs/bin/python /home/user/p4r/scripts/hooks_runpy.py \
  $O/hooks_on_dump.ndjson $RT $C $O/icp_roundT_squareT_pressureGate_squareT.json $O/A-axis-on-dump $A > $O/dump_on.log 2>&1; echo "on exit $?"
P4_X3_SET="cluster.column_core_margin=0" P4_DUMP=300,310,322 P4_DUMP_DIR=$O/dump_off PYTHONPATH=$W:/home/user/p4r/scripts/x3_override \
  /home/user/venv/rs/bin/python /home/user/p4r/scripts/hooks_runpy.py $O/hooks_off_dump.ndjson $RT $C \
  $O/icp_roundT_squareT_pressureGate_squareT.json $O/A-axis-off-dump $A > $O/dump_off.log 2>&1; echo "off exit $?"
echo DUMP_DONE
