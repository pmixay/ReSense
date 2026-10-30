#!/bin/bash
# One stream of falcon_test.zst teed to sha256/bytes and falcon_multi.py (manual + falcon_ros replicas) of control and combined
set -u
O=/data/acc/falcon; . /home/user/venv/bin/activate; export OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
M=/home/user/wt/comb/docs/evidence/track_opinion_2026-10-21/scripts/falcon_multi.py
run() { (export RESENSE_REPO=$2 PYTHONPATH=$2:$2/ros2_ws/src/resense_ros; cd $2; python -c "import resense;print(resense.__file__)" > $O/$1.which; python $M /dev/stdin --out $O/$1 --spec $O/spec.json > $O/$1.log 2>&1; echo "$1 exit $?" >> $O/$1.log); }
mkdir -p $O/ctl $O/comb
HREF=$(curl -fsS --get --data-urlencode "public_key=https://disk.yandex.ru/d/SfBeRHbs8bNJAQ" \
  --data-urlencode "path=/falcon_test.zst" https://cloud-api.yandex.net/v1/disk/public/resources/download \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["href"])')
date -u +"start %T"
curl -fsSL "$HREF" | tee >(sha256sum > $O/stream.sha256) >(wc -c > $O/stream.bytes) >(run comb /home/user/wt/comb) | run ctl /home/user/wt/base
echo "pipe status ${PIPESTATUS[*]}"
until grep -q "exit" $O/comb.log 2>/dev/null && [ -s $O/stream.sha256 ]; do sleep 10; done
date -u +"end %T"; cat $O/stream.sha256 $O/stream.bytes
echo FALCON_DONE
