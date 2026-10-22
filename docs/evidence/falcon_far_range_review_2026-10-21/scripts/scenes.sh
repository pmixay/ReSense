#!/bin/bash
# run every scene spec of index.json on both checkouts: scenes.sh <specdir> <outdir> <jobs> [name-filter-regex]
S=$1; O=$2; J=$3; F=${4:-.}
mkdir -p $O
python3 -c "
import json; [print(n, f) for n,f in json.load(open('$S/index.json'))]" | grep -E "$F" | while read n f; do
  for w in wt_v120 wt_cand; do echo "$n $f $w"; done
done | xargs -P $J -L 1 bash -c '
n=$0; f=$1; w=$2
[ -f '$O'/${n}__${w}.meta.json ] && exit 0
. /home/user/venv/bin/activate
export RESENSE_REPO=/home/user/$w PYTHONPATH=/home/user/$w:/home/user/$w/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
python /home/user/rv/s/scene_run.py --frames $f --spec '$S'/$n.json --out '$O'/${n}__${w} > '$O'/${n}__${w}.log 2>&1 || echo FAIL $n $w'
echo SCENESDONE
