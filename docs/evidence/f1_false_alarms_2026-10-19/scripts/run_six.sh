#!/bin/bash
# run_six.sh <tag> [--set k=v ...]: the six recordings through replay.py (one detector each), with the low record
source /tmp/claude-0/-home-user-ReSense/314e4672-57bf-5bc8-aad1-a40ec29bc1c0/scratchpad/f1/env.sh
TAG=$1; shift; OUT=$SP/runs/$TAG; mkdir -p $OUT
R=$RESENSE_REPO/docs/evidence/f1_false_alarms_2026-10-19/scripts/replay.py
for b in doubleT_obstacle doubleT_platform roundT_doubleT roundT_pressureGate_roundT roundT_squareT_pressureGate_squareT squareT_platform_squareT_switch cloud_with_fake_obj; do
  python $R --bag $b --out $OUT/$b --lowref --trace "$@" > $OUT/$b.log 2>&1
done
echo SIX_DONE $TAG
