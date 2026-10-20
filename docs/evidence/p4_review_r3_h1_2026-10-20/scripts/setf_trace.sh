#!/bin/bash
# After the gate trace finishes: set F straight (default config) under the read-only hooks; the report it writes
# must equal the shipped set F (hits, sustained values) and the trace lists every track where R3 matters.
until grep -q "^exit" /home/user/data/logs/trace_gate.log; do sleep 5; done
W=/home/user/wt_ship; O=/home/user/p4r/setf_trace; mkdir -p $O
export PATH=/home/user/venv/rs/bin:$PATH OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 RESENSE_REPO=$W PYTHONPATH=$W
cd $W && python /home/user/p4r/scripts/setf_trace.py $O/trace $O/setF_traced.json
echo "exit $?"
