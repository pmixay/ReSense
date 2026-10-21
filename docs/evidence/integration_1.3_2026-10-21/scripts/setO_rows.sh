#!/bin/bash
# set O per-frame rows (eval_real, as the gate) for control and combined, for the F2 re-measurement
. /home/user/venv/bin/activate; export OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
for t in ctl:/home/user/wt/base comb:/home/user/wt/comb; do n=${t%%:*}; r=${t#*:}
 (cd $r; RESENSE_REPO=$r PYTHONPATH=$r:$r/ros2_ws/src/resense_ros python scripts/eval_real.py --cache /data/cache --bags cloud_with_fake_obj --jobs 1 --out /data/acc/setO_rows/$n > /data/acc/setO_rows/$n.log 2>&1; echo "exit $?" >> /data/acc/setO_rows/$n.log) &
done; wait; echo SETO_ROWS_DONE
