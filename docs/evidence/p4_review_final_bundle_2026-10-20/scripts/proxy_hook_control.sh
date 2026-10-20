#!/bin/sh
# tests/test_lidar_proxy_hook.py::test_child_process_inherits_hook_and_bad_source_fails_closed:
# the child interpreter gets PYTHONPATH=<hook dir> only, so `resense` must be installed in that interpreter.
# A: resense reachable only through PYTHONPATH of the parent (how the R3 runs were made)  -> the test fails
# B: resense installed in the interpreter (a .pth file; an editable install does the same)  -> the test passes
# Run from the checkout.
set -e
SP=$(python3 -c "import site;print(site.getsitepackages()[0])")
echo "== A: PYTHONPATH only"
PYTHONPATH=$PWD python3 -m pytest -q tests/test_lidar_proxy_hook.py -p no:cacheprovider 2>&1 | tail -3 || true
echo "== B: installed in the interpreter"
echo "$PWD" > "$SP/zz_resense_control.pth"
env -u PYTHONPATH python3 -m pytest -q tests/test_lidar_proxy_hook.py -p no:cacheprovider 2>&1 | tail -2
rm -f "$SP/zz_resense_control.pth"
