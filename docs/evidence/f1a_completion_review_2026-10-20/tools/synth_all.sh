#!/bin/bash
# usage: synth_all.sh <wt> <tag> <jobs> [extra synth_controls args]
S=/tmp/claude-0/-home-user-ReSense/2f98805c-ba30-5c4f-b1a6-a591bfc61cdc/scratchpad/f1a_review
D=/home/user/ReSense/.claude/worktrees/agent-a8a0362cc58419a5f/docs/evidence/f1a_completion_review_2026-10-20
W=$1
TAG=$2
J=$3
shift 3
for fam in ${FAMS:-empty centre beside rail rail_ranges}; do
  $S/rv.sh $W synth_controls.py --family $fam --out $D/out/synth_${fam}_${TAG}.json --jobs $J "$@" > $S/out/synth_${fam}_${TAG}.log 2>&1
done
echo done > $S/out/synth_${TAG}.done
