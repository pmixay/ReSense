#!/bin/bash
# Sampled K2 range jobs (judge's range_test.py of k1_k2_gauge_2026-10-19/tools, job arguments as prebuild_range.py)
# B / C x person / cube05 / cube1: own placement for ctl (v1.2.0) and fin (1.3.0), and ctl at fin's placement
# (ctl run with fin's object-free baseline files: the same object positions as fin).
set -u
. /home/user/venv/bin/activate; export OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
T=/home/user/wt/fin/docs/evidence/k1_k2_gauge_2026-10-19/tools; O=/data/rv/range; mkdir -p $O
B=roundT_doubleT; C=roundT_pressureGate_roundT
declare -A ARGS=([B_person]="$B --obj 0.5,0.5,1.75 --start 50 --d0 230" [B_cube05]="$B --obj 0.5,0.5,0.5 --start 50 --d0 230"
  [B_cube1]="$B --obj 1.0,1.0,1.0 --start 50 --d0 230" [C_person]="$C --obj 0.5,0.5,1.75 --start 0 --d0 230"
  [C_cube05]="$C --obj 0.5,0.5,0.5 --start 0 --d0 230" [C_cube1]="$C --obj 1.0,1.0,1.0 --start 0 --d0 230")
base() { local tag=$1 repo=$2; mkdir -p $O/cache_$tag $O/$tag
  for b in $B $C; do [ -e $O/cache_$tag/$b ] || ln -s /data/decoded/$b $O/cache_$tag/$b
    [ -s $O/cache_$tag/${b}_baseline.json ] || (cd $repo; RESENSE_REPO=$repo PYTHONPATH=$repo:$repo/ros2_ws/src/resense_ros \
      python -c "import sys; sys.path.insert(0, '$T'); import range_test as t; t.baseline('$O/cache_$tag/$b', '$O/cache_$tag/${b}_baseline.json')"); done; }
job() { local tag=$1 repo=$2 name=$3; set -- ${ARGS[$name]}; local bag=$1; shift
  (cd $repo; RESENSE_REPO=$repo PYTHONPATH=$repo:$repo/ros2_ws/src/resense_ros python $T/range_test.py $O/cache_$tag/$bag \
    /data/x1/icp/icp_$bag.json $O/$tag/$name "$@" > $O/$tag/$name.log 2>&1; echo "$tag $name exit $?"); }
base ctl /home/user/wt/ctl & base fin /home/user/wt/fin & wait
mkdir -p $O/cache_ctlatfin; cp $O/cache_fin/*_baseline.json $O/cache_ctlatfin/
for b in $B $C; do [ -e $O/cache_ctlatfin/$b ] || ln -s /data/decoded/$b $O/cache_ctlatfin/$b; done
for n in "${!ARGS[@]}"; do for t in ctl:/home/user/wt/ctl fin:/home/user/wt/fin ctlatfin:/home/user/wt/ctl; do echo "${t%%:*} ${t#*:} $n"; done; done \
  | xargs -P ${JOBS:-3} -L 1 bash -c "$(declare -f job); $(declare -p ARGS O T B C); job \$0 \$1 \$2"
echo RANGE_DONE
