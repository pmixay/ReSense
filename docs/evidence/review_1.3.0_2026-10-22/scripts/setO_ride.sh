#!/bin/bash
# set O (Yandex, streamed unpack) -> zstd gate cache + decoded cache; then the ride intake (cache_extended_ride.py)
set -u
. /home/user/venv/bin/activate; R=/home/user/wt/int; cd $R; A=/data/rv/acc
if [ ! -f /data/cache/cloud_with_fake_obj/cloud_with_fake_obj_stamps.json ]; then
  for k in 1 2 3 4 5; do
    HREF=$(curl -fsS --get --data-urlencode "public_key=https://disk.yandex.ru/d/KpkG_yKoGk-vHQ" \
      https://cloud-api.yandex.net/v1/disk/public/resources/download | python3 -c 'import json,sys; print(json.load(sys.stdin)["href"])')
    curl -fsSL -C - -o /data/setO.zst "$HREF" && break; echo "setO download attempt $k failed"; sleep 30
  done
  echo "setO zst sha256 $(sha256sum /data/setO.zst | cut -d' ' -f1) (want d41c2fb28475194a98efeca5d2ee3fd175c0aef350ffb92fff4c26d497e696e9)"
  python scripts/unpack_dataset.py /data/setO.zst --out /data || { echo SETO_UNPACK_FAIL; exit 1; }
  rm -f /data/setO.zst
  python scripts/cache_frames.py /data/cloud_with_fake_obj /data/cache/cloud_with_fake_obj --every 1 --int16 --stamps --zstd > $A/cache_setO.log 2>&1 &
  python docs/evidence/judgement_2026-10-13/scripts/cache_decoded.py /data/cloud_with_fake_obj /data/decoded/cloud_with_fake_obj > $A/decoded_setO.log 2>&1 &
  wait
  echo "setO cache $(ls /data/cache/cloud_with_fake_obj | grep -c npy) decoded $(ls /data/decoded/cloud_with_fake_obj | grep -c npz)"
  rm -rf /data/cloud_with_fake_obj; df -h / | tail -1
fi
echo SETO_DONE
for k in 1 2 3 4 5 6; do
  python scripts/cache_extended_ride.py --cache /data/cache/new_data --spool /data/.ride_spool --reserve-gib 3 >> $A/ride_intake.log 2>&1
  rc=$?; echo "attempt $k exit $rc"; [ $rc -eq 0 ] && break; sleep 30
done
ls /data/cache/new_data/*_stamps.json | wc -l; du -sh /data/cache/new_data; df -h / | tail -1; echo RIDE_DONE
