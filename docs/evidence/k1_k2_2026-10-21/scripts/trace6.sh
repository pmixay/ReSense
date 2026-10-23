#!/bin/bash
# trace6.sh <tag> <repo> <outdir>: trace the six decoded recordings (no overrides: the tree's YAML)
tag=$1; repo=$2; out=$3; mkdir -p $out
. /data/work/env.sh; setrepo $repo; cd $repo
for b in doubleT_obstacle doubleT_platform roundT_doubleT roundT_pressureGate_roundT roundT_squareT_pressureGate_squareT squareT_platform_squareT_switch; do
  echo "python /data/work/trace_decoded.py /data/decoded/$b $out/${tag}_$b.jsonl"
done | xargs -P 2 -I{} sh -c "{} 2>/dev/null"
