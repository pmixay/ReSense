#!/bin/bash
# ICP odometry of A, B, C, D from the decoded caches (independent of the detector)
. /home/user/venv/bin/activate; export OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
mkdir -p /data/x1/icp; cd /home/user/wt/base; export RESENSE_REPO=$PWD PYTHONPATH=$PWD:$PWD/ros2_ws/src/resense_ros
T=/home/user/wt/comb/docs/evidence/k1_k2_gauge_2026-10-19/tools/icp_odometry.py
for b in roundT_squareT_pressureGate_squareT roundT_doubleT roundT_pressureGate_roundT squareT_platform_squareT_switch; do
  [ -s /data/x1/icp/icp_$b.json ] || python $T /data/decoded/$b /data/x1/icp/icp_$b.json > /data/acc/icp_$b.log 2>&1 &
done; wait; echo ICP_DONE
