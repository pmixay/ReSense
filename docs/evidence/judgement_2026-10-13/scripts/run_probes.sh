#!/usr/bin/env bash
# Robustness probe matrix (8.4). Outputs out/probe/<cache>__<variant>.jsonl
cd "$(dirname "$0")/.." || exit 1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
source /tmp/claude-0/venv/bin/activate
C=/tmp/claude-0/judge_data/cache
L=()
for v in "base:" "pitch+2:--pitch 2" "pitch-2:--pitch -2" "roll+2:--roll 2" "yaw+3:--yaw 3" "drop30:--drop 0.3" "drop50:--drop 0.5" "dedup:--dedup" "5Hz:--every 2" "noise2cm:--noise 0.02"; do
  L+=("doubleT_obstacle|$v"); done
for v in "base:" "pitch+2:--pitch 2" "drop30:--drop 0.3" "dedup:--dedup" "5Hz:--every 2"; do L+=("cloud_with_fake_obj|$v"); done
for b in roundT_squareT_pressureGate_squareT squareT_platform_squareT_switch; do
  for v in "base:" "pitch+2:--pitch 2" "pitch-2:--pitch -2" "roll+2:--roll 2" "drop30:--drop 0.3" "dedup:--dedup" "5Hz:--every 2"; do L+=("$b|$v"); done
done
one() { IFS='|' read -r b v <<< "$1"; name=${v%%:*}; args=${v#*:}; out=out/probe/${b}__${name};
        [ -s $out.jsonl ] && return; python scripts/probe.py /tmp/claude-0/judge_data/cache/$b $out $args > $out.log 2>&1; }
export -f one
printf '%s\n' "${L[@]}" | xargs -P 2 -I{} bash -c 'one "{}"'
echo ALL_PROBES_DONE
