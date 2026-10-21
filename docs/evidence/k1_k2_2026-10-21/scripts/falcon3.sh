#!/bin/bash
# One stream of falcon_test.zst teed to sha256/bytes and falcon_trace.py of control, off, cand (each its own tree).
set -u
O=/data/acc/falcon; . /opt/venv/bin/activate; export OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
T=docs/evidence/f1_false_alarms_2026-10-19/scripts/falcon_trace.py
run() { (export RESENSE_REPO=$2 PYTHONPATH=$2:$2/ros2_ws/src/resense_ros; cd $2; python $T /dev/stdin --out $O/$1 > $O/$1.log 2>&1); }
HREF=$(curl -fsS --get --data-urlencode "public_key=https://disk.yandex.ru/d/SfBeRHbs8bNJAQ" \
  --data-urlencode "path=/falcon_test.zst" https://cloud-api.yandex.net/v1/disk/public/resources/download \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["href"])')
date -u +"start %T"
curl -fsSL "$HREF" | tee >(sha256sum > $O/stream.sha256) >(wc -c > $O/stream.bytes) \
  >(run off /opt/off1) >(run cand /opt/cand1) | run control /opt/base
echo "pipe status ${PIPESTATUS[*]}"
until [ -s $O/off.meta.json ] && [ -s $O/cand.meta.json ] && [ -s $O/stream.sha256 ]; do sleep 5; done
date -u +"end %T"; cat $O/stream.sha256 $O/stream.bytes
echo FALCON_DONE
