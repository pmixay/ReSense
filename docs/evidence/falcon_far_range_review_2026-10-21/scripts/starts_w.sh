#!/bin/bash
# plain replays from different start frames to 3300, both checkouts: does the first / held STOP depend on the start?
O=/home/user/rv/starts; mkdir -p $O
for s in 0 600 1200 1800 2100 2400; do for w in ${WS:-wt_v120 wt_cand}; do echo $s $w; done; done | xargs -P ${1:-4} -L 1 bash -c '
s=$0; w=$1
[ -f '$O'/s${s}__${w}.meta.json ] && exit 0
. /home/user/venv/bin/activate
export RESENSE_REPO=/home/user/$w PYTHONPATH=/home/user/$w:/home/user/$w/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
cd /home/user/rv && python s/scene_run.py --plain --frames $s:3300 --out '$O'/s${s}__${w} > '$O'/s${s}__${w}.log 2>&1 || echo FAIL $s $w'
echo STARTSDONE
