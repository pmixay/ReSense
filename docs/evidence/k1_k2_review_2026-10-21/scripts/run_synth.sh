#!/bin/bash
# run_synth.sh <outdir> <jobs>: every attack scene x object on the control tree (/opt/base) and the candidate tree (/opt/cand3)
O=$1; J=${2:-2}; S=/home/user/ReSense/docs/evidence/k1_k2_review_2026-10-21/scripts/attack_synth.py
mkdir -p $O
. /opt/venv/bin/activate; export OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
list() {
 for sc in R300 R450 R600 entry exit scurve500 scurve350 double500 double350 siding300 diverge open400; do
  for ob in none p130 p130l1.6 p130l-1.6 p130l-1.9 walk110 cross100 recede100; do echo "$sc+$ob"; done
  case $sc in double*|siding*) echo "$sc+adjtrain60"; echo "$sc+adjtrain100";; esac
 done
}
list | while read n; do for t in base cand3; do echo "$n $t"; done; done | xargs -P $J -n 2 sh -c '
  n=$0; t=$1; f='$O'/${t}__${n}.jsonl; [ -s $f ] && exit 0
  cd /opt/$t && RESENSE_REPO=/opt/$t PYTHONPATH=/opt/$t:/opt/$t/ros2_ws/src/resense_ros python '$S' --scene "$n" --mode yaml --out $f.tmp > $f.log 2>&1 && mv $f.tmp $f'
echo SYNTH_DONE
