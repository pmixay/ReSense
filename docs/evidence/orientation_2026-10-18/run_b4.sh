#!/bin/bash
set -u
O=/home/user/rs-data/b4; PY=/home/user/rs-py310/bin/python
one() {  # tag checkout bag
  T=$1; R=$2; B=$3
  cd $R && RESENSE_REPO=$R PYTHONPATH=$R:$R/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 \
    $PY /home/user/ReSense/scripts/orientation_battery.py run /home/user/rs-data/decoded/$B $O/${T}_$B.json > $O/${T}_$B.log 2>&1
  cd $R && RESENSE_REPO=$R PYTHONPATH=$R:$R/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 \
    $PY /home/user/ReSense/docs/evidence/rejudge_2026-10-16/scripts/probe.py /home/user/rs-data/decoded/$B $O/plain_${T}_$B > $O/plain_${T}_$B.log 2>&1
  echo "$T $B exit=$?"
}
one v110 /home/user/rs-1.1.0 doubleT_obstacle & one v100 /home/user/rs-707ea9c doubleT_obstacle &
one v110 /home/user/rs-1.1.0 roundT_squareT_pressureGate_squareT & one v100 /home/user/rs-707ea9c roundT_squareT_pressureGate_squareT &
wait; echo B4_DONE
