#!/usr/bin/env bash
# Build the optional native kernels in place, for a source checkout used without pip
# (PYTHONPATH=.); `pip install .` / `pip install -e .` build them through setup.py.
# Same flags as setup.py: bit-identical arithmetic to the numpy code (no FMA contraction,
# no fast-math, no -march=native).
#
#   scripts/build_native.sh            # -> resense/_resense_native.so
#   RESENSE_NATIVE=0 ...               # force the numpy code at run time
set -euo pipefail
cd "$(dirname "$0")/.."
CXX="${CXX:-g++}"
"$CXX" -O3 -std=c++17 -ffp-contract=off -fno-fast-math -shared -fPIC -Wall -Wextra \
    -o resense/_resense_native.so native/resense_native.cpp
python3 -c "import sys; sys.path.insert(0, '.'); from resense import _native; print(_native.status())"
