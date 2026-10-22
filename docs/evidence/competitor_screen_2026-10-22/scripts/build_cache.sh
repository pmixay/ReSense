#!/usr/bin/env bash
# one bag at a time: unpack -> int16 cache with stamps -> delete the raw bag (disk allowance is ~26 GB)
set -uo pipefail
SP=${SCRATCH:?set SCRATCH to a work directory}
REPO=/home/user/ReSense
export PYTHONPATH=$REPO RESENSE_REPO=$REPO OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
PY=$SP/venv/bin/python
for bag in doubleT_obstacle doubleT_platform roundT_doubleT roundT_pressureGate_roundT roundT_squareT_pressureGate_squareT squareT_platform_squareT_switch; do
  if [ -f $SP/cache/$bag/.done ]; then echo "$bag: cached already"; continue; fi
  echo "== $bag unpack $(date +%T)"
  $PY $REPO/scripts/unpack_dataset.py $SP/data/dataset.zip --out $SP/data --only $bag || { echo "FAIL unpack $bag"; continue; }
  echo "== $bag cache $(date +%T)"
  mkdir -p $SP/cache/$bag
  $PY $REPO/scripts/cache_frames.py $SP/data/for_hackathon/$bag $SP/cache/$bag --every 1 --int16 --stamps && touch $SP/cache/$bag/.done || echo "FAIL cache $bag"
  rm -rf $SP/data/for_hackathon/$bag
  echo "== $bag done $(date +%T) frames=$(ls $SP/cache/$bag/*.npy 2>/dev/null | wc -l) size=$(du -sh $SP/cache/$bag | cut -f1)"
done
echo ALL_DONE
