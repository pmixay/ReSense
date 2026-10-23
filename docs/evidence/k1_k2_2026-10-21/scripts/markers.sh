#!/bin/bash
# one marked bag at a time: unpack, replay control/off/cand (judge runner, each tree's YAML), decoded cache for B6, delete
set -u
. /data/work/env.sh
O=/data/acc/markers; S=/home/user/ReSense/docs/evidence/k1_k2_2026-10-21/scripts
for b in tunnels platform switch; do
  bag=synthetic_${b}_cloud_with_markers
  [ -s $O/cand_$b.jsonl ] && continue
  python /home/user/ReSense/scripts/unpack_dataset.py /data/markers.zst --out /data/mbags --only $bag
  bd=$(find /data/mbags -maxdepth 3 -type d -name $bag | head -1); echo "bag dir $bd"
  for t in control:/opt/base off:/opt/off1 cand:/opt/cand1; do
    n=${t%%:*}; r=${t#*:}
    (setrepo $r; cd $r; python $S/judge_runner_set.py --bag $bd --out $O/${n}_$b > $O/${n}_$b.log 2>&1) &
  done
  [ -f /data/decoded/synthetic_$b/meta.json ] || (python /home/user/ReSense/docs/evidence/judgement_2026-10-13/scripts/cache_decoded.py $bd /data/decoded/synthetic_$b > /dev/null 2>&1) &
  wait
  rm -rf /data/mbags; df -h / | tail -1
done
echo MARKERS_DONE
