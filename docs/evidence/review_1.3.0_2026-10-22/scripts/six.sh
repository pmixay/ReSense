#!/bin/bash
# The six recordings from the zip: per bag unpack -> zstd gate cache (+ decoded cache for X3 bags) -> delete the bag
set -u
. /home/user/venv/bin/activate; R=/home/user/wt/int; cd $R; export OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
Z=/data/Датасет.zip; A=/data/rv/acc; mkdir -p $A
want=e23166801794cdeb2dcd77a3cc8b40a906b1d9cefab6f26739e368234e9168be; got=$(sha256sum $Z | cut -d' ' -f1)
echo "zip sha256 $got (want $want)"; [ "$got" = "$want" ] || { echo ZIP_SHA_MISMATCH; exit 1; }
for b in doubleT_obstacle doubleT_platform roundT_doubleT roundT_pressureGate_roundT roundT_squareT_pressureGate_squareT squareT_platform_squareT_switch; do
  [ -f /data/cache/$b/${b}_stamps.json ] && continue
  python scripts/unpack_dataset.py $Z --out /data --only $b || { echo "UNPACK_FAIL $b"; exit 1; }
  bd=/data/for_hackathon/$b
  python scripts/cache_frames.py $bd /data/cache/$b --every 1 --int16 --stamps --zstd > $A/cache_$b.log 2>&1 &
  case $b in doubleT_obstacle|roundT_squareT_pressureGate_squareT|squareT_platform_squareT_switch)
    python docs/evidence/judgement_2026-10-13/scripts/cache_decoded.py $bd /data/decoded/$b > $A/decoded_$b.log 2>&1 & ;; esac
  wait
  grep "for_hackathon/$b/" scripts/cold_bags.sha256 | (cd /data && sha256sum -c - 2>&1) | tee -a $A/six_bag_sha.txt
  [ $b = doubleT_obstacle ] && cp $bd/metadata.yaml $A/doubleT_obstacle_metadata.yaml
  echo "$b cache $(ls /data/cache/$b | grep -c npy) decoded $(ls /data/decoded/$b 2>/dev/null | grep -c npz)"
  rm -rf "/data/for_hackathon/$b"; df -h / | tail -1
done
echo SIX_DONE
