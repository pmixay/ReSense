# P4 case register and numeric export — format v1 (proposed, for P2 to confirm)

Built by [`build_export.py`](build_export.py) from committed evidence only; re-run it after any new
P4 result. `python build_export.py --check` re-reads every exported number from its source and
fails on any difference (last run: **2,461 numbers, 0 mismatches**). Proposed by P4 on 16.10.
**Not yet agreed:** P2 confirms the columns, or names the changes, and the format then becomes "v1 agreed".

## `case_register.csv` / `.json` — one row per case × detector version

| column | meaning |
|---|---|
| `case_id` | `<stage>/<recording or case>/<variant>`, stable across versions |
| `stage` | `X3` robustness battery, `X1` range attribution, `J1` judge pipeline, `G3` held-out (registered) |
| `recording`, `alias` | organizer recording; alias A/B/C/S/D/obstacle/platform/Set O (B = roundT_doubleT, C = roundT_pressureGate_roundT) |
| `object` | labelled / synthetic object or `none (empty)` |
| `variant` | X3 perturbation, X1 judge arguments, G3 motion + its 11 variants |
| `version`, `commit` | `v1.0.0` = `707ea9c`, `1.1.0` = sealed tree of `492e407` (= measured `5211565`) |
| `runtime` | where it was measured |
| `status` | `MEASURED`, `PASS vs control`, `MEASURED (attributed)`, `DRY RUN`, `PRE-RELEASE, not a J1 result`, `REGISTERED, NOT RUN` |
| `scope` | `development data (in-sample)` or `held-out synthetic probes` |
| `result` | one-line human summary |
| `evidence` | committed source file |

Current content: **238 rows**. X3 has 120 rows: 40 cases × 3 runs (v1.0.0 Windows, the v1.0.0
Linux control and 1.1.0). X1 has 22 (11 cases × 2 versions) and J1 has 12 (6 bags × 2). G3 has
**84 registered cases (924 planned runs), none run.**

## `numbers.csv` / `.json` — one row per number (long / tidy)

| column | meaning |
|---|---|
| `stage`, `case_id`, `version` | as in the register |
| `metric` | dotted name, e.g. `stop_frames`, `object.small_on_rail.first_stop_m`, `cause.no_blob.150-200m`, `label_check.track:confirm_time.confirmed` |
| `value`, `unit` | the number exactly as in the source; unit `frames`, `episodes`, `rows`, `m`, `frame index`, `bool`, `cases`, `runs` |
| `status`, `scope`, `runtime` | as in the register; `in-sample` for all measured rows |
| `source`, `pointer`, `source_sha256` | committed JSON file, RFC 6901 JSON pointer into it, SHA-256 of the file used |
| `derived` | empty for read values; else the formula of a total computed by the builder (126 rows: X3 summed inside rows, acceptance counts, G3 counts, wrong-label counts) |

Use for charts: filter `stage`, `version`, `metric`. Every chart number can then be traced to a file
and pointer. Do **not** mix stages in one series: X3 / X1 / J1 use the node-decoded path, the team's
regression gate uses compact16 caches, and their hit counts are not interchangeable.

## Rules for captions

* Numbers are **in-sample** (development recordings and the organizers' synthetic set O). G3 has no result.
* A `PRE-RELEASE` row is not a J1 result; the judge score 66/100 is v1.0.0's.
* X3 perturbation rows depend on the BLAS kernel; they are comparable only within one runtime
  (the export's 1.1.0 and Linux control rows share one).
