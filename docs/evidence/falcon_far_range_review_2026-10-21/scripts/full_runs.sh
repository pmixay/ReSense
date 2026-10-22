#!/bin/bash
# full-recording replays with the author's run_far.py (read from the review checkout), each checkout via RESENSE_REPO
F=/home/user/ReSense/docs/evidence/falcon_far_range_2026-10-21/scripts
O=/home/user/rv/full; mkdir -p $O
run() {  # name repo args...
  local name=$1 repo=$2; shift 2
  ( . /home/user/venv/bin/activate; export RESENSE_REPO=$repo PYTHONPATH=$repo:$repo/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
    python -c "import resense;print('$name', resense.__file__)"
    python $F/run_far.py --cache /home/user/data/falcon --profile falcon_ros --out $O/$name "$@" ) > $O/$name.log 2>&1
}
run base /home/user/wt_v120 &
run cand /home/user/wt_cand --trace &
run pc1910 /home/user/wt_v120 --pre farrange.with_falcon_profile=true &
wait
run c89 /home/user/wt_cand --pre farrange.axis_stable=false &
run cand_plain /home/user/wt_cand &
wait
echo FULLDONE
