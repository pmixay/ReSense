#!/usr/bin/env bash
# J1 on release day: every step that does not need the Docker image, behind one command, on the 1.2.0 seal.
#
#   release_day.sh <release checkout> <work dir> [--run] [step ...]
#
# Without --run it checks the identity (cheap, no data) and prints the plan; nothing else is executed. With --run it
# executes the steps in order. Steps: identity verify x3 sixbags seto ranges new ride    (default: all but ride)
#   identity  the release tree is the sealed tree: `git ls-tree -r` over the sealed paths hashes to EXPECT_TREE_SHA and
#             `detector_freeze.py verify` prints EXPECT_DIGEST (defaults: the R3 seal, main f56ad5e, 20.10)
#   verify    detector_freeze.py verify into <work>/freeze_verify.txt
#   x3        scripts/robustness_battery.py on the four decoded caches, against the sealed 1.2.0 X3 result (40 cases)
#   sixbags   judge_runner.py on the six organizer bags, then summarize_empty.py on the five obstacle-free ones
#   seto      judge_runner.py on Set O, then score_objects.py
#   ranges    prebuild_range.py: the judge's 37 range jobs
#   new       run_new_recordings.sh (synthetic, Falcon, switch, gauge) and its compare step
#   ride      stream_new_data.py (~14 GB peak disk, 1-2 h): only when named
# The Docker chain summaries wait for the release image: scripts/docker/chain.sh <image> <bag dir> <bag> <label> [play
# options] (RELEASE_DAY.md). `scores.json` and `delta.md` are written by a fresh-context agent afterwards.
#
# Environment: PY (the P4 runtime: Python 3.12, numpy 1.26.4, scipy, scikit-learn, open3d, rosbags, zstandard; one runtime
# for the whole run), DATA (root holding decoded/<bag> node-decoded caches and x1/icp/ ICP files), BAGS (folder with the six
# organizer bags and cloud_with_fake_obj as ROS2 bag folders), DATASET_ZIP (the organizers' original archive), EXPECT_TREE_SHA,
# EXPECT_DIGEST. RESENSE_REPO / PYTHONPATH / OPENBLAS_CORETYPE / OMP_NUM_THREADS are set here (P4 protocol, amendment 1).
set -u
R=$(cd "${1:?release checkout}" && pwd); W=$(mkdir -p "${2:?work dir}" && cd "$2" && pwd); shift 2
RUN=0; STEPS=()
for a in "$@"; do if [ "$a" = "--run" ]; then RUN=1; else STEPS+=("$a"); fi; done
[ ${#STEPS[@]} -eq 0 ] && STEPS=(identity verify x3 sixbags seto ranges new)
H=$(cd "$(dirname "$0")/../../.." && pwd)             # the evidence repository (tools, labels, expected values)
PY=${PY:-python3}; DATA=${DATA:-$W/data}; BAGS=${BAGS:-$W/bags}
EXPECT_TREE_SHA=${EXPECT_TREE_SHA:-014ad8fd61f1a4b6962952505cc0274c95744f476c0d8d501a9c8cbe27873e54}
EXPECT_DIGEST=${EXPECT_DIGEST:-6d091081769104657ecc2c0b06f53049647d4f6c7327b7429bbda92673782452}
J=$H/docs/evidence/rejudge_2026-10-16/scripts; E=$H/docs/evidence
export RESENSE_REPO=$R PYTHONPATH=$R:$R/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
mkdir -p "$W/logs"
log() { echo "[$(date +%H:%M:%S)] $*"; }
run() {  # echo the command; execute it only with --run
  echo "  \$ $*"
  [ "$RUN" = 1 ] || return 0
  "$@"
}
fail=0
for s in "${STEPS[@]}"; do case $s in
identity)
  log "identity: the release tree is the sealed tree"
  sha=$(cd "$R" && git ls-tree -r HEAD -- resense native configs setup.py pyproject.toml ros2_ws/src/resense_ros/config | sha256sum | cut -d' ' -f1)
  dig=$($PY "$R/scripts/detector_freeze.py" verify 2>&1 | tee "$W/freeze_verify.txt" | sed -n 's/.*source \([0-9a-f]\{64\}\).*/\1/p')
  [ "$sha" = "$EXPECT_TREE_SHA" ] && echo "  tree sha256 PASS $sha" || { echo "  tree sha256 FAIL: $sha, expected $EXPECT_TREE_SHA"; fail=1; }
  [ "$dig" = "$EXPECT_DIGEST" ] && echo "  seal digest PASS $dig" || { echo "  seal digest FAIL: '$dig', expected $EXPECT_DIGEST"; fail=1; }
  echo "  release commit $(cd "$R" && git rev-parse HEAD); record the tag, the archive SHA-256 and the image ID from the release next to this line"
  [ $fail = 0 ] || { echo "IDENTITY FAILED: this is not the sealed tree; stop (RELEASE_DAY.md)"; exit 2; } ;;
verify)
  log "verify"; run $PY "$R/scripts/detector_freeze.py" verify ;;
x3)
  log "x3: 40 cases against the sealed 1.2.0 result"
  run $PY "$R/scripts/robustness_battery.py" --repo "$R" --cache "$DATA/decoded" --out "$W/x3.json" -j 2 \
      --reference "$E/r3_completion_2026-10-20/x3-a-candidate.json" ;;
sixbags)
  log "six organizer bags"
  for b in doubleT_obstacle doubleT_platform roundT_doubleT roundT_pressureGate_roundT roundT_squareT_pressureGate_squareT squareT_platform_squareT_switch; do
    run $PY "$J/judge_runner.py" --bag "$BAGS/$b" --out "$W/judge/$b"
  done
  run $PY "$J/summarize_empty.py" "$W/judge/doubleT_platform.jsonl" "$W/judge/roundT_doubleT.jsonl" "$W/judge/roundT_pressureGate_roundT.jsonl" \
      "$W/judge/roundT_squareT_pressureGate_squareT.jsonl" "$W/judge/squareT_platform_squareT_switch.jsonl" ;;
seto)
  log "Set O"
  run $PY "$J/judge_runner.py" --bag "$BAGS/cloud_with_fake_obj" --out "$W/judge/cloud_with_fake_obj"
  run $PY "$J/score_objects.py" "$W/judge/cloud_with_fake_obj.jsonl" "$H/labels/cloud_with_fake_obj.json" "$W/judge/set_o_scores.json" ;;
ranges)
  log "ranges: 37 jobs"
  run $PY "$E/rejudge_2026-10-16/prebuild_range.py" --repo "$R" --tag 1.2.0 --data "$DATA" --out "$W/range" -j 3 ;;
new)
  log "new recordings: one command, then the committed-evidence check"
  run env PY="$PY" DATASET_ZIP="${DATASET_ZIP:-}" bash "$E/rejudge_2026-10-16/new_recordings/run_new_recordings.sh" "$R" "$W/new" ;;
ride)
  log "ride (new_data)"
  run $PY "$J/stream_new_data.py" --work "$W/ride_work" --out "$W/ride" ;;
*) echo "unknown step $s"; exit 1 ;;
esac; done
[ "$RUN" = 1 ] || echo "(plan only: add --run to execute; the Docker steps wait for the image)"
log "done"
