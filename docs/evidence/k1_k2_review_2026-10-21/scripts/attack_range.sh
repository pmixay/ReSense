#!/bin/bash
# attack_range.sh: scene attacks as ray-cast injections into the real curve recordings B (roundT_doubleT, R ~ 400 m,
# double track) and C (roundT_pressureGate_roundT, curve entry), with the unchanged range_test.py of K1/K2 19.10.
# Each job runs twice at the SAME placement (the candidate's own object-free track, ~ the true track on curves):
# the candidate (tag cand) and control (tag ctlatcand, control with the candidate's baseline files).
set -u
. /opt/venv/bin/activate; export OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
RT=/home/user/ReSense/docs/evidence/k1_k2_gauge_2026-10-19/tools/range_test.py
R=/data/acc/range; O=$R/attack; mkdir -p $O/cand $O/ctlatcand
B=roundT_doubleT; C=roundT_pressureGate_roundT
jobs() {
 for rec in B C; do
  if [ $rec = B ]; then bag=$B; st="--start 50 --d0 230"; else bag=$C; st="--start 0 --d0 230"; fi
  for l in 1.6 -1.6 1.9 -1.9; do echo "${rec}_pout${l} $bag --obj 0.5,0.5,1.75 $st --lat $l"; done
  for l in 1.4 -1.4; do echo "${rec}_c05out${l} $bag --obj 0.5,0.5,0.5 $st --lat $l"; done
  for l in 4.1 -4.1; do echo "${rec}_train${l} $bag --obj 40,3.0,3.5 $st --lat $l"; echo "${rec}_car${l} $bag --obj 4,3.0,3.5 $st --lat $l"; done
  for l in 2.4 -2.4; do echo "${rec}_post${l} $bag --obj 0.3,0.3,3.0 $st --lat $l"; done
  echo "${rec}_recede5 $bag --obj 0.6,0.6,1.0 ${st/--d0 230/--d0 100} --vx 5"
  echo "${rec}_cross $bag --obj 0.5,0.5,1.75 ${st/--d0 230/--d0 150} --lat -4 --vy 1.0"
  echo "${rec}_appear100 $bag --obj 0.5,0.5,1.75 $st --appear 100"
  echo "${rec}_lat05 $bag --obj 0.5,0.5,1.75 $st --lat 0.5"
  echo "${rec}_latm05 $bag --obj 0.5,0.5,1.75 $st --lat -0.5"
 done
}
run() {  # name bag args... ; tag
  tag=$1; shift; name=$1; bag=$2; shift 2
  [ -s $O/$tag/$name.json ] && return
  if [ $tag = cand ]; then t=/opt/cand3; else t=/opt/base; fi
  (cd $t && RESENSE_REPO=$t PYTHONPATH=$t:$t/ros2_ws/src/resense_ros python $RT $R/cache_$tag/$bag /data/x1/icp/icp_$bag.json $O/$tag/$name "$@" > $O/$tag/$name.log 2>&1)
  echo "$tag $name $?"
}
export -f run; export O R RT
jobs | while read l; do echo "cand $l"; echo "ctlatcand $l"; done | xargs -P ${J:-3} -I{} bash -c 'run {}'
echo ATTACK_DONE
