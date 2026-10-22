#!/bin/bash
# full regression gate (seal baseline, no --allow) on the four trees, one core each; per-frame work kept
. /home/user/venv/bin/activate; export OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
O=/data/acc/gate; mkdir -p $O
for t in ${TREES:-ctl:/home/user/wt/base k2:/home/user/wt/k2 preg2:/home/user/wt/preg2 comb:/home/user/wt/comb}; do n=${t%%:*}; r=${t#*:}
 (cd $r; export RESENSE_REPO=$r PYTHONPATH=$r:$r/ros2_ws/src/resense_ros; python -c "import resense; print(resense.__file__)" > $O/$n.which
  python scripts/regression_gate.py --cache /data/cache --jobs 1 \
   --baseline docs/evidence/results/regression_baseline_2026-09-29_shell_off.json \
   --out $O/gate_$n.json --work $O/work_$n > $O/gate_$n.txt 2>&1; echo "gate exit $?" >> $O/gate_$n.txt) &
done; wait; echo GATE_DONE
