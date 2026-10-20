# R3: Set F sustained median explained; reporting repaired — 20 October 2026

**The reported 34.2 ->17.8 m drop is not a reproduced detector regression.**
Fresh paired runs confirm a change in the population over which this conditional
median is computed. The historical R3 report already documented that explanation;
the backlog had incorrectly continued to treat it as an unexplained open loss.

## Fresh result, not an assumption from the old report

The [protocol](PROTOCOL.md) and driver were committed before running. Source
**`69cf4b8`** has the same detector/config bytes as merged H1 `0f02b28` and main
publication `cefd4c4`. One side uses current defaults, the other changes only
`tracking.cable_confirm_time_s` to 0 (disabling both R3 shortcuts).

Every original RNG draw is retained: all five kinds, in their registered order,
on six ride starts. This is **30 sequences, 3,060 rows per side**, including six
3 cm cable sequences with 612 rows per side. Inputs and source are hash-pinned;
frame identities, placement/geometry and return counts agree in every paired row.

| Ride start | Matched cable rows, off ->on | held90, off ->on (m) |
|---|---:|---:|
| 46 | 8 ->8 | absent ->absent |
| 68 | 23 ->26 | 19.0 ->19.0 |
| 98 | 29 ->31 | absent ->16.6 |
| 140 | 21 ->21 | 49.5 ->49.5 |
| 168 | 3 ->5 | absent ->16.4 |
| 172 | 18 ->20 | absent ->absent |

**No previous hit is lost**, on any of the 30 sequences. The other four kinds
add no hit; cables add nine. False detections do not increase; both cable sides
have zero. First detections and every previously achieved sustained range are
preserved or improved.

## Why the median falls

The original metric excludes sequences without a >=90%-recall visible tail
containing at least five frames. Its successful population changes:

* Off: **2/6**, values 19.0 and 49.5, displayed median **34.2 m**.
* On: **4/6**, values 16.4, 16.6, 19.0, 49.5, displayed median **17.8 m**.
* Fixed baseline-success cohort: **34.2 ->34.2 m** (unrounded 34.25 both sides).

These are injected objects on moving real backgrounds with legacy detector-axis
placement. held90 pools visible frames; it is **not** continuous STOP, surveyed
real-world range or braking sufficiency. This diagnosis does not claim broader
R3 perfection or close H1, the independent final review, or P4's B2/B3 findings.

## What is repaired

`scripts/regression_gate.py` now retains compact per-sequence evidence and prints
success coverage beside the original median. When both compared reports contain
that evidence it adds paired baseline-success-cohort diagnostics and lists losses.
Legacy summaries explicitly yield **not_comparable**, not a fabricated paired pass.

`scripts/set_f_comparison.py` provides the same comparison directly from raw Set F
runs. It reports a lost hit or sustained success even when the aggregate median
improves, rejects changed placement/visibility or missing sequence populations as
not comparable, and exits nonzero for regression/incomparability.

**All existing metric values and gating bits are preserved.** The 34.2 ->17.8 row
still has its original informational `worse` verdict; the explanation is additional
evidence, not a waiver or replacement number. No detector/config edit was needed.

## Verification and limits

* [Independent recount](audit.json): held90 derived by sorted-distance integer hit
  counts, independently of the original evaluator. All 30 sequences and all 612
  cable rows checked; all six cable outcomes match the historical audit.
* [New comparator output](paired-comparison.json) agrees with the independent
  recount on every sequence, every lost/added hit set and every sustained range.
* Nine raw changed-hit examples are printed in the audit: object distances
  14.5–73.9 m, 17–43 inserted returns, false ->true; all were inspected. The
  [six raw tail-recall plots](cable-tail-recall.png) were visually inspected:
  on is nowhere below off; starts 46/140 overlap, the other four improve.
* Positive controls find a planted known-hit/sustained-success loss and reject
  missing sequences/changed placement. Unit tests also cover the misleading
  **higher** median caused by losing an old success, duplicate rows, visibility
  changes and the five-frame minimum.
* **51 affected tests pass**, no skips. Full suite was not rerun for this reporting
  change; the last merged-detector full run remains 2,276 passed +17 subtests,
  one inherited proxy-hook failure, eight external-data deselections.
* [Reporting verification](reporting-verification.json): every one of 224 original
  gate metric tuples (208 non-timing) is exact, including direction/gated bits.
  The [prior complete gate was re-graded](regraded-prior-gate.json), not replayed;
  its acceptance record is identical. No fresh full gate/X3/Falcon is claimed.
  Detector/config bytes are unchanged from the source already checked by those
  [combined H1 runs](../h1_partial_integration_2026-10-20/README.md).

## Reproduction and retained evidence

Runtime: Python3.12, NumPy1.26.4, the existing native binary. Set
`RESENSE_REPO`, `PYTHONPATH`, `OPENBLAS_CORETYPE=Haswell`, `OMP_NUM_THREADS=1`,
`OPENBLAS_NUM_THREADS=1` and the existing Open3D `LD_LIBRARY_PATH` as in the
[H1 runtime record](../h1_trajectory_2026-10-19/README.md).

`run_checks.py` uses `/tmp/opencode/r3-sustained`; use a fresh working/evidence
directory for reproduction because outputs are created exclusively. The raw
archive contains off/on reports, configuration, logs, JUnit and source snapshots;
the archive and every member are checked against [package.json](package.json) and
[raw-manifest.json](raw-manifest.json). Inputs are pinned separately in
[input-manifest.json](input-manifest.json).

```bash
python scripts/set_f_comparison.py <raw-off.json> <raw-on.json> --out <fresh-output.json>
python -m pytest -q tests/test_set_f_comparison.py tests/test_regression_gate.py \
  tests/test_far_range_eval.py tests/test_far_range_placement.py
```

The P3/P4 detector issues in draft PR #43 require their own diagnosis/acceptance.
This follow-up resolves the **Set F aggregate concern only**. No G3, new judging,
release, reseal or independent final acceptance is performed.
