# P3 checkpoint: the 15-16 October work started and measured

**Owner:** P3. **Date:** 15.10.2026. **Status:** H1 and H2 measurement packages
complete; five cheap R2/R1 overrides rejected. H3 integration, H4 independent
review and H5/H6 release work remain with P1/P4.

## Local handoff branches

| task | branch | code measured | evidence commit / path |
|---|---|---|---|
| H1 free-top hardening | `r3/column` | `a2660af` (detector = WIP `42108ac`) | `ccb68c1`; `docs/evidence/column_hardening_2026-10-15/README.md` and `continuation/` |
| H2 structure-cut physical bar | `h2/cut-bar` | `eba9761` | `7380f65`; `docs/evidence/structure_cut_bar_2026-10-15/` |
| R2/R1 screen + shared intake | `p3/range-screen` | `264f5b2` (detector = `d0d17bb`) | `docs/evidence/range_screen_2026-10-15/` and this directory |

Worktrees are under `C:/Users/alikh/AppData/Local/Temp/opencode/`:
`rs-h1`, `rs-h2`, `rs-range-screen`. `git worktree list` identifies them.
The H1/H2 paths in the table belong to their named branches, rather than
being links to nonexistent files in the screening branch.

## Results

* The unmodified **full baseline gate passed**, then **H1 and H2 passed**
  separately, all without `--allow` or candidate overrides.
* Both candidates preserve all **15,269 frames / 15 work outputs** against
  the local `final/silent-misses` control in obstacle/warning flags,
  detections/warnings, nearest/clear distance, candidate count and track.
  Set F is checked separately by each full gate.
* H1 dark-band what-if: piece 1 **30/6 -> 23/5**, piece 3 **13/3 -> 7/3**
  STOP frames/episodes. Plain replays match the seal. The residual excess
  over the seal under the what-if remains 9 and 5 STOP frames.
* H1: **20 stress cases**, zero changed decisions; **15 pole/post controls
  and 6 tall-object probes**, zero lost matching STOP / new GO. A-axis pole
  remains **157/177**. Three CAUTION warning `reason` fields differ from
  the seal (`column` -> empty); H1's descriptor diff explicitly lists them
  for H4. No independent safety review is claimed here.
* H2: the pre-committed single-azimuth-column defect is fixed by requiring
  one full **0.1 degree** horizontal sensor step. The problematic mast's
  matching false STOPs **2 -> 0**; C person stays **82.77 m / 55 STOP frames**.
  **20 wall-anchored cases** add zero false wall-object STOP frames and lose
  zero axis-object STOP frames. C dropout/5 Hz retains no cut fragment.
* H1 affected tests: **51 passed**, no skips. H2 affected/neighboring tests:
  **48 + 123 passed**, no skips; changed-code/test lint passes.
* **All five R2/R1 overrides fail the full gate** (exit 1): each increases
  ride false-alarm events. R2b also worsens platform events/episodes and Set F
  trolley false detections. See the
  [screen report](../range_screen_2026-10-15/README.md) for exact metrics and
  the small range gains that do not meet the acceptance targets.

Machine-readable consolidated results: [`results.json`](results.json).

## Prepared data and runtime

```text
C:/Users/alikh/AppData/Local/Temp/opencode/resense-p3-data/
  for_hackathon/   original six organizer bags, 23.1 GB unpacked
  cache/          gate compact16 caches: all six bags + Set O + full ride
  decoded/        node-decoded float32 caches, including A/B/C/S
  odometry/       recomputed ICP on A/B/C/S; shared sealed baseline axes
```

Gate counts: doubleT_obstacle 201, doubleT_platform 345, roundT_doubleT 252,
roundT_pressureGate_roundT 268, roundT_squareT_pressureGate_squareT 545,
squareT_platform_squareT_switch 877, Set O 1,510, ride 11,271.

The six bags were downloaded from the organizer Google Drive link in
`VM_GUIDE.md` and decoded with the repository's tools. Existing local Set O
and ride caches were preserved; compressed split-named gate views were
created without changing their arrays. Every ride timestamp was checked
against the original DB3; the first payload of **each of 221 splits** was
freshly decoded and compared. The local `new_data.zst` size and published
SHA-256 were verified. Exact intake: [`ride_intake.json`](ride_intake.json).

Python environment:
`C:/Users/alikh/AppData/Local/Temp/opencode/resense-p3-venv/Scripts/python.exe`.
Native C ABI kernels were built in each checkout with MSVC x64 strict FP;
native parity tests passed. `PYTHONPATH` and `RESENSE_REPO` were pinned to the
checkout under test, with one BLAS thread per process. Timings here are
informational on a shared Windows machine, not a stand performance claim.

The 36 baseline committed source blobs match the 29.09 seal. The raw
`detector_freeze.py verify` call on Windows fails on CRLF checkout bytes and
the generated `.pyd`; this is recorded in provenance rather than labelled
PASS. Candidate source changes await H4/H5; the Linux reseal check belongs
to that acceptance path.

## Reproduction and raw outputs

Retained raw runs:
`C:/Users/alikh/AppData/Local/Temp/opencode/resense-p3-runs/`.
SHA-256 identities: [`raw_sha256.json`](raw_sha256.json). This includes the
gate work JSONLs, range probe rows, robustness replays and their hook data.

[`scripts/`](scripts/) preserves the continuation scratch drivers as `.txt`
for audit (not CI/application modules). To rerun, restore the original
`resense-p3-<name>.py` names under a scratch root and adapt their `BASE`, repo
and data paths. The Unix `resource` import has a Windows-only RSS adapter;
it does not change detection or decision logic. The inherited `.py.txt`
drivers are loaded directly. Only `grun.py`'s global frame-index parser is
adapted to accept the existing flat ride cache names; split/local identity
is independently checked by the data-view preparation.

## Next owners

1. **P1 H3:** integrate passing H1/H2 and `r3/axis` on `final/silent-misses`,
   gate the combined committed detector and explain its frame diff.
2. **P4 H4:** independently review the combined source and evidence,
   including H1's three changed warning reasons and its dark-band residuals.
3. **P4 X1 / P3 validation:** attribute the R1/R2 range losses before another
   code candidate; arrange the G3 pre-registration for further tuning.
4. **P1 H5/H6:** version bump, final gate, reseal and release after review.

This checkpoint does not substitute the individual gates for the combined
H3 gate or the independent H4 review.
