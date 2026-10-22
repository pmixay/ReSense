#!/bin/bash
# the author's matrix2.py on fresh seeds of mine (40, 41), both checkouts, frames 1290+ of the cache
F=/home/user/ReSense/docs/evidence/falcon_far_range_2026-10-21/scripts
O=/home/user/rv/matrix; mkdir -p $O
for w in wt_v120 wt_cand; do
  ( . /home/user/venv/bin/activate; cd /home/user/rv
    export RESENSE_REPO=/home/user/$w PYTHONPATH=/home/user/$w:/home/user/$w/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 FALCON_CACHE=/home/user/data/falcon
    python $F/matrix2.py --name $w --out $O --seeds 40,41 --jobs ${1:-2} --check-prefix ) > $O/$w.log 2>&1 &
done
wait
echo MATRIXDONE
