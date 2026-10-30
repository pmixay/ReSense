#!/bin/bash
# X3: a fresh v1.2.0 battery, then the combined tree against it (no commits to these trees during the run)
. /home/user/venv/bin/activate; export OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
O=/data/acc/x3; mkdir -p $O; C=${X3_CAND:-/home/user/wt/comb}; N=${X3_NAME:-comb}
(cd /home/user/wt/base; export RESENSE_REPO=$PWD PYTHONPATH=$PWD:$PWD/ros2_ws/src/resense_ros
 [ -s $O/control.json ] || { python scripts/robustness_battery.py --repo $PWD --cache /data/decoded --out $O/control.json -j 2 > $O/control.log 2>&1; echo "control exit $?" >> $O/control.log; })
(cd $C; export RESENSE_REPO=$PWD PYTHONPATH=$PWD:$PWD/ros2_ws/src/resense_ros
 python scripts/robustness_battery.py --repo $PWD --cache /data/decoded --out $O/$N.json -j 2 --reference $O/control.json > $O/$N.log 2>&1; echo "$N exit $?" >> $O/$N.log)
echo X3_DONE
