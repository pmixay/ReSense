#!/bin/bash
# the ride's per-frame rows (eval_real, 8 pieces as the gate) for the four trees, one core each
. /home/user/venv/bin/activate; export OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
O=/data/acc/ride; mkdir -p $O
for t in ${TREES:-ctl:/home/user/wt/base k2:/home/user/wt/k2 preg2:/home/user/wt/preg2 comb:/home/user/wt/comb}; do n=${t%%:*}; r=${t#*:}
 (cd $r; RESENSE_REPO=$r PYTHONPATH=$r:$r/ros2_ws/src/resense_ros python scripts/eval_real.py --cache /data/cache --bags new_data --jobs 1 --chunks 8 --out $O/$n > $O/$n.log 2>&1; echo "exit $?" >> $O/$n.log) &
done; wait; echo RIDE_ROWS_DONE
