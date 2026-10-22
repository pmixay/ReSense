#!/bin/bash
# the far-range review's 6-start table: plain falcon_ros replays from frames 0..2400 to 3300 (scene_run.py --plain), per tree
O=/data/acc/starts; mkdir -p $O; SR=/home/user/ReSense/docs/evidence/falcon_far_range_review_2026-10-21/scripts/scene_run.py
for s in 0 600 1200 1800 2100 2400; do for w in ${WS:-base fin}; do echo $s $w; done; done | xargs -P ${1:-4} -L 1 bash -c '
s=$0; w=$1
[ -f '$O'/s${s}__${w}.meta.json ] && exit 0
. /home/user/venv/bin/activate
export RESENSE_REPO=/home/user/wt/$w PYTHONPATH=/home/user/wt/$w:/home/user/wt/$w/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
cd /home/user/wt/$w && python '$SR' --plain --cache /data/falcon --frames $s:3300 --out '$O'/s${s}__${w} > '$O'/s${s}__${w}.log 2>&1 || echo FAIL $s $w'
echo STARTSDONE
