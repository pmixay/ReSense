#!/bin/bash
# full regression gate per tree (seal baseline, no --allow); per-frame work kept for the paired diff
tag=$1; repo=$2; jobs=${3:-2}
. /data/work/env.sh; setrepo $repo; cd $repo
mkdir -p /data/acc/gate
python scripts/regression_gate.py --cache /data/cache --jobs $jobs \
  --baseline docs/evidence/results/regression_baseline_2026-09-29_shell_off.json \
  --out /data/acc/gate/gate_$tag.json --work /data/acc/gate/work_$tag > /data/acc/gate/gate_$tag.txt 2>&1
echo "$tag gate exit $?"
