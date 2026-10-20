#!/bin/bash
# run the reviewer finding tests on all three checkouts; write outputs into the deliverable out/ dir
S=/tmp/claude-0/-home-user-ReSense/2f98805c-ba30-5c4f-b1a6-a591bfc61cdc/scratchpad/f1a_review
D=/home/user/ReSense/.claude/worktrees/agent-a8a0362cc58419a5f/docs/evidence/f1a_completion_review_2026-10-20
export OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export LD_LIBRARY_PATH=$S/stublib
for w in wt_ref wt_parent wt_cand; do
  cd $S/$w || exit 1
  PYTHONPATH=$S/$w:$S/$w/tests RESENSE_REPO=$S/$w $S/venv/bin/python -m pytest -q -p no:cacheprovider --rootdir=$S/$w $D/review_findings_checks.py > $D/out/review_findings_$w.txt 2>&1
  echo "$w: $(tail -1 $D/out/review_findings_$w.txt)"
done
