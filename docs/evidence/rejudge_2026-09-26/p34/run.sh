#!/usr/bin/env bash
cd /home/user/ReSense
W=/tmp/claude-0/work/p34
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
for m in as_recorded roll_3 pitch_3; do
  python scripts/robustness_check.py --cache /home/user/data/cache --out $W/robust_$m.json --mount $m --jobs 4 > $W/robust_$m.log 2>&1; echo "robust $m exit $?"
done
python scripts/robustness_check.py --cache /home/user/data/cache --out $W/robust_every2.json --every 2 --jobs 4 > $W/robust_every2.log 2>&1; echo "robust every2 exit $?"
python scripts/start_offsets.py --cache /home/user/data/cache --jobs 4 --json $W/start_offsets.json > $W/start_offsets.log 2>&1; echo "offsets exit $?"
for v in "B tracking.near_escalate_voxels=8" "union gauge.axis_union=1"; do
  set -- $v
  python scripts/regression_gate.py --cache /home/user/data/cache --jobs 4 --set $2 --work $W/gate_$1 --out $W/gate_$1.json \
    --baseline docs/evidence/results/regression_baseline_2026-09-26_ride_p3d.json --allow 'ride.*' --allow 'set_F_straight.*' > $W/gate_$1.log 2>&1; echo "gate $1 exit $?"
done
echo ALL DONE
