#!/bin/bash
# the six recordings from the verified zip: per bag unpack -> zstd gate cache + decoded cache -> delete the bag
set -u
. /home/user/venv/bin/activate; cd /home/user/ReSense; export OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
want=$(head -1 scripts/cold_bags.sha256 | cut -d' ' -f1); got=$(sha256sum /data/dataset.zip | cut -d' ' -f1)
echo "zip sha256 $got (want $want)"; [ "$got" = "$want" ] || { echo ZIP_SHA_MISMATCH; exit 1; }
for b in doubleT_obstacle doubleT_platform roundT_doubleT roundT_pressureGate_roundT roundT_squareT_pressureGate_squareT squareT_platform_squareT_switch; do
  [ -f /data/cache/$b/${b}_stamps.json ] && [ -f /data/decoded/$b/meta.json -o $b = doubleT_platform ] && continue
  python scripts/unpack_dataset.py /data/dataset.zip --out /data --only $b || { echo "UNPACK_FAIL $b"; exit 1; }
  bd=/data/for_hackathon/$b; ls $bd
  python scripts/cache_frames.py $bd /data/cache/$b --every 1 --int16 --stamps --zstd &
  [ $b = doubleT_platform ] || python docs/evidence/judgement_2026-10-13/scripts/cache_decoded.py $bd /data/decoded/$b > /data/acc/decoded_$b.log 2>&1 &
  wait
  grep "for_hackathon/$b/" scripts/cold_bags.sha256 | (cd /data && sha256sum -c - 2>&1) | tee -a /data/acc/six_bag_sha.txt
  echo "$b cache $(ls /data/cache/$b | grep -c npy) decoded $(ls /data/decoded/$b 2>/dev/null | grep -c npz)"
  rm -rf "/data/for_hackathon/$b"; df -h / | tail -1
done
echo SIX_DONE
