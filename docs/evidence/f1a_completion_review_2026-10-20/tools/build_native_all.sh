#!/bin/bash
# Build the native kernels (gitignored .so) once and copy the identical binary into the three scratch checkouts.
S=/tmp/claude-0/-home-user-ReSense/2f98805c-ba30-5c4f-b1a6-a591bfc61cdc/scratchpad/f1a_review
cd $S/wt_cand || exit 1
g++ -O3 -std=c++17 -ffp-contract=off -fno-fast-math -shared -fPIC -Wall -Wextra -o resense/_resense_native.so native/resense_native.cpp 2>&1 | tail -3
for w in wt_ref wt_parent; do
  cmp $S/wt_cand/native/resense_native.cpp $S/$w/native/resense_native.cpp && cp resense/_resense_native.so $S/$w/resense/_resense_native.so
done
sha256sum $S/wt_*/resense/_resense_native.so
cd $S/wt_cand && PYTHONPATH=. $S/venv/bin/python -c "from resense import _native; print(_native.status())"
