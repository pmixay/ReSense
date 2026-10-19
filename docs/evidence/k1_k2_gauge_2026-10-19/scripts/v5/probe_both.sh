#!/bin/bash
until grep -q RANGE_DONE /data/work_k2/range/run.log; do sleep 15; done
export PATH=/home/user/venv/rs/bin:$PATH OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
for tag in base v5b; do
  T=/data/work_k2/trees/$([ $tag = base ] && echo base || echo v5)
  export RESENSE_REPO=$T PYTHONPATH=$T:$T/ros2_ws/src/resense_ros
  P=$T/docs/evidence/k1_k2_gauge_2026-10-19/tools/probe.py
  for b in squareT_platform_squareT_switch doubleT_obstacle; do
    date -u; (cd $T && python $P /data/decoded_f1/$b /data/work_k2/probe/${tag}_$b)
  done
done
date -u; echo PROBE_DONE
