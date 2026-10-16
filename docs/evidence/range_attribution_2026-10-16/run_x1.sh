#!/usr/bin/env bash
# X1 runs (PROTOCOL: ../p4_eval_1.1.0_2026-10-16/PROTOCOL.md §C). Usage: run_x1.sh <tag> <checkout> <data root>
# For each case: a plain judge run (hooks off, the equality reference) and the attributed run (hooks on),
# then verify. range_test caches the detector's own object-free track model next to the cache path
# (<cache>_baseline.json), so each checkout reads the decoded caches through its own symlink folder and
# the baselines are built once per recording before the parallel jobs.
set -u
TAG=$1; R=$2; D=$3
H=$(cd "$(dirname "$0")/../../.." && pwd)
PY=${PY:-python}
OUT=$D/x1/$TAG; CACHE=$OUT/cache; ICP=$D/x1/icp
mkdir -p "$CACHE"
export RESENSE_REPO=$R PYTHONPATH=$R:$R/ros2_ws/src/resense_ros OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export OPENBLAS_CORETYPE=${OPENBLAS_CORETYPE:-Haswell}   # PROTOCOL amendment 1
A=roundT_squareT_pressureGate_squareT; B=roundT_doubleT; C=roundT_pressureGate_roundT; S=squareT_platform_squareT_switch
for b in $A $B $C $S; do ln -sfn "$D/decoded/$b" "$CACHE/$b"; done
J=$H/docs/evidence/judgement_2026-10-13/scripts
for b in $A $B $C $S; do
  (cd "$R" && $PY -c "import sys; sys.path.insert(0, '$J'); import range_test as t; t.baseline('$CACHE/$b', '$CACHE/${b}_baseline.json')") || exit 1
done
CASES=(
 "A_cube03|$A --obj 0.3,0.3,0.3 --start 150 --d0 230 --end 340"
 "A_lowbox_rail|$A --obj 0.3,0.3,0.15 --start 150 --d0 230 --end 340"
 "A_cube05|$A --obj 0.5,0.5,0.5 --start 150 --d0 230 --end 340"
 "C_cube05|$C --obj 0.5,0.5,0.5 --start 0 --d0 230"
 "D_cube05|$S --obj 0.5,0.5,0.5 --start 100 --d0 230 --end 420"
 "S_person_100|$S --obj 0.5,0.5,1.75 --start 360 --d0 100 --end 620"
 "S_person_150|$S --obj 0.5,0.5,1.75 --start 360 --d0 150 --end 620"
 "S_cube05_100|$S --obj 0.5,0.5,0.5 --start 360 --d0 100 --end 620"
 "B_person|$B --obj 0.5,0.5,1.75 --start 50 --d0 230"
 "E6_cable_low_c|$A --obj 0.05,0.05,2.6 --start 150 --d0 230 --end 340 --base 0.2"
)
one() {
  IFS='|' read -r n spec <<< "$1"; set -- $spec; bag=$1; shift
  cd "$R" || return 1
  $PY "$H/scripts/range_attrib.py" run --hooks-off --repo "$R" --out x range "$CACHE/$bag" "$ICP/icp_$bag.json" "$OUT/$n.off" "$@" > "$OUT/$n.off.log" 2>&1
  $PY "$H/scripts/range_attrib.py" run --repo "$R" --out "$OUT/$n" range "$CACHE/$bag" "$ICP/icp_$bag.json" "$OUT/$n.on" "$@" > "$OUT/$n.on.log" 2>&1
  $PY "$H/scripts/range_attrib.py" verify "$OUT/$n" "$OUT/$n.on.json" "$OUT/$n.off.json"
}
export -f one; export H R OUT CACHE ICP PY
printf '%s\n' "${CASES[@]}" | xargs -P "${JOBS:-2}" -I{} bash -c 'one "{}"'
# set O windows: one replay from frame 0 (tracker history) to the end of the later window
cd "$R" || exit 1
L=$H/labels/cloud_with_fake_obj.json; W="--window small_center:300:340 --window thin_hanging:760:790"
$PY "$H/scripts/range_attrib.py" run --hooks-off --repo "$R" --out x probe "$D/decoded/cloud_with_fake_obj" "$OUT/setO.off" --end 791 > "$OUT/setO.off.log" 2>&1
$PY "$H/scripts/range_attrib.py" run --repo "$R" --out "$OUT/setO" --labels "$L" $W probe "$D/decoded/cloud_with_fake_obj" "$OUT/setO.on" --end 791 > "$OUT/setO.on.log" 2>&1
$PY "$H/scripts/range_attrib.py" verify "$OUT/setO" "$OUT/setO.on.jsonl" "$OUT/setO.off.jsonl"
echo X1_DONE "$TAG"
