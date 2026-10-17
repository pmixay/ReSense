#!/bin/bash
# usage: synth_probe.sh <tag> <checkout> <bag>
T=$1; R=$2; B=$3; D=/home/user/rs-data
cd $R && RESENSE_REPO=$R PYTHONPATH=$R:$R/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 \
  /home/user/rs-py310/bin/python /home/user/ReSense/docs/evidence/rejudge_2026-10-16/scripts/probe.py \
  $D/decoded/$B $D/synth_runs/${T}_$B > $D/synth_runs/${T}_$B.log 2>&1
echo "$T $B exit=$?"
