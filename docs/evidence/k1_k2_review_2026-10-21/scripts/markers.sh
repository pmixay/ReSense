#!/bin/bash
# one marked bag at a time: unpack, replay control / cand (+ v5c-15 on tunnels: positive control), delete
set -u
. /opt/venv/bin/activate; export OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
O=/data/acc/markers; mkdir -p $O; S=/home/user/ReSense/docs/evidence/k1_k2_2026-10-21/scripts
V5C="--set track.axis_joint_fit=true --set track.axis_joint_range=false --set track.axis_joint_min_curvature=0.0001 --set track.axis_joint_reach_cap=true --set track.axis_joint_reach_dual=15.0"
for b in tunnels platform switch; do
  bag=synthetic_${b}_cloud_with_markers
  [ -s $O/cand_$b.jsonl ] && continue
  python /home/user/ReSense/scripts/unpack_dataset.py /data/markers.zst --out /data/mbags --only $bag
  bd=$(find /data/mbags -maxdepth 3 -type d -name $bag | head -1); echo "bag dir $bd"; du -sh $bd
  for t in control:/opt/base cand:/opt/cand3; do
    n=${t%%:*}; r=${t#*:}
    (cd $r; RESENSE_REPO=$r PYTHONPATH=$r:$r/ros2_ws/src/resense_ros python $S/judge_runner_set.py --bag $bd --out $O/${n}_$b > $O/${n}_$b.log 2>&1) &
  done
  if [ $b = tunnels ]; then
    (cd /opt/base; RESENSE_REPO=/opt/base PYTHONPATH=/opt/base:/opt/base/ros2_ws/src/resense_ros python $S/judge_runner_set.py --bag $bd --out $O/v5c_$b $V5C > $O/v5c_$b.log 2>&1) &
  fi
  wait
  rm -rf /data/mbags; df -h / | tail -1
done
echo MARKERS_DONE
