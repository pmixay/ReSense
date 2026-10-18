#!/bin/bash
# B6: poses once per recording (detector-independent), track model per version, then measure.
set -u
O=/home/user/rs-data/b6; G=/home/user/ReSense/scripts/gauge_stability.py; PY=/home/user/rs-py310/bin/python
BAGS="doubleT_obstacle doubleT_platform roundT_doubleT roundT_pressureGate_roundT roundT_squareT_pressureGate_squareT squareT_platform_squareT_switch cloud_with_fake_obj synthetic_platform synthetic_switch synthetic_tunnels"
for b in $BAGS; do
  R=/home/user/rs-1.1.0; export RESENSE_REPO=$R PYTHONPATH=$R:$R/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
  [ -f $O/poses_$b.json ] || $PY $G poses /home/user/rs-data/decoded/$b $O/poses_$b.json > $O/poses_$b.log 2>&1
  for t in v110:/home/user/rs-1.1.0 v100:/home/user/rs-707ea9c; do
    T=${t%%:*}; R=${t#*:}; export RESENSE_REPO=$R PYTHONPATH=$R:$R/ros2_ws/src/resense_ros
    mkdir -p $O/$T; cd $R
    [ -f $O/$T/track_$b.json ] || $PY $G track /home/user/rs-data/decoded/$b $O/$T/track_$b.json > $O/$T/track_$b.log 2>&1
    $PY $G measure $O/$T/track_$b.json $O/poses_$b.json $O/$T/measure_$b.json > /dev/null 2>$O/$T/measure_$b.err
    echo "$b $T exit=$?"
  done
done
echo B6_DONE
