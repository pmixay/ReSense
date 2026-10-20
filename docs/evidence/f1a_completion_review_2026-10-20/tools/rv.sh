#!/bin/bash
# usage: rv.sh <checkout|-> <script-in-deliverable-dir> [args...]
# '@S' in args = scratch dir, '@D' = deliverable dir. checkout '-' = no repo (PYTHONPATH unset), run with python -I.
S=/tmp/claude-0/-home-user-ReSense/2f98805c-ba30-5c4f-b1a6-a591bfc61cdc/scratchpad/f1a_review
D=/home/user/ReSense/.claude/worktrees/agent-a8a0362cc58419a5f/docs/evidence/f1a_completion_review_2026-10-20
W=$1
SCRIPT=$2
shift 2
ARGS=()
for x in "$@"; do
  x=${x//@S/$S}
  x=${x//@D/$D}
  ARGS+=("$x")
done
export OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export LD_LIBRARY_PATH=$S/stublib
if [ "$W" = "-" ]; then
  exec $S/venv/bin/python -I $D/$SCRIPT "${ARGS[@]}"
fi
export RESENSE_REPO=$S/$W
export PYTHONPATH=$S/$W
cd $S/$W || exit 99
exec $S/venv/bin/python $D/$SCRIPT "${ARGS[@]}"
