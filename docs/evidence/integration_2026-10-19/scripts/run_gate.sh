#!/bin/bash
# run_gate.sh <repo> <tag> <jobs> [--set k=v ...]: the full regression gate of <repo> against the seal baseline
REPO=$1; TAG=$2; J=$3; shift 3
export PATH=/home/user/venv/rs/bin:$PATH RESENSE_REPO=$REPO PYTHONPATH=$REPO:$REPO/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
SP=/tmp/claude-0/-home-user-ReSense/314e4672-57bf-5bc8-aad1-a40ec29bc1c0/scratchpad/f1
cd $REPO
python -c "import resense,sys;print('resense', resense.__file__)"
git -C $REPO rev-parse HEAD; git -C $REPO status --porcelain -- resense configs native | head
python scripts/regression_gate.py --cache /data/cache --jobs $J --work /data/work_f1/gate_$TAG \
  --baseline docs/evidence/results/regression_baseline_2026-09-29_shell_off.json \
  --out $SP/gates/gate_$TAG.json "$@"
echo "GATE_EXIT $?"
