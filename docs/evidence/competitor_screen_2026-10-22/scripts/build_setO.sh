#!/usr/bin/env bash
set -uo pipefail
SP=${SCRATCH:?set SCRATCH to a work directory}; REPO=/home/user/ReSense
export PYTHONPATH=$REPO RESENSE_REPO=$REPO OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
PY=$SP/venv/bin/python
echo "== setO unpack $(date +%T)"
$PY $REPO/scripts/unpack_dataset.py https://disk.yandex.ru/d/KpkG_yKoGk-vHQ --out $SP/data || { echo FAIL_UNPACK; exit 1; }
ls -la $SP/data/cloud_with_fake_obj
echo "== setO cache $(date +%T)"
mkdir -p $SP/cache/cloud_with_fake_obj
$PY $REPO/scripts/cache_frames.py $SP/data/cloud_with_fake_obj $SP/cache/cloud_with_fake_obj --every 1 --int16 --stamps && touch $SP/cache/cloud_with_fake_obj/.done || echo FAIL_CACHE
echo "== setO done $(date +%T) frames=$(ls $SP/cache/cloud_with_fake_obj/*.npy | wc -l) size=$(du -sh $SP/cache/cloud_with_fake_obj | cut -f1)"
echo ALL_DONE
