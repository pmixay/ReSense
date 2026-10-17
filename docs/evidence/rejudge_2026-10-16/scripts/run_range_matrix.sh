#!/usr/bin/env bash
# Range-test matrix (8.2). Runs 3 jobs at a time. Outputs out/range/<name>.json
cd "$(dirname "$0")/.." || exit 1
source /tmp/claude-0/venv/bin/activate
C=/tmp/claude-0/judge_data/cache
jobs_list=()
add() { jobs_list+=("$*"); }
declare -A OBJ=([person]=0.5,0.5,1.75 [cube1]=1.0,1.0,1.0 [cube05]=0.5,0.5,0.5 [cube03]=0.3,0.3,0.3)
for o in person cube1 cube05 cube03; do
  add "A_${o} $C/roundT_squareT_pressureGate_squareT out/icp_roundT_squareT_pressureGate_squareT.json --obj ${OBJ[$o]} --start 150 --d0 230 --end 340"
  add "B_${o} $C/roundT_doubleT out/icp_roundT_doubleT.json --obj ${OBJ[$o]} --start 50 --d0 230"
  add "C_${o} $C/roundT_pressureGate_roundT out/icp_roundT_pressureGate_roundT.json --obj ${OBJ[$o]} --start 0 --d0 230"
  add "D_${o} $C/squareT_platform_squareT_switch out/icp_squareT_platform_squareT_switch.json --obj ${OBJ[$o]} --start 100 --d0 230 --end 420"
done
add "A_person_latp05 $C/roundT_squareT_pressureGate_squareT out/icp_roundT_squareT_pressureGate_squareT.json --obj 0.5,0.5,1.75 --start 150 --d0 230 --end 340 --lat 0.5"
add "A_person_latm05 $C/roundT_squareT_pressureGate_squareT out/icp_roundT_squareT_pressureGate_squareT.json --obj 0.5,0.5,1.75 --start 150 --d0 230 --end 340 --lat -0.5"
add "A_person_drop $C/roundT_squareT_pressureGate_squareT out/icp_roundT_squareT_pressureGate_squareT.json --obj 0.5,0.5,1.75 --start 150 --d0 230 --end 340 --dropout"
add "A_cube05_drop $C/roundT_squareT_pressureGate_squareT out/icp_roundT_squareT_pressureGate_squareT.json --obj 0.5,0.5,0.5 --start 150 --d0 230 --end 340 --dropout"
add "A_cube1_drop $C/roundT_squareT_pressureGate_squareT out/icp_roundT_squareT_pressureGate_squareT.json --obj 1.0,1.0,1.0 --start 150 --d0 230 --end 340 --dropout"
add "A_lowbox_rail $C/roundT_squareT_pressureGate_squareT out/icp_roundT_squareT_pressureGate_squareT.json --obj 0.3,0.3,0.15 --start 150 --d0 230 --end 340"
# standing train at the platform (squareT_platform frames ~300-690 speed 0): static object at fixed distance
for d in 60 100 150; do
  add "S_person_${d} $C/squareT_platform_squareT_switch out/icp_squareT_platform_squareT_switch.json --obj 0.5,0.5,1.75 --start 360 --d0 $d --end 620"
  add "S_cube05_${d} $C/squareT_platform_squareT_switch out/icp_squareT_platform_squareT_switch.json --obj 0.5,0.5,0.5 --start 360 --d0 $d --end 620"
done
run_one() { set -- $1; name=$1; shift; [ -s out/range/$name.json ] && return; python scripts/range_test.py "$1" "$2" out/range/$name "${@:3}" > out/range/$name.log 2>&1; }
export -f run_one
printf '%s\n' "${jobs_list[@]}" | xargs -P 3 -I{} bash -c 'run_one "{}"'
echo ALL_RANGE_DONE
