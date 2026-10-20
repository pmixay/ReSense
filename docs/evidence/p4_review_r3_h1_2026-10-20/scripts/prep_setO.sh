#!/bin/bash
# Set O (cloud_with_fake_obj.zst, Yandex Disk) streamed once through a named pipe: sha256 + byte count of the
# same bytes that unpack_dataset.py reads; then the gate cache and the X3 node-decoded cache; then delete the bag.
set -u
W=/home/user/wt_ship; D=/home/user/data; L=$D/logs
export PATH=/home/user/venv/rs/bin:$PATH OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 RESENSE_REPO=$W
export PYTHONPATH=$W:$W/ros2_ws/src/resense_ros
HREF=$(curl -fsS --get --data-urlencode "public_key=https://disk.yandex.ru/d/KpkG_yKoGk-vHQ" \
  https://cloud-api.yandex.net/v1/disk/public/resources/download | python3 -c 'import json,sys; print(json.load(sys.stdin)["href"])')
mkdir -p $D/fifo; rm -f $D/fifo/setO.zst; mkfifo $D/fifo/setO.zst
( cd $W && python scripts/unpack_dataset.py $D/fifo/setO.zst --out $D ) > $L/unpack_setO.log 2>&1 &
up=$!
curl -fsSL "$HREF" | tee >(sha256sum > $L/setO.sha256) >(wc -c > $L/setO.bytes) > $D/fifo/setO.zst
wait $up; echo "unpack exit $? $(date -u +%T)"; sleep 2; cat $L/setO.sha256 $L/setO.bytes
B=$(find $D -maxdepth 2 -type d -name cloud_with_fake_obj | grep -v cache | grep -v decoded | head -1); echo "bag $B"; ls -la $B
( cd $W && python scripts/cache_frames.py $B $D/cache/cloud_with_fake_obj --every 1 --int16 --stamps ) > $L/cache_setO.log 2>&1 &
c=$!
( cd $W && python docs/evidence/judgement_2026-10-13/scripts/cache_decoded.py $B $D/decoded/cloud_with_fake_obj ) > $L/decoded_setO.log 2>&1
echo "decoded exit $?"; wait $c; echo "cache exit $?"
rm -rf "$B"; echo SETO_DONE $(date -u +%T)
