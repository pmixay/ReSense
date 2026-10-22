#!/bin/bash
cd /home/user/rv
( . /home/user/venv/bin/activate; export RESENSE_REPO=/home/user/wt_rev2 PYTHONPATH=/home/user/wt_rev2:/home/user/wt_rev2/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
  python s/pandar_sample.py --cache /home/user/data/cache --work /home/user/rv/pandar/wt_rev2 doubleT_obstacle roundT_doubleT doubleT_platform new_data > pandar_rev2.log 2>&1 ) &
WS=wt_rev2 s/scenes_w.sh /home/user/rv/specs /home/user/rv/scenes 3 > scenes_rev2.log 2>&1
wait
WS=wt_rev2 s/starts_w.sh 2 > starts_rev2.log 2>&1 &
WS="wt_v120 wt_rev2" SEEDS=70,71 MO=/home/user/rv/matrix7071 s/matrix_runs_w.sh 1 > matrix7071.log 2>&1
wait
echo REV2DONE
