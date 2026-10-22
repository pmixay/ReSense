#!/bin/bash
# X3: a fresh v1.2.0 battery (control), then each candidate in CANDS (name:path) against it
. /home/user/venv/bin/activate; export OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
O=${O:-/data/rv/x3}; mkdir -p $O
(cd /home/user/wt/ctl; export RESENSE_REPO=$PWD PYTHONPATH=$PWD:$PWD/ros2_ws/src/resense_ros
 python -c "import resense; print(resense.__file__)" > $O/control.which
 [ -s $O/control.json ] || { python scripts/robustness_battery.py --repo $PWD --cache /data/decoded --out $O/control.json -j ${J:-2} > $O/control.log 2>&1; echo "control exit $?" >> $O/control.log; })
for t in $CANDS; do n=${t%%:*}; r=${t#*:}
(cd $r; export RESENSE_REPO=$PWD PYTHONPATH=$PWD:$PWD/ros2_ws/src/resense_ros
 python -c "import resense; print(resense.__file__)" > $O/$n.which; git rev-parse HEAD > $O/$n.commit
 python scripts/robustness_battery.py --repo $PWD --cache /data/decoded --out $O/$n.json -j ${J:-2} --reference $O/control.json > $O/$n.log 2>&1; echo "$n exit $?" >> $O/$n.log)
done
echo X3_DONE
