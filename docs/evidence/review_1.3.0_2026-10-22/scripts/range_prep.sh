#!/bin/bash
# B, C decoded caches from the zip (sha256 checked) and their ICP odometry (k1_k2_gauge tools, ctl checkout), then the range sample
set -u
while ps -C curl -o args= | grep -q "D0%94%D0%B0"; do sleep 10; done   # the zip download (started separately)
. /home/user/venv/bin/activate; export OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1; R=/home/user/wt/fin; cd $R; A=/data/rv/acc
Z=/data/Датасет.zip; got=$(sha256sum $Z | cut -d' ' -f1); echo "zip sha256 $got"
[ $got = e23166801794cdeb2dcd77a3cc8b40a906b1d9cefab6f26739e368234e9168be ] || { echo ZIP_SHA_MISMATCH; exit 1; }
mkdir -p /data/x1/icp
for b in roundT_doubleT roundT_pressureGate_roundT; do
  python scripts/unpack_dataset.py $Z --out /data --only $b || exit 1
  python docs/evidence/judgement_2026-10-13/scripts/cache_decoded.py /data/for_hackathon/$b /data/decoded/$b > $A/decoded_$b.log 2>&1
  rm -rf /data/for_hackathon/roundT_doubleT /data/for_hackathon/roundT_pressureGate_roundT
  echo "$b decoded $(ls /data/decoded/$b | grep -c npz)"
  (cd /home/user/wt/ctl; RESENSE_REPO=$PWD PYTHONPATH=$PWD:$PWD/ros2_ws/src/resense_ros python $R/docs/evidence/k1_k2_gauge_2026-10-19/tools/icp_odometry.py /data/decoded/$b /data/x1/icp/icp_$b.json > $A/icp_$b.log 2>&1; echo "icp $b exit $?") &
done
wait; rm -f /data/Датасет.zip; df -h / | tail -1
/home/user/ReSense/docs/evidence/review_1.3.0_2026-10-22/scripts/range_sample.sh
