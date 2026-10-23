#!/bin/bash
# B6 track + measure per recording for a tree tag; poses from the committed gauge_stability b6_raw (detector-independent)
tag=$1; repo=$2; shift 2; O=/data/acc/b6; mkdir -p $O
. /data/work/env.sh; setrepo $repo; cd $repo
for b in "$@"; do
  [ -s $O/track_${tag}_$b.json ] || python scripts/gauge_stability.py track /data/decoded/$b $O/track_${tag}_$b.json > $O/track_${tag}_$b.log 2>&1
  python scripts/gauge_stability.py measure $O/track_${tag}_$b.json /data/b6/poses_$b.json $O/measure_${tag}_$b.json > /dev/null 2> $O/measure_${tag}_$b.err
  echo "$tag $b $?"
done
