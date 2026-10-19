#!/bin/bash
until [ -f /data/work_k2/gates/chain.done ]; do sleep 10; done
/data/work_k2/scripts/run_gate.sh /data/work_k2/trees/base v3 --set track.axis_joint_fit=true --set track.walls_smoothing_distance=1.5 > /data/work_k2/gates/v3.log 2>&1
echo DONE > /data/work_k2/gates/chain2.done
