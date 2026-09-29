# Branch review — `experiment/cross-ring-sparse-evidence` against `main`, 29.09

> **Purpose:** a code review of the experimental branch, what it improves over `main`, and what
> was fixed in the review.
> **Audience:** team · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-09-29: branch head `75ef4e2` plus the review commits below, against
> `main` `692820b` (merge base `059948a`) · **Status:** dated record

## Verdict

**No big gain over `main`.** The branch brings one small, real detection gain, one speed gain
whose size depends on the NumPy build, stricter input validation, and a large body of evaluation
tooling and tests. By default its node starts up less fresh than `main`'s, by design. The
opt-in change most likely to move the scores, fresh STOP-onset evidence, is off and not
validated.

| | `main` `692820b` | this branch |
|---|---|---|
| rail object on `doubleT_obstacle`, raw STOP frames after frame 75 | 123 / 126 (GO at 111, CAUTION at 117, 197) | **126 / 126** |
| person on `doubleT_obstacle` | 61 / 61 | 61 / 61 |
| ride false events / five empty recordings | unchanged | unchanged (full gate: 144 enforced rows unchanged, 2 better) |
| reserved synthetic (v2), sustained positives | — | 14 / 32 float32, 13 / 32 compact16, identical for baseline and candidate |
| detector processing p95, team laptop, NumPy 1.26 | 105.15 ms positive, 77.33 ms clear | 76.32 ms, 60.51 ms (one warm local pair) |
| start-up freshness (node) | first 3 s of results 38–105 ms old | every start-up frame processed (`catchup_startup_step` 0), so results are older while it catches up |
| tests (`pytest`) | 770 passed | 1 091 passed on the branch head, 1 100 after this review |
| reviewer scores (same rubric, paired) | — | 66 → 66 (continuation), 67 → 67.5 (health: +0.5 speed) |

Sources: [`P3_SCORE_SYNC_2026-09-28.md`](P3_SCORE_SYNC_2026-09-28.md),
[`IMPROVEMENT_CYCLE_2026-09-28.md`](IMPROVEMENT_CYCLE_2026-09-28.md),
[health histogram evidence](evidence/cycle_2026-09-28/health_histogram/README.md),
[`SCORECARD.md`](SCORECARD.md) "Experimental development reviews". The detection figures come from
the team's recorded replays; this review re-ran the test suites and the micro-benchmarks, not the
organizers' recordings (they are not in the review container).

## What the branch changes

**On by default**

1. **Bounded low-height continuation** (`tracking.stop_keep_low_s` 0.3 s,
   `lowobj.straddle_keep_height_margin` 0.03 m). A straddle cluster whose top misses the 0.10 m bar by
   at most 3 cm may continue an existing low STOP for 0.3 s of sensor time since the last clean
   hit. It never seeds a track, adds confidence or resets a clean-hit clock. It fills the three raw
   gaps of the rail object. Reviewed: association (25 cm gate, shape against the last *clean* low
   cluster, ambiguous clusters dropped), expiry through `hold_misses` and long stamp gaps, the
   reseed hold exemption, and `keep_low` provenance for the fresh-onset rule. No defect found.
2. **Health histogram** (`health._sector_counts`): binary search instead of `np.histogram`'s sort.
   Exact (fuzzed here against `np.histogram`). Its speed depends on NumPy, see finding S1.
3. **Strict PointCloud2 row layout** (`fastcloud.packed`): a payload whose length is not
   `height * row_step`, or a `row_step` shorter than a row, faults the frame instead of decoding
   padding as points. The node catches it (`on_processing_error`).
4. **Node start-up default** `catchup_startup_step` 0.2 → **0**. This keeps every frame of the
   player's start-up burst, reverting `main`'s 29.09 thinning (`main`'s A/B: 198–200 of 201 frames
   processed, 185–189 STOP frames instead of 190). The branch trades start-up freshness for not
   skipping obstacle frames. `0.2` remains available as an explicit launch argument.
5. `rosbags` ≥ 0.11 for the tools image, which could not read standalone `.db3` files.

**Opt-in, off by default** (no effect on default outputs): cross-ring sparse evidence
(`cluster.weak_min_rings`, `tracking.far_min_ring_count`), fresh STOP-onset evidence
(`tracking.fresh_stop_evidence`; the branch reports ride false events 32 → 27, not validated on
the six short recordings), and local bed/rail surface support (`lowobj.local_support_*`).

**Tooling**: the synthetic LiDAR fixture (24 clouds, 18 masks), the compressed ride cache and its
intake checks, paired history-stress and raw-replay comparisons, the registered synthetic
protocol, and +321 tests.

## Findings

### Fixed in this review

| # | finding | where | commit |
|---|---|---|---|
| R1 | A cloud **without a `ring` field** decoded to channel 0 for every point, so the node gave the detector "one known channel" instead of "unknown". With the cross-ring profile every far sparse cluster of such a sensor had `ring_count` 1 and was dropped, contradicting the detector's own contract. The node and its offline mirror now pass `ring=None` in that case. | `detector_node.py`, `fastcloud.has_field`, `replay_node_frames.py` | `84da355` |
| R2 | `selected_stamps_sha256` of set F reports was constant on the `.npy.zst` ride cache (`splitext` left `.npy`, every stamp `None`). `compare_setf` could therefore not refuse unpaired runs. | `far_range_eval.py` | `cb5b676` |
| R3 | `trace_false_targets` could not read the compressed ride cache that `cache_extended_ride` writes. | `trace_false_targets.py` | `cb5b676` |
| R4 | `quality_screen` summarised an earlier run's `history.json` / `acceptance.json` when those stages were skipped, and exited 0 after a failing gate. It now clears stage outputs and exits with the first failing stage's code. | `quality_screen.py` | `cb5b676` |
| R5 | `--reserve-gib` reserved 10⁹ bytes per unit; a duplicate ride cache stem made the gate exit 1 ("worse metric") instead of 2 (input error). | `cache_extended_ride.py`, `regression_gate.py` | `cb5b676` |
| R6 | The synthetic evaluator loaded the geometry auditor from the *detector* checkout when that checkout had one (`scripts` is a namespace package), while it recorded the observer's hash. | `synthetic_sensitivity.py` | `91b0738` |
| R7 | "No new false STOP frame" was enforced on counts only: a false STOP that moved from frame 3 to frame 12 passed. | `synthetic_sensitivity.compare_reports` | `91b0738` |
| R8 | The stage diagnosis failed on every v2 case: its parity check lacked the v2 rows' `target_returns_in_physical_envelope`. | `diagnose_synthetic_sensitivity.py` | `91b0738` |
| R9 | The low-height replay found "new" false alarms by `(frame, track id)`. One track kept alive renumbers every later track, so this both invents and hides regressions. It now matches by frame and place. | `evaluate_low_height_keep.py` | `91b0738` |
| R10 | Cross-ring measurement summaries merged STOP episodes across ride pieces, each of which runs on a fresh detector. | `analyze_cross_ring_measurement.py` | `91b0738` |

R1, R3, R4, R6, R7 and R10 have regression tests that fail on the code before the fix; R2 and R9
have tests of the new helpers. R5 and R8 are fixed by reading only: R8's parity path needs a v2
development cache.

### Not fixed: sealed detector files

`resense/`, `configs/`, `native/` and the build inputs are sealed. A change needs the full gate on
the organizers' data and a reviewed reseal ([`DETECTOR_FREEZE.md`](DETECTOR_FREEZE.md)), which this
review could not run.

**S1 — the health histogram's speed-up depends on NumPy, and it is slower than `main` on NumPy 2.**
`np.histogram` with explicit edges sorts the data. Only NumPy 1.x without AVX-512 sorts slowly;
the team laptop (i7-8565U) with the image's pinned NumPy 1.26.4 is that case. Median ms of one
frame's azimuth histogram on the review container, scan-ordered clouds tiled from the synthetic
fixture. NumPy 1.26 has AVX-512 disabled (`NPY_DISABLE_CPU_FEATURES`) to stand in for that laptop;
NumPy 2.4 gives similar figures with or without AVX-512. Ranges span repeated runs:

| NumPy | points | `main` (`np.histogram`) | branch (`searchsorted`) | proposed (compare counts) |
|---|---:|---:|---:|---:|
| 1.26.4, AVX2 only | 127 k / 381 k / 890 k | 6.0 / 19.1 / 50.4 | 1.4 / 3.5 / 13.9 | 0.3–0.5 / 1.7–2.1 / 4.2–5.2 |
| 2.4.6 | 127 k / 381 k / 890 k | 0.6 / 1.8 / 4.3 | 1.3 / 3.9 / 9.0 | 0.2–0.3 / 1.6–1.8 / 3.9–4.3 |

The proposed body counts `values >= edge` per edge. That is branch-free and needs no sort or search.
It keeps the same fallback conditions and returns identical counts: 4 000 fuzzed cases on each NumPy,
covering every edge, the next float outside the range, NaN, ±inf and −0.0. With it in place, the
branch's 75 health tests pass (`test_health_histogram.py`, `test_health_gate_parity.py`).

```python
def _sector_counts(values: np.ndarray, edges: np.ndarray) -> np.ndarray:
    """Exact ``np.histogram(values, bins=edges)[0]`` for the health monitor's few explicit edges,
    by counting ``values >= edge`` per edge (vectorised compares, no sort, no per-value search).
    Values are compared in float64, as ``np.histogram`` compares float32 data with float64 edges;
    NaN fails every comparison and +-inf cancels out, as there. Unusual inputs keep ``np.histogram``."""
    floating = (np.dtype("float32"), np.dtype("float64"))
    if not (type(values) is np.ndarray and values.ndim == 1 and values.dtype in floating
            and type(edges) is np.ndarray and edges.ndim == 1 and edges.dtype in floating
            and 2 <= edges.size <= 257 and np.isfinite(edges).all()
            and (edges[1:] > edges[:-1]).all()):
        return np.histogram(values, bins=edges)[0]
    v = values.astype(np.float64, copy=False)
    e = edges.astype(np.float64, copy=False).tolist()
    at_least = np.array([np.count_nonzero(v >= x) for x in e], dtype=np.intp)
    counts = at_least[:-1] - at_least[1:]
    counts[-1] += at_least[-1] - np.count_nonzero(v > e[-1])   # the last bin includes its right edge
    return counts
```

**S2 — `lowobj.local_surface_mask` (opt-in) has no time bound.** Up to 512 candidates each run a
windowed `np.unique(axis=0)` and per-metre percentiles. Measure its cost on a dense frame before
enabling `experimental_low_local_support.yaml`.

**S3 — `timing_ms.total` excludes the health stage** (known, pre-existing; see the health evidence
README). The node's `detect_ms` measures the whole call.

### Design notes (no change made)

* The start-up default (item 4 above) is a deliberate choice, but it is a measured start-up
  regression against `main`. Deciding it needs the paired start-up recall comparison that
  [`MAIN_SYNC_2026-09-28.md`](MAIN_SYNC_2026-09-28.md) asks for.
* `test_evaluator_rejects_mutated_reserved_candidate_before_processing` is weak: its manifest has
  no cases, so the guard it names cannot fire.

## Organizers' answer of 29.09

Q1 and Q2 are answered: the envelope is measured from the rail heads, the rails may run at any
angle to the LiDAR, and the synthetic objects are placed approximately, which the check corrects
for. It is recorded in [`organizers/answers.md`](organizers/answers.md) §9; the decisions it
unblocked, without a detector change, are in [`QUESTIONS.md`](QUESTIONS.md) and
[`DECISIONS.md`](DECISIONS.md) rows 1 and 18:

* `gauge.reference` 3 stays. It never narrows the rails' envelope and widens it by at most 0.2 m
  within 60 m on straight track, at no measured false-alarm cost. Rails-only loses the real person
  61 → 58 frames and the edge cube 35.0 → 5.2 m.
* `gauge.axis_union` stays off.
* Q2's box stays an obstacle.

The public deck still lists the question as a next step, and P2 needs to rebuild it
([`PRESENTATION.md`](PRESENTATION.md)).

## Verification

* `ruff check .` clean; `scripts/sync_params.sh --check` in sync; `scripts/detector_freeze.py
  verify` PASS (34 files, source `c0273a13…`), unchanged by the review.
* `pytest` (Python 3.11, NumPy 2.4, Open3D, native kernels, `RESENSE_REQUIRE_SYNTHETIC=1`):
  `main` 770 passed; branch head 1 091 passed; after the review 1 100 passed, 6 subtests. In each
  run, one test is deselected because it needs the ride cache.
* Not re-run here: the regression gate, history stress and ROS runtime on the organizers' data.
