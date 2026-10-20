# F1a publication and main synchronization — 20 October 2026

The user explicitly requested committing, pushing to GitHub, recording the
results there and resolving conflicts. This authorizes publication of the
measured repair; it does not turn the starting-main ride gate failure into a
PASS or claim independent P4 acceptance.

* Author implementation / full evidence: `f07f4b8`.
* Fetched remote main: `2a58369`, containing PR #43 (`8c2bf51`) and evidence
  lint configuration. K2 v5c is off by default.
* Combined source: `060bde786a57c30af350ac34be4fc41ef05f3120`.
* Merge: Git's `ort` three-way merge preserved both F1a and K2 changes in the
  shared detector/configuration files. No textual conflict occurred; the
  unmerged-path inventory is empty. The combined diff was inspected.

## Verification of the combined source

Command, with `RESENSE_REPO=/home/aiops/resense`,
`LD_LIBRARY_PATH=/tmp/opencode/resense-b4-libs/usr/lib/x86_64-linux-gnu`,
`RESENSE_REQUIRE_SYNTHETIC=1`, `OPENBLAS_CORETYPE=Haswell`,
`OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`:

```sh
/tmp/opencode/resense-b4-venv/bin/python -m pytest -q \
  tests/test_f1a_b1.py tests/test_f1_false_alarms.py \
  tests/test_low_height_keep.py tests/test_lowobj_near.py \
  tests/test_low_local_support.py tests/test_rail_start.py \
  tests/test_late_candidates.py tests/test_k1_k2_axis.py \
  --junitxml=/tmp/opencode/f1a-b1-publication-merged-tests.xml
```

Result: **219 passed, 1 external-data deselection, no skips**, exit0,
122.09 seconds. The deselected test requires `/data/cache/new_data` literally;
the complete earlier data runs use the available cache in `/tmp/opencode`.
XML SHA-256:
`6040ad81c03e5468de1962b8c49873a9b634f8f4cfb7aebca7b89ddcc8b3a0f5`.

Additional checks: affected Python files pass Ruff; both YAML parameter copies
are in sync; `git diff --check` passes. No detector edits were made during
these checks.

The complete gate, whole Falcon and 40-case author X3 in `README.md` measured
the archived pre-merge author source, not this later combined source. They
were not rerun after incorporating PR #43. Final combined-source data
acceptance, independent review and reseal remain pending. The two failed
starting-main ride metrics and the three failures of the earlier full pytest
run are retained in the report and raw evidence.
