#!/bin/bash
# A-axis probe (default config) under the read-only hooks; its rows must equal the plain A-axis-default run.
W=/home/user/wt_ship; O=/home/user/p4r/aaxis
export OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 RESENSE_REPO=$W PYTHONPATH=$W
cd $W && /home/user/venv/rs/bin/python /home/user/p4r/scripts/hooks_runpy.py $O/A-axis-default-traced.hooks.ndjson \
  docs/evidence/judgement_2026-10-13/scripts/range_test.py /home/user/data/decoded/roundT_squareT_pressureGate_squareT \
  $O/icp_roundT_squareT_pressureGate_squareT.json $O/A-axis-default-traced --obj 0.3,0.3,2.8 --start 150 --d0 230 --end 340
echo "exit $?"
