#!/bin/bash
# the whole Falcon recording through the final tree (fin2), manual and falcon_ros, with the node's range path
set -u
O=/data/acc/falcon_node; mkdir -p $O; . /home/user/venv/bin/activate; export OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
R=/home/user/wt/fin2; export RESENSE_REPO=$R PYTHONPATH=$R:$R/ros2_ws/src/resense_ros; cd $R
cp /data/acc/falcon/spec.json $O/spec.json
HREF=$(curl -fsS --get --data-urlencode "public_key=https://disk.yandex.ru/d/SfBeRHbs8bNJAQ" \
  --data-urlencode "path=/falcon_test.zst" https://cloud-api.yandex.net/v1/disk/public/resources/download \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["href"])')
curl -fsSL "$HREF" | tee >(sha256sum > $O/stream.sha256) | python /home/user/ReSense/docs/evidence/integration_1.3_2026-10-21/scripts/node_policy_falcon.py /dev/stdin --out $O/fin2 --spec $O/spec.json > $O/run.log 2>&1
echo "exit $?" >> $O/run.log; echo FALCON_NODE_DONE >> $O/run.log
