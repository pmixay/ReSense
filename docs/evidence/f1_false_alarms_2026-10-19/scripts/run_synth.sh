#!/bin/bash
source /tmp/claude-0/-home-user-ReSense/314e4672-57bf-5bc8-aad1-a40ec29bc1c0/scratchpad/f1/env.sh
S=$RESENSE_REPO/docs/evidence/f1_false_alarms_2026-10-19/scripts/synth_local.py
for b in synthetic_platform synthetic_tunnels synthetic_switch; do
  python $S --zst https://disk.yandex.ru/d/SfBeRHbs8bNJAQ --bag $b --spool /data/synth_f1 --out $SP/synth/v2 > $SP/synth/v2_$b.log 2>&1
  echo "DONE $b $?"
done
