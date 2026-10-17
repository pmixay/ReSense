#!/bin/bash
# A5: X1-style attribution of the visible non-STOP rows of the inserted objects on synthetic_platform 0-314.
# usage: run_a5.sh <tag> <checkout> <out dir>      (Linux runtime of the P4 protocol)
set -u
TAG=$1; R=$2; OUT=$3; H=/home/user/ReSense; D=/home/user/rs-data; PY=/home/user/rs-py310/bin/python
export RESENSE_REPO=$R PYTHONPATH=$R:$R/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
mkdir -p "$OUT"; cd "$R" || exit 1
L=$H/docs/evidence/synthetic_labels_2026-10-17/labels_synthetic_platform_0-314.json
W="--window obj03:57:314 --window obj01:0:176"
$PY "$H/scripts/range_attrib.py" run --hooks-off --repo "$R" --out x probe "$D/decoded/synthetic_platform" "$OUT/plat.off" --end 315 > "$OUT/plat.off.log" 2>&1
$PY "$H/scripts/range_attrib.py" run --repo "$R" --out "$OUT/plat" --labels "$L" $W --keep-frames probe "$D/decoded/synthetic_platform" "$OUT/plat.on" --end 315 > "$OUT/plat.on.log" 2>&1
$PY "$H/scripts/range_attrib.py" verify "$OUT/plat" "$OUT/plat.on.jsonl" "$OUT/plat.off.jsonl"
$PY "$H/scripts/range_attrib.py" table --out "$OUT/table.json" "$OUT/plat"
echo A5_DONE "$TAG" exit=$?
