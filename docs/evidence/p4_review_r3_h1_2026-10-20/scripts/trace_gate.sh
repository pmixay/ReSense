#!/bin/bash
# Read-only switch trace of the whole gate (six recordings, set O, the ride in 8 pieces), default config, the gate's
# own replay (eval_real.run_piece). Its .jsonl rows must equal the shipped gate rows (cmp_frames.py).
W=/home/user/wt_ship
export PATH=/home/user/venv/rs/bin:$PATH OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 RESENSE_REPO=$W PYTHONPATH=$W
cd $W && python /home/user/p4r/scripts/switch_trace.py /home/user/data/cache /home/user/p4r/trace_gate \
  --names doubleT_obstacle,doubleT_platform,roundT_doubleT,roundT_pressureGate_roundT,roundT_squareT_pressureGate_squareT,squareT_platform_squareT_switch,cloud_with_fake_obj,new_data --jobs 4
echo "exit $?"
