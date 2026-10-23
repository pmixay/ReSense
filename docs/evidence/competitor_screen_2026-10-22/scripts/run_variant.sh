#!/usr/bin/env bash
# usage: run_variant.sh <name> [--set k=v ...]
set -uo pipefail
SP=${SCRATCH:?set SCRATCH to a work directory}; REPO=/home/user/ReSense
NAME=$1; shift
cd $REPO
export PYTHONPATH=$REPO RESENSE_REPO=$REPO OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
mkdir -p $SP/out/$NAME
$SP/venv/bin/python scripts/regression_gate.py --cache $SP/cache --work $SP/out/$NAME/work --jobs 4 \
  --baseline docs/evidence/results/regression_baseline_2026-09-29_shell_off.json \
  --allow 'ride.*' --allow 'set_F_straight.*' --out $SP/out/$NAME/gate.json "$@" > $SP/logs/gate_$NAME.log 2>&1
echo "gate_exit=$?" >> $SP/logs/gate_$NAME.log
