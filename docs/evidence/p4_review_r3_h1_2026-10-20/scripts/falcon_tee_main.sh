#!/bin/bash
# One stream of falcon_test.zst (Yandex Disk, published size/sha256 checked) teed to: sha256 + byte count,
# and three falcon_trace.py runs of the shipped source: default (reproduction control), R3 off, H1 off.
set -u
W=/home/user/wt_main; O=/home/user/p4r/falcon_main; mkdir -p $O
export PATH=/home/user/venv/rs/bin:$PATH OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 RESENSE_REPO=$W PYTHONPATH=$W
T=$W/docs/evidence/f1_false_alarms_2026-10-19/scripts/falcon_trace.py
HREF=$(curl -fsS --get --data-urlencode "public_key=https://disk.yandex.ru/d/SfBeRHbs8bNJAQ" \
  --data-urlencode "path=/falcon_test.zst" https://cloud-api.yandex.net/v1/disk/public/resources/download \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["href"])')
date -u +"start %T"
curl -fsSL "$HREF" | tee >(sha256sum > $O/stream.sha256) >(wc -c > $O/stream.bytes) \
  >(python $T /dev/stdin --out $O/r3off --set tracking.cable_confirm_time_s=0 > $O/r3off.log 2>&1) \
  >(python $T /dev/stdin --out $O/h1off --set cluster.column_core_margin=0 > $O/h1off.log 2>&1) \
  | python $T /dev/stdin --out $O/default > $O/default.log 2>&1
echo "pipe status ${PIPESTATUS[*]}"
until [ -s $O/r3off.meta.json ] && [ -s $O/h1off.meta.json ] && [ -s $O/stream.sha256 ]; do sleep 5; done
date -u +"end %T"; cat $O/stream.sha256 $O/stream.bytes
echo FALCON_DONE
