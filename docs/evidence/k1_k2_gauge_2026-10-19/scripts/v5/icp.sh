#!/bin/bash
T=/data/work_k2/trees/base
export PATH=/home/user/venv/rs/bin:$PATH RESENSE_REPO=$T PYTHONPATH=$T:$T/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
E=$T/docs/evidence/k1_k2_gauge_2026-10-19/tools
cd $T
for b in roundT_squareT_pressureGate_squareT squareT_platform_squareT_switch; do
  date -u; python $E/icp_odometry.py /data/decoded_f1/$b /data/work_k2/rdata/x1/icp/icp_$b.json
done
date -u; echo ICP_DONE
