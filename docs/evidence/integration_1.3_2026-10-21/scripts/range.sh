#!/bin/bash
# K2 range jobs: own placement (ctl, comb), then the same placement both ways (ctlatcomb: control with the
# combined tree's object-free baseline files; combatctl: the reverse), as the K2 review
. /home/user/venv/bin/activate; export OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
P=/home/user/wt/comb/docs/evidence/k1_k2_gauge_2026-10-19/tools/prebuild_range.py; O=/data/acc/range; mkdir -p $O
B=/home/user/wt/base; C=${RANGE_CAND:-/home/user/wt/comb}; N=${RANGE_NAME:-comb}
python $P --repo $B --tag ctl --data /data --out $O -j 2 > $O/ctl.log 2>&1 &
python $P --repo $C --tag $N --data /data --out $O -j 2 > $O/$N.log 2>&1 &
wait
for pr in "ctlat$N $B $N" "${N}atctl $C ctl"; do set -- $pr
  mkdir -p $O/cache_$1; cp $O/cache_$3/*_baseline.json $O/cache_$1/
  python $P --repo $2 --tag $1 --data /data --out $O -j 2 > $O/$1.log 2>&1 &
done; wait; echo RANGE_DONE
