#!/bin/bash
# One stream of falcon_test.zst teed to sha256/bytes and to falcon_multi.py (manual + falcon_ros replicas)
# of each tree in TREES (name:path[:probe[:spec]]); "probe" wraps the run in curve_state_probe.py; MULTI = runner
# (default falcon_multi.py of the integration tree; falcon_starts.py for start-frame windows), spec default $O/spec.json.
set -u
O=${O:-/data/rv/falcon}; . /home/user/venv/bin/activate; export OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
HERE=$(cd $(dirname $0) && pwd)
run() { local n=$1 r=$2 pr=${3:-} sp=${4:-$O/spec.json}; (export RESENSE_REPO=$r PYTHONPATH=$r:$r/ros2_ws/src/resense_ros; cd $r
  M=${MULTI:-/home/user/wt/int/docs/evidence/track_opinion_2026-10-21/scripts/falcon_multi.py}
  python -c "import resense;print(resense.__file__)" > $O/$n.which
  if [ "$pr" = probe ] || [ "$pr" = probectl ]; then PROBE_OUT=$O/$n.probe.jsonl PROBE_CONTROL=$([ "$pr" = probectl ] && echo 1 || echo 0) python $HERE/curve_state_probe.py $M /dev/stdin --out $O/$n --spec $sp > $O/$n.log 2>&1
  else python $M /dev/stdin --out $O/$n --spec $sp > $O/$n.log 2>&1; fi
  echo "$n exit $?" >> $O/$n.log); }
export -f run; export O HERE
mkdir -p $O
[ -f $O/spec.json ] || echo '[{"name": "manual", "profile": "manual", "pre": [], "set": [], "rows": false}, {"name": "ros", "profile": "falcon_ros", "pre": [], "set": [], "rows": false}]' > $O/spec.json
HREF=$(curl -fsS --get --data-urlencode "public_key=https://disk.yandex.ru/d/SfBeRHbs8bNJAQ" \
  --data-urlencode "path=/falcon_test.zst" https://cloud-api.yandex.net/v1/disk/public/resources/download \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["href"])')
date -u +"start %T"
TEES=(); for t in $TREES; do IFS=: read n r p sp <<< "$t"; mkdir -p $O/$n; TEES+=(">(run $n $r ${p:--} $sp)"); done
eval "curl -fsSL \"\$HREF\" | tee >(sha256sum > $O/stream.sha256) >(wc -c > $O/stream.bytes) ${TEES[*]} > /dev/null"
echo "pipe status ${PIPESTATUS[*]}"
for t in $TREES; do n=${t%%:*}; until grep -q " exit" $O/$n.log 2>/dev/null; do sleep 10; done; done
until [ -s $O/stream.sha256 ]; do sleep 5; done
date -u +"end %T"; cat $O/stream.sha256 $O/stream.bytes; echo FALCON_DONE
