#!/bin/bash
until grep -q PROBE_DONE /data/work_k2/probe/run.log && [ -f /data/work_k2/gates/chain2.done ]; do sleep 15; done
export PATH=/home/user/venv/rs/bin:$PATH OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
python -c "import numpy; assert numpy.__version__ == '1.26.4'"
for tag in base v5b; do
  T=/data/work_k2/trees/$([ $tag = base ] && echo base || echo v5)
  export RESENSE_REPO=$T PYTHONPATH=$T:$T/ros2_ws/src/resense_ros
  REF=""; [ $tag = v5b ] && REF="--reference /data/work_k2/x3/x3_base.json"
  date -u; echo "X3 $tag $(git -C $T rev-parse HEAD)"
  (cd $T && python scripts/robustness_battery.py --repo $T --cache /data/decoded_f1 --out /data/work_k2/x3/x3_$tag.json -j 2 $REF)
  echo "X3_EXIT $tag $?"
done
date -u; echo X3_DONE
