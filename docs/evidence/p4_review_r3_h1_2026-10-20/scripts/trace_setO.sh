#!/bin/bash
# Read-only switch trace of set O (default config) on the gate's own replay.
W=/home/user/wt_ship
export PATH=/home/user/venv/rs/bin:$PATH OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 RESENSE_REPO=$W PYTHONPATH=$W
cd $W && python /home/user/p4r/scripts/switch_trace.py /home/user/data/cache /home/user/p4r/trace_setO --names cloud_with_fake_obj --jobs 1
echo "exit $?"
