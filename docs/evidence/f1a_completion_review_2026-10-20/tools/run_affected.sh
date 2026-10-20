#!/bin/bash
# usage: run_affected.sh <wt> <logname>   -- the author's "affected" suite list, run on checkout <wt>
S=/tmp/claude-0/-home-user-ReSense/2f98805c-ba30-5c4f-b1a6-a591bfc61cdc/scratchpad/f1a_review
W=$1
L=$S/out/$2
T=""
for m in f1a_continuation f1a_b1 f1_false_alarms low_height_keep lowobj_near low_local_support rail_start modules core algorithm native cable_current_support cable_confirmation ego_veto explained_run; do
  T="$T tests/test_$m.py"
done
$S/run_in.sh $W $S/venv/bin/python -m pytest -q -rs -p no:cacheprovider --junitxml=$L.xml $T > $L.log 2>&1
echo "exit $?" >> $L.log
