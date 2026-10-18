#!/bin/bash
# B3 / B8: Pandar -> Falcon and Falcon -> Pandar in ONE detector (judge runner, several --bag), plus each bag alone.
# usage: run_b3.sh <tag> <checkout> <out dir> <pandar bag dir> <falcon bag dir>   (runs one after another: timing)
set -u
TAG=$1; R=$2; OUT=$3; P=$4; F=$5
export RESENSE_REPO=$R PYTHONPATH=$R:$R/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
J=$(cd "$(dirname "$0")/.." && pwd)/rejudge_2026-10-16/scripts/judge_runner.py; PY=${PY:-python3}
mkdir -p "$OUT"; cd "$R" || exit 1
$PY $J --bag "$P" --out "$OUT/pandar"             > "$OUT/pandar.log" 2>&1
$PY $J --bag "$F" --out "$OUT/falcon"             > "$OUT/falcon.log" 2>&1
$PY $J --bag "$P" --bag "$F" --out "$OUT/p2f"     > "$OUT/p2f.log" 2>&1
$PY $J --bag "$F" --bag "$P" --out "$OUT/f2p"     > "$OUT/f2p.log" 2>&1
echo B3_RUN_DONE "$TAG"
