#!/bin/bash
# The new recordings of 16-18.10 on a detector checkout, then a check against the pre-release values.
#
#   run_new_recordings.sh <checkout R> <work dir> [step ...]      steps: verify synth score falcon switch gauge compare
#
# Environment (all optional): PY (python with numpy 1.26 / scipy / sklearn / open3d / rosbags / zstandard, default
# python3), DECODED (decoded caches, default <work>/decoded), DATASET_ZIP (the organizers' original archive, for the
# six bags; default: none, then the gauge step skips them), LINK (the organizers' Yandex Disk folder).
# Needs: ~13 GB peak disk for "switch" (Pandar bag + Falcon prefix), ~8 GB for decoded caches. Runtime ~1.5 h.
set -u
R=$(cd "$1" && pwd); W=$(mkdir -p "$2" && cd "$2" && pwd); shift 2
STEPS=${*:-verify synth score falcon switch gauge compare}
H=$(cd "$(dirname "$0")/../../../.." && pwd)                  # the evidence repository (tools, labels, expected values)
PY=${PY:-python3}; DECODED=${DECODED:-$W/decoded}; LINK=${LINK:-https://disk.yandex.ru/d/SfBeRHbs8bNJAQ}
J=$H/docs/evidence/judgement_2026-10-13/scripts; EV=$H/docs/evidence
export RESENSE_REPO=$R PYTHONPATH=$R:$R/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
mkdir -p "$DECODED" "$W/logs"; cd "$R" || exit 1
log() { echo "[$(date +%H:%M:%S)] $*"; }
decode() {  # <bag dir> <name>: node-decoded cache, once; it must hold every point-cloud message of the bag
  [ -f "$DECODED/$2/meta.json" ] && return 0
  $PY "$J/cache_decoded.py" "$1" "$DECODED/$2" > "$W/logs/decode_$2.log" 2>&1
  $PY - "$1/metadata.yaml" "$DECODED/$2/meta.json" <<'PYEOF' || { rm -rf "${DECODED:?}/$2"; echo "FATAL: $2 incomplete"; exit 3; }
import json, re, sys
y = open(sys.argv[1]).read()
counts = [int(m) for m in re.findall(r"message_count: (\d+)", y)]
got = len(json.load(open(sys.argv[2])))
print(f"decoded {got} frames; metadata message counts {counts}")
sys.exit(0 if got in counts else 1)
PYEOF
}
unpack() {  # unpack_dataset.py arguments...: up to three tries, each from a clean output folder
  local out=${@: -1} k
  for k in 1 2 3; do
    rm -rf "$out"; $PY -I "$H/scripts/unpack_dataset.py" "$@" > "$W/logs/unpack_$(basename "$out")_$k.log" 2>&1 && return 0
    log "unpack try $k failed (see logs)"
  done
  echo "FATAL: unpack failed three times: $*"; exit 3
}
for s in $STEPS; do case $s in
verify)
  log "detector_freeze verify"; $PY "$R/scripts/detector_freeze.py" verify | tee "$W/freeze_verify.txt" | tail -2 ;;
synth)
  for b in synthetic_platform synthetic_switch synthetic_tunnels; do
    if [ ! -f "$DECODED/$b/meta.json" ]; then
      [ -f "$W/raw_synth/.complete" ] || { unpack "$LINK" --member new_synth_data.zst --out "$W/raw_synth"
                                           touch "$W/raw_synth/.complete"; }
      decode "$W/raw_synth/${b}_cloud_only" "$b" && rm -rf "$W/raw_synth/${b}_cloud_only"
    fi
    log "synthetic $b"; $PY "$J/probe.py" "$DECODED/$b" "$W/synth_$b" > "$W/logs/synth_$b.log" 2>&1
  done ;;
score)
  log "score synthetic_platform 0-314"
  $PY "$EV/synthetic_labels_2026-10-17/scripts/score_platform.py" "$W/synth_synthetic_platform.jsonl" \
    "$EV/synthetic_labels_2026-10-17/labels_synthetic_platform_0-314.json" "$W/score_platform.json" ;;
falcon)
  log "Falcon whole recording (streamed)"
  $PY "$H/scripts/stream_falcon.py" "$LINK" --out "$W/falcon_full" > "$W/logs/falcon_full.log" 2>&1
  tar -xJf "$EV/extended_data_2026-10-17/runs_raw.tar.xz" -C "$W" runs/falcon_prefix.jsonl runs/falcon_window.jsonl
  $PY "$EV/falcon_full_2026-10-18/check_b2.py" "$W/falcon_full.jsonl" "$W/runs/falcon_prefix.jsonl" \
    "$W/runs/falcon_window.jsonl" "$W/falcon_check.json" > /dev/null ;;
switch)
  X=$EV/extended_data_2026-10-17/scripts
  if [ ! -f "$W/falcon_prefix/falcon_prefix.db3" ]; then
    log "Falcon prefix (first 4.5 GB)"
    HREF=$($PY -c "import sys; sys.path.insert(0, '$H/scripts'); from unpack_dataset import resolve_yadisk; print(resolve_yadisk('$LINK', 'falcon_test.zst'))" 2>/dev/null)
    curl -sSL "$HREF" | $PY -I "$X/zst_tar_stdin.py" --out "$W/falcon_raw" --only metadata.yaml,falcon_test_second_dark_0.db3 \
      --max-bytes 4500000000 --stop-after 2 > "$W/logs/falcon_raw.log" 2>&1
    mkdir -p "$W/falcon_prefix"
    $PY -I "$X/prefix_bag.py" "$(find "$W/falcon_raw" -name falcon_test_second_dark_0.db3)" "$W/falcon_prefix/falcon_prefix.db3" \
      > "$W/logs/prefix.log" 2>&1 && rm -rf "$W/falcon_raw"
  fi
  if [ ! -d "$W/pandar/for_hackathon/doubleT_obstacle" ]; then
    log "doubleT_obstacle from \$DATASET_ZIP"
    unpack "${DATASET_ZIP:?set DATASET_ZIP to the organizers archive}" --only doubleT_obstacle --out "$W/pandar"
  fi
  log "switch runs"; PY=$PY "$EV/falcon_switch_2026-10-18/run_b3.sh" new "$R" "$W/switch" \
    "$W/pandar/for_hackathon/doubleT_obstacle" "$W/falcon_prefix" > "$W/logs/switch.log" 2>&1
  $PY "$EV/falcon_switch_2026-10-18/compare_b3.py" "$W/switch" "$W/switch/compare.json" > /dev/null ;;
gauge)
  mkdir -p "$W/gauge"; tar -xJf "$EV/gauge_stability_2026-10-18/b6_raw.tar.xz" -C "$W/gauge" --wildcards 'poses_*'
  for b in doubleT_obstacle doubleT_platform roundT_doubleT roundT_pressureGate_roundT roundT_squareT_pressureGate_squareT \
           squareT_platform_squareT_switch cloud_with_fake_obj synthetic_platform synthetic_switch synthetic_tunnels; do
    if [ ! -f "$DECODED/$b/meta.json" ]; then               # decode one bag at a time, then delete the raw bag
      if [ "$b" = cloud_with_fake_obj ]; then
        unpack "$LINK" --member cloud_with_fake_obj.zst --out "$W/raw_bag"
      elif [ -n "${DATASET_ZIP:-}" ] && [ "${b#synthetic}" = "$b" ]; then
        unpack "$DATASET_ZIP" --only "$b" --out "$W/raw_bag"
      fi
      SRC=$(find "$W/raw_bag" -name metadata.yaml -path "*$b*" 2>/dev/null | head -1)
      [ -n "$SRC" ] && decode "$(dirname "$SRC")" "$b"; rm -rf "$W/raw_bag"
    fi
    if [ ! -f "$DECODED/$b/meta.json" ]; then log "gauge: no decoded cache for $b, skipped"; continue; fi
    log "gauge $b"
    $PY "$H/scripts/gauge_stability.py" track "$DECODED/$b" "$W/gauge/track_$b.json" > /dev/null
    $PY "$H/scripts/gauge_stability.py" measure "$W/gauge/track_$b.json" "$W/gauge/poses_$b.json" "$W/gauge/measure_$b.json" > /dev/null
    [ -f "$W/gauge/run_$b.jsonl" ] || $PY "$J/probe.py" "$DECODED/$b" "$W/gauge/run_$b" > /dev/null 2>&1
    [ "$b" = doubleT_obstacle ] || $PY "$H/scripts/gauge_stability.py" honesty "$W/gauge/track_$b.json" \
      "$W/gauge/poses_$b.json" "$W/gauge/run_$b.jsonl" "$W/gauge/honesty_$b.json" > /dev/null
  done ;;
compare)
  $PY "$EV/rejudge_2026-10-16/new_recordings/compare_new_recordings.py" "$W" | tee "$W/compare.txt" ;;
*) echo "unknown step $s"; exit 2 ;;
esac; done
