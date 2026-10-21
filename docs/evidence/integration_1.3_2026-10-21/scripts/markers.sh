#!/bin/bash
# marked bags: download the archive once (sha256 checked), then one bag at a time: unpack, replay 4 trees, delete
set -u
. /home/user/venv/bin/activate; export OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
O=/data/acc/markers; mkdir -p $O; S=/home/user/wt/comb/docs/evidence/k1_k2_2026-10-21/scripts
if [ ! -s /data/markers.zst ]; then
  HREF=$(curl -fsS --get --data-urlencode "public_key=https://disk.yandex.ru/d/SfBeRHbs8bNJAQ" \
    --data-urlencode "path=/new_synth_data_with_markers.zst" https://cloud-api.yandex.net/v1/disk/public/resources/download \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["href"])')
  curl -fsSL -o /data/markers.zst "$HREF" || { echo DL_FAIL; exit 1; }
fi
sha256sum /data/markers.zst | tee $O/markers_zst.sha256
for b in tunnels platform switch; do
  bag=synthetic_${b}_cloud_with_markers
  [ -s $O/comb_$b.jsonl ] && continue
  python /home/user/ReSense/scripts/unpack_dataset.py /data/markers.zst --out /data/mbags --only $bag
  bd=$(find /data/mbags -maxdepth 3 -type d -name $bag | head -1); echo "bag dir $bd"; du -sh $bd
  for t in ctl:/home/user/wt/base k2:/home/user/wt/k2 preg2:/home/user/wt/preg2 comb:/home/user/wt/comb; do
    n=${t%%:*}; r=${t#*:}
    (cd $r; RESENSE_REPO=$r PYTHONPATH=$r:$r/ros2_ws/src/resense_ros python $S/judge_runner_set.py --bag $bd --out $O/${n}_$b > $O/${n}_$b.log 2>&1; echo "exit $?" >> $O/${n}_$b.log) &
  done
  wait
  rm -rf /data/mbags; df -h / | tail -1
done
echo MARKERS_DONE
