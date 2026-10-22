#!/bin/bash
# One measuring run on one side, with a receipt (command, commit, clean-tree check, resense path, exit code, times).
#   run_check.sh <side: control|cand> <phase: gate|falcon|x3|physical|ride|affected|full> <out dir> [x3 reference]
# control = detached worktree of v1.2.0 (3b73bbe), cand = detached worktree of the measured branch commit.
set -u
side=$1; phase=$2; out=$3; ref=${4:-}
W=/home/user/wt/$side
E=$W/docs/evidence
export RESENSE_REPO=$W PYTHONPATH=$W:$W/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 \
       OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
. /home/user/venv/bin/activate
mkdir -p "$out"
name=$phase-$side
cd "$W"
case $phase in
  gate) cmd=(python scripts/regression_gate.py --cache /data/cache --jobs 2
             --baseline docs/evidence/results/regression_baseline_2026-09-29_shell_off.json
             --out "$out/$name.json" --work "$out/$name-work") ;;
  falcon) cmd=(python $E/falcon_long_range_2026-10-19/scripts/run_cache.py --cache /data/falcon_full
               --profile falcon_ros --out "$out/$name") ;;
  x3) cmd=(python scripts/robustness_battery.py --repo "$W" --cache /data/decoded --out "$out/$name.json" -j 2)
      [ -n "$ref" ] && cmd+=(--reference "$ref") ;;
  physical) cmd=(env PYTHONPATH=$W:$W/ros2_ws/src/resense_ros:$E/f1a_b1_2026-10-20
                 python $E/f1a_b1_2026-10-20/physical.py --out "$out/$name.json") ;;
  ride) cmd=(python $E/f1_false_alarms_2026-10-19/scripts/replay.py --cache /data/cache --bag new_data
             --out "$out/$name" --full) ;;
  affected) cmd=(python -m pytest -q -p no:cacheprovider --junitxml "$out/$name.xml" tests/test_f1a_b1.py
                 tests/test_f1_false_alarms.py tests/test_low_height_keep.py tests/test_lowobj_near.py
                 tests/test_low_local_support.py tests/test_rail_start.py tests/test_modules.py tests/test_core.py
                 tests/test_algorithm.py tests/test_native.py tests/test_cable_current_support.py
                 tests/test_cable_confirmation.py tests/test_ego_veto.py tests/test_explained_run.py)
            [ -f tests/test_f1a_bounded.py ] && cmd+=(tests/test_f1a_bounded.py) ;;
  full) cmd=(python -m pytest -q -p no:cacheprovider --junitxml "$out/$name.xml" tests) ;;
esac
start=$(date -u +%FT%TZ)
head=$(git rev-parse HEAD); dirty=$(git status --porcelain --untracked-files=no | wc -l)
rpath=$(python -c "import resense; print(resense.__file__)")
"${cmd[@]}" > "$out/$name.log" 2>&1
rc=$?
python - "$out/$name.receipt.json" <<PY
import json, sys
json.dump({"side": "$side", "phase": "$phase", "worktree": "$W", "commit": "$head", "tracked_changes": $dirty,
           "resense": "$rpath", "command": """${cmd[*]}""", "started": "$start",
           "finished": "$(date -u +%FT%TZ)", "returncode": $rc,
           "commit_after": "$(git rev-parse HEAD)"}, open(sys.argv[1], "w"), indent=1)
PY
echo "$name rc=$rc"
