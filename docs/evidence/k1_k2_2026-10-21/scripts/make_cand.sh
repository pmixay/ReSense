#!/bin/bash
# make_cand.sh <commit> <dir>: detached worktree of <commit> with the K2 union candidate switched on in BOTH YAML
# copies (nothing else changed), committed locally (X3 needs a clean committed tree), native kernels built.
set -eu
C=$1; D=$2; R=/home/user/ReSense
git -C $R worktree add --detach "$D" "$C"
cd "$D"
for f in configs/default.yaml ros2_ws/src/resense_ros/config/detector.yaml; do
  sed -i -E 's/^(\s+)axis_joint_fit: false/\1axis_joint_fit: true/; s/^(\s+)axis_joint_range: true/\1axis_joint_range: false/;
             s/^(\s+)axis_joint_min_curvature: 0\.0 /\1axis_joint_min_curvature: 0.0001 /; s/^(\s+)axis_joint_union: false/\1axis_joint_union: true/' $f
done
git diff --stat
python -c "
from resense.config import DetectorConfig as D
for p in ('configs/default.yaml','ros2_ws/src/resense_ros/config/detector.yaml'):
    t=D.from_yaml(p).track; assert (t.axis_joint_fit,t.axis_joint_range,t.axis_joint_min_curvature,t.axis_joint_union)==(True,False,1e-4,True),p
print('candidate switches on in both YAMLs')"
git -c user.name=eval -c user.email=eval@local commit -qam "evaluation tree: K2 union candidate switched on (not for merge)"
bash scripts/build_native.sh | tail -1
git log --oneline -1
