#!/bin/bash
# nominal probe.py run (judge record format, with the node's monitored range) per recording for a tree
tag=$1; repo=$2; shift 2; O=/data/acc/b6; . /data/work/env.sh; setrepo $repo; cd $repo
for b in "$@"; do
  [ -s $O/run_${tag}_$b.jsonl ] || python docs/evidence/judgement_2026-10-13/scripts/probe.py /data/decoded/$b $O/run_${tag}_$b > $O/run_${tag}_$b.log 2>&1
  echo "$tag $b $?"
done
