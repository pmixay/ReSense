#!/bin/bash
set -u
. /home/user/venv/bin/activate; cd /home/user/ReSense
export OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
date -u +"start %T"; df -h / | tail -1
python scripts/unpack_dataset.py https://disk.yandex.ru/d/KpkG_yKoGk-vHQ --out /data || { echo UNPACK_FAIL; exit 1; }
python scripts/cache_frames.py /data/cloud_with_fake_obj /data/cache/cloud_with_fake_obj --every 1 --int16 --stamps &
python docs/evidence/judgement_2026-10-13/scripts/cache_decoded.py /data/cloud_with_fake_obj /data/decoded/cloud_with_fake_obj > /data/acc/decoded_setO.log 2>&1 &
wait
ls /data/cache/cloud_with_fake_obj | grep -c npy; ls /data/decoded/cloud_with_fake_obj | grep -c npz
du -sh /data/cache/cloud_with_fake_obj /data/decoded/cloud_with_fake_obj
rm -rf /data/cloud_with_fake_obj; df -h / | tail -1; date -u +"end %T"; echo SETO_DONE
