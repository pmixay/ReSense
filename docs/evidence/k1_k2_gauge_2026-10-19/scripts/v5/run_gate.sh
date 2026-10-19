#!/bin/bash
# run_gate.sh <tree> <tag> [--set k=v ...]: the full regression gate of <tree> against the 29.09 baseline, --jobs 2
T=$1; TAG=$2; shift 2
export PATH=/home/user/venv/rs/bin:$PATH RESENSE_REPO=$T PYTHONPATH=$T:$T/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
O=/data/work_k2/gates/$TAG
mkdir -p $O
cd $T
python -c "import numpy, resense; assert numpy.__version__ == '1.26.4', numpy.__version__; print('numpy', numpy.__version__, 'resense', resense.__file__)"
git -C $T rev-parse HEAD; git -C $T status --porcelain -- resense configs native ros2_ws | head
date -u
python scripts/regression_gate.py --cache /data/cache --jobs 2 \
  --baseline docs/evidence/results/regression_baseline_2026-09-29_shell_off.json \
  --out $O/gate.json --work $O/work "$@" > $O/gate.txt 2>&1
echo "GATE_EXIT $?"
date -u
