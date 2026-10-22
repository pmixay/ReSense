#!/bin/bash
# marked bags: download the archive once (sha256 checked), then one bag at a time: unpack, replay the trees in
# TREES (name:path[:extra --set args separated by ,]) with the K2 lane's judge_runner_set.py, delete the bag
set -u
. /home/user/venv/bin/activate; export OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
O=/data/rv/markers; mkdir -p $O; JR=/home/user/wt/int/docs/evidence/k1_k2_2026-10-21/scripts/judge_runner_set.py
if [ ! -s /data/markers.zst ] || [ "$(sha256sum /data/markers.zst | cut -d' ' -f1)" != 04d176b49526e5da55a0481cf92d8442604dc0fb9f69c31680482b21d8682760 ]; then
  for k in 1 2 3 4; do
    HREF=$(curl -fsS --get --data-urlencode "public_key=https://disk.yandex.ru/d/SfBeRHbs8bNJAQ" \
      --data-urlencode "path=/new_synth_data_with_markers.zst" https://cloud-api.yandex.net/v1/disk/public/resources/download \
      | python3 -c 'import json,sys; print(json.load(sys.stdin)["href"])')
    curl -fsSL -C - -o /data/markers.zst "$HREF" && break; sleep 30
  done
fi
sha256sum /data/markers.zst | tee $O/markers_zst.sha256
for b in tunnels platform switch; do
  bag=synthetic_${b}_cloud_with_markers
  python /home/user/wt/int/scripts/unpack_dataset.py /data/markers.zst --out /data/mbags --only $bag
  bd=$(find /data/mbags -maxdepth 3 -type d -name $bag | head -1); echo "bag dir $bd"; du -sh $bd
  for t in $TREES; do
    IFS=: read n r extra <<< "$t"; [ "$n" = v5c ] && [ $b != tunnels ] && continue
    sets=""; [ -n "$extra" ] && for s in ${extra//,/ }; do sets="$sets --set $s"; done
    (cd $r; RESENSE_REPO=$r PYTHONPATH=$r:$r/ros2_ws/src/resense_ros python $JR --bag $bd --out $O/${n}_$b $sets > $O/${n}_$b.log 2>&1; echo "exit $?" >> $O/${n}_$b.log) &
  done
  wait
  rm -rf /data/mbags; df -h / | tail -1
done
echo MARKERS_DONE
