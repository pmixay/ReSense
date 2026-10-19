#!/bin/bash
# wait for the base gate, then run v5a, v5b, off5 (v5 tree) and v4 (base tree) one after another
until grep -q GATE_EXIT /data/work_k2/gates/base.log; do sleep 10; done
S=/data/work_k2/scripts/run_gate.sh
V4="--set track.axis_joint_fit=true --set track.axis_joint_range=false --set track.walls_smoothing_distance=1.5"
$S /data/work_k2/trees/v5 v5a $V4 --set track.axis_joint_min_curvature=0.0001 > /data/work_k2/gates/v5a.log 2>&1
$S /data/work_k2/trees/v5 v5b $V4 --set track.axis_joint_min_curvature=0.0001 --set track.axis_joint_reach_cap=true > /data/work_k2/gates/v5b.log 2>&1
$S /data/work_k2/trees/v5 off5 > /data/work_k2/gates/off5.log 2>&1
$S /data/work_k2/trees/base v4 $V4 > /data/work_k2/gates/v4.log 2>&1
echo CHAIN_DONE >> /data/work_k2/gates/chain.done
