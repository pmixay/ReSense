#!/bin/bash
# Synthetic acceptance runs (PROTOCOL A1, A3): the review's synth_controls.py (unchanged, read from the branch's
# copy of the review directory) and ext_scenes.py, on the control worktree (v1.2.0) and the candidate worktree.
#   run_synth.sh <side: control|cand> <out dir> [families...]
set -u
side=$1; out=$2; shift 2
W=/home/user/wt/$side
REV=/home/user/ReSense/docs/evidence/f1a_completion_review_2026-10-20
EXT=/home/user/ReSense/docs/evidence/f1a_bounded_2026-10-21/ext_scenes.py
export RESENSE_REPO=$W PYTHONPATH=$W:$W/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
. /home/user/venv/bin/activate
mkdir -p "$out"
for fam in "$@"; do
  case $fam in
    ext_*) python "$EXT" --family "${fam#ext_}" --out "$out/synth_${fam}_${side}.json" --jobs 4 > "$out/synth_${fam}_${side}.log" 2>&1 ;;
    *) python "$REV/synth_controls.py" --family "$fam" --out "$out/synth_${fam}_${side}.json" --jobs 4 > "$out/synth_${fam}_${side}.log" 2>&1 ;;
  esac
  echo "$side $fam rc=$? $(date -u +%T)"
done
