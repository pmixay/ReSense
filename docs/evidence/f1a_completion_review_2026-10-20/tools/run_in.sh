#!/bin/bash
# usage: run_in.sh <wt_ref|wt_parent|wt_cand> <command...>
# Runs the command with the evidence-run environment inside the named checkout.
S=/tmp/claude-0/-home-user-ReSense/2f98805c-ba30-5c4f-b1a6-a591bfc61cdc/scratchpad/f1a_review
W=$1
shift
export OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export RESENSE_REPO=$S/$W
export PYTHONPATH=$S/$W
export PY=$S/venv/bin/python
export LD_LIBRARY_PATH=$S/stublib
cd $S/$W || exit 99
exec "$@"
