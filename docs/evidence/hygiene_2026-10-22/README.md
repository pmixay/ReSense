# Scripts and paths hygiene, 22.10.2026

Lane: scripts-and-paths hygiene, branch `claude/hygiene-scripts-1.3`, base `f24d939`.
Scope kept to `scripts/`, `tests/` and `scripts/README.md`; no detector code, no `docs/evidence/**` of
other dates, no captain files. `check_archived_lint.py` (ruff 0.15.8) PASS and `detector_freeze.py verify`
PASS (42 files) before each push.

## 1. Scripts nothing refers to

Method: one `rg` pass over every tracked file for each of the 143 names in `scripts/` (name with
extension, `scripts.<stem>`, `scripts/<stem>`), json manifests and sha lists not counted as mentions
(they only list every file). A script counts as unreferenced when no test, CI file, Dockerfile, other
script or **live** doc (not `docs/evidence`, not `docs/archive`) names it. Result: **24** (the earlier
"about 19" probably counted differently; `cache_to_bag` is named without extension in `docs/CAPTAIN.md`).
No positive control was run for this sweep beyond the 119 other files being found referenced; the
count of 24 is therefore a stated-definition result, not an independent one.

For each: origin by `git log --follow` (18 first appear in the 1.1.0 integration `44b462e`, 2 in
`d9603e0`, and one each in `e9d8fc6`, `ddf5b63`, `3486ad9`, `f671a62`); purpose from its docstring; evidence link in
[`scripts/README.md`](../../../scripts/README.md).

Runs on 1.3.0:

* `--help` from a directory outside the repository, venv with `pip install -e ".[dev]"`: 22 of 23
  Python scripts print `usage:` (checked on the output text, not only the exit code; the test also fails a
  script that imports a missing module and one that ignores `--help`). `p2_draft_deck.py` needs
  `python-pptx` (extra `presentation`): without it the only error is that import and the file compiles.
* All 85 names the 24 scripts import from `resense` / `scripts` exist (AST walk, positive control: a
  nonsense name is reported missing).
* Small real inputs, synthetic-tunnel frames from `resense.synthetic` (30 frames, then 130 for
  `mount_survey`): `mount_survey`, `robustness_check`, `speed_timing`, `startup_census`,
  `start_offsets` run to the end. Their outputs are all-zero alarms and a constant mount, as a clean
  synthetic tunnel should give; they show the code path works, not any measurement. `mount_survey`
  crashes on fewer samples than its longest window (30 frames at `--every 5`): that is short input, not
  a regression, left as is.
* Not run beyond `--help`: `bench_health_histogram`, `check_synth_labels`, `compare_history_stress`,
  `dust_battery`, `lying_person_eval`, `ml_second_opinion`, `orientation_battery` (needs the judge's
  helpers), `p4_*_intake`, `render_false_targets`, `speed_setf`, `speed_static_check`,
  `summarize_*`, `track_opinion_pipeline` (all need recordings or reports not in this container).
  **Unverified** beyond start-up and imports.

Finished:

* Index with purpose, evidence link and coverage: `scripts/README.md`.
* Tests, `tests/test_unreferenced_scripts.py`: `--help` of all 23 Python tools, index completeness,
  `run_offline.sh` with a stub CLI, `consistency_check.py` on built run folders (event counts, alarm
  frames, summary line), `cache_to_bag.py` round trip (frames, stamps, topic, frame_id, point layout,
  empty dual-return slots, quantised coordinates, intensity, ring).
* Fix: `cache_to_bag.py` found no frames in `--zstd` caches (`*.npy` glob only; `IndexError`).
  Reproduced by the test first (`npy.zst` failed, `npy` passed), then fixed with
  `scripts/cache_io.py` (`cache_files`, `load_cache_array`, `cache_file_stem`). Check: the bag from the
  old script and from the new one on the same plain cache are identical row by row (timestamps and
  CDR bytes, 3 of 3 messages), and the new script on the zstd copy of that cache gives the same bytes.
  Left unchanged: `mount_survey`, `robustness_check`, `speed_setf`, `speed_timing` glob `*.npy` only;
  their documented caches (`/data/cache/<bag>`) are plain.
* Nothing removed: no exact duplicate; `lying_person_eval.py` wraps `far_range_eval.py` (different
  file, 48 vs 479 lines, registers the lying objects); no tool is superseded.

## 2. Personal Windows paths

Found with `[CD]:/(Users|Datasets)` outside `docs/evidence`: `analyze_local_body_support.py` (2),
`analyze_residual_events.py` (1), `test_evidence_coherence.py` (2), `test_far_structure.py` (1, docstring),
and one more: `test_fresh_support_analysis.py`. (`docs/EXPERIMENT_*`, `RESIDUAL_EVENTS`, `archive/**`
keep their dated commands.)

Mechanism reused, not invented: recorded data is under `$RESENSE_CACHE` (default `/data/cache`, as in
`scripts/bench_8core.sh`) and a test needing it carries `@pytest.mark.realdata(path)` (`tests/conftest.py`),
as `test_rail_start.py` does with its own `RESENSE_RIDE_CACHE`. `scripts/analyze_residual_events.py`
defines `CACHE` and `MEASUREMENT`; the others import them. The positive-stress and direct-capture
folders are `$RESENSE_CACHE/fresh-stop-positive-stress` and `$RESENSE_CACHE/direct-fresh-support-all`.
The analysis script's output root `TEMP` is `tempfile.gettempdir()`.

Proof (`tests/test_data_paths.py`, subprocess `pytest --collect-only`):

* data absent: 15 of 22 tests in the two files collected, **7 deselected**, the summary names each with
  the missing path;
* data present (empty stub folders for the three paths): all 22 collected, including the 3 that need the
  data. The stubs prove selection only; the data-dependent assertions themselves were **not run**,
  the real measurement data is not in this container.
* no personal path in `scripts tests resense native configs ros2_ws webapp web docker` (scan with a
  positive control), and the default and the override of `RESENSE_CACHE` reach the scripts and tests.

## 3. `test_rail_start.py::test_finding_rail_heads_ahead_of_a_standing_fresh_start_do_not_stop`

**Not done.** The ride cache (`/data/cache/new_data`) needs `Датасет.zip`; the download was refused by
the session's permission classifier and not retried by other means. Without the data the cause cannot
be named. What the repository shows (no run): the test is recorded as passing on 26.09 and 28.09
(`freeze_2026-09-26/pytest_final.xml`, `cycle_2026-09-28/tooling/junit_ride.xml`), was edited on 19.10
(`0acb18c`, the `f1` run and its assertion added), and failed first on 1.2.0 (`track_opinion_2026-10-21`,
`integration_1.3_2026-10-21`); no log of the failing assertion is committed. Which of its four
assertions fails, and whether the expectation or the detector moved, is **unverified**.

## Verification of the suite

See the end of this file (filled in after the final run).
