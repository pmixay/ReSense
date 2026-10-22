#!/bin/bash
# run_attack.sh <control|cand> <outdir> <family> [--trace]
set -u
side=$1; out=$2; fam=$3; tr=${4:-}
W=/home/user/wt/$side
export RESENSE_REPO=$W PYTHONPATH=$W:$W/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
. /home/user/venv/bin/activate
mkdir -p "$out"
sfx=$side; [ -n "$tr" ] && sfx=${side}_trace
python /home/user/ReSense/docs/evidence/f1a_bounded_review_2026-10-21/attack.py --family "$fam" --out "$out/$fam-$sfx.json" --jobs ${JOBS:-4} $tr > "$out/$fam-$sfx.log" 2>&1
echo "$side $fam $tr rc=$? $(date -u +%T)"
