#!/usr/bin/env bash
# Dynamic / shape probes (8.1, 8.4) on the straight segment A. Waits for the main matrix.
cd "$(dirname "$0")/.." || exit 1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
source /tmp/claude-0/venv/bin/activate

C=/tmp/claude-0/judge_data/cache; A="$C/roundT_squareT_pressureGate_squareT out/icp_roundT_squareT_pressureGate_squareT.json"
L=(
 "E1_cross150|$A --obj 0.5,0.5,1.75 --start 150 --d0 150 --end 340 --lat -4 --vy 1.0"
 "E2_cross80|$A --obj 0.5,0.5,1.75 --start 220 --d0 80 --end 340 --lat -3 --vy 1.0"
 "E3_recede8|$A --obj 0.6,0.6,1.0 --start 230 --d0 100 --end 340 --vx 8"
 "E3_recede5|$A --obj 0.6,0.6,1.0 --start 230 --d0 100 --end 340 --vx 5"
 "E4_appear60|$A --obj 0.5,0.5,1.75 --start 150 --d0 230 --end 340 --appear 60"
 "E4_appear100|$A --obj 0.5,0.5,1.75 --start 150 --d0 230 --end 340 --appear 100"
 "E5_pole_side|$A --obj 0.3,0.3,2.8 --start 150 --d0 230 --end 340 --lat 0.7"
 "E5_pole_c|$A --obj 0.3,0.3,2.8 --start 150 --d0 230 --end 340"
 "E6_cable_low_c|$A --obj 0.05,0.05,2.6 --start 150 --d0 230 --end 340 --base 0.2"
)
one() { IFS='|' read -r n args <<< "$1"; [ -s out/range2/$n.json ] && return; python scripts/range_test.py $args > out/range2/$n.log 2>&1 || true; }
# range_test takes <cache> <icp> <out> first: rebuild the argument order
one() { IFS='|' read -r n args <<< "$1"; set -- $args; [ -s out/range2/$n.json ] && return; python scripts/range_test.py "$1" "$2" out/range2/$n "${@:3}" > out/range2/$n.log 2>&1 || true; }
export -f one
printf '%s\n' "${L[@]}" | xargs -P 3 -I{} bash -c 'one "{}"'
echo ALL_EXTRA_DONE
