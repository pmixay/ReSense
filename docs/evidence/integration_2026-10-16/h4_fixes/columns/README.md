# H4 column author work — BLOCKED, no acceptable runtime fix

**The zero-dark-excess candidate loses accepted positives and is rejected.** This
folder records implementation-author work, not independent review or release
approval. H4-S1/S3 remain open in the integration runtime. The production column
files and configuration are restored exactly; the rejected implementation is
retained as an auditable patch. The conditional continuation to main is blocked.

## Main measured results

| Check | Control | Rejected attempt 08 |
|---|---:|---:|
| Physical case 45, highest-first, no dropout | 0 matched STOP / 20 updates | **14 / 20**, frames 5–9,11–19 |
| Exact inherited dark observer, ride piece 1 | 14 STOP | **14**, 0 excess / 0 lost frames |
| Same, ride piece 3 | 2 STOP | **2**, 0 excess / 0 lost frames |
| A-axis short pole, identical Linux parent control | **157 / 177** | **139 / 177**, 18 lost matched STOP frames |
| C-person first STOP / matched STOP frames | 82.77 m / 55 | 82.77 m / 55 |
| B / S, 27% dropout, seed 461023 | 0 / 51 STOP | 0 / 51, exact detection/warning descriptors |
| Plain ride pieces 1 / 3 | 14 / 2 STOP | 14 / 2, exact detection/warning descriptors |

The dark comparisons use the entire 1,409-frame pieces, fresh detectors, unchanged
input/fitted model/candidate arrays and the **exact inherited** 0.6-degree mask.
Frame sets and serialized centers are compared with **zero tolerance**, independent
of track IDs. `attempt-08-dark-comparison.json` records zero excess and loss.
This result belongs only to the rejected source, not the restored runtime.
The separate **new `restored-dark` replay** confirms the final integration runtime
still produces **23 / 7** dark STOP frames (**9 / 5 excess**, no lost sealed frames).
All 14 excess detections again match plain sealed warning centers exactly. This
is a new paired measurement, recorded in `restored-dark-comparison.json`.

Case 45 reconstructs the published XYZ SHA
`680878ed4f0b233cec517f999ca8648b1193522c929b7ce0f9df9fad7d545a20`, with
80 strict-gauge voxels / 20 rings and clipped observed top 2.939613 m. The author
candidate follows actual same-face returns above that cut, then asks for measured
footprint sight below the physical local vault. It never treats an absent ring
alone as positive sight. The two missing frames remain 9/10; STOP holds on 9,
releases on 10 and re-arms on 11 with the separately authored tracker fix.

## Rejection and limits

One complete positive footprint ring retains more short-pole detections but leaves
**8** exact dark excess frames in piece 1 (piece 3 excess 0); see attempts 06/07.
Two rings remove that excess, but reduce A-axis 157 -> 139 and lose the existing
free-pole-under-beam positive. In the full independent matrix, all sealed matched
STOPs remain, but comparison with the previously accepted combined H3 column path
also exposes losses:

| Component group | Prior matched STOP updates | Attempt 08 | Lost prior updates |
|---|---:|---:|---:|
| 2.72 m poles, 256 variants | 2,608 | 2,520 | **208** (120 returning-hit gains coexist with the losses) |
| 3.22 m poles, 256 variants | 1,144 | 2,068 | 0 |
| 3.62 m poles, 256 variants | 780 | 780 | 0; no tall improvement in this group |
| Opaque ceiling columns | 780 | 780 | 0 |
| Absorbing band 2.54..3.18 m | 1,680 | 1,680 | 0 |
| Absorbing band 2.54..ceiling | 2,616 | 1,680 | 936 |
| Original over-top beam controls | 416 | 56 | 364 |
| Multiple columns, matched per object | 120 | 120 | 0 |
| Analytic surface components, 144 variants | 3,632 | 2,432 | **1,200** |

These are sampled updates, not independent statistical trials. Physical columns
inside the known true envelope are collision objects; their STOPs are **not**
called physical false positives. The original beam does not fully occlude every
target. The self-contained portable negative beam separately uses a 2.65 m bottom
to actually block the first over-top sight line; the original fixture is immutable.
The supplied-coordinate surface controls do not establish ray realizability.

`probe_comparison.json` retains all 18 exact lost P3 frame rows and verifies
unchanged placements, visibility counts and original judge matcher. No range,
signature threshold, global bar or target acceptance was relaxed. No claim of
intrinsic/general impossibility is made: these measured current-frame evidence
paths do not satisfy the joint acceptance requirement. The remaining ambiguity
and STOP-history consequences need further author design and independent review;
the rejected prototype is not an approved temporal-evidence fix.

## Tests, registration and source identity

* **c87fc94** committed portable failure witnesses and `PROTOCOL.md` before any
  production patch, replay or tuning. `1edced6` retained the first parent failure
  scope and pinned Linux adapter. `f3074cf` retained subsequent test clarification,
  the exact-mask witnesses and rejected-attempt protocol/diagnostics.
* `tests/test_h4_column_evidence.py` is self-contained under tests/: no cache,
  evidence-folder imports or external fixtures. Its final parent run is **7 passed,
  12 failed, no skips**, exposing the remaining runtime defects.
* Attempt 08: **19/19** new H4 tests pass. Full affected suite: **117 passed,
  4 failed, no skips**; native **28**, structure/far-structure **22**, synthetic
  **40** pass. Original `test_column_free_top.py` assertions remain unchanged:
  two expose the unaccepted tall default, one the deliberately changed dark policy,
  and one the real under-beam positive loss. The suite is **not** called passing.
* Tests use Linux/Open3D with `RESENSE_REQUIRE_SYNTHETIC=1`; native is the verified
  unchanged Linux `.so` copied from the read-only H3 reference. No host native
  build or shared venv mutation occurs.
* `retained-08-reconstruction` independently rebuilds the rejected working source
  from its Git base plus archived patch, verifies identical source/config/native
  identities and runs the 19 portable witnesses: **19 passed**, no skips. This
  proves the retained prototype is reproducible, not acceptable.

| Identity | Value |
|---|---|
| Attempt-08 Linux Git base | `f3074cfb445425c50d926ded235fe01a4c3029ea` plus retained owned overlay |
| Attempt-08 36-file source SHA-256 | `e9eb1bf6443d5cf8206904c32c6f03cd1f2bd4f726741e8e88292a8bb44475d8` |
| Attempt-08 clustering.py SHA-256 | `d608eee06953966e280f5103ec83e86d5eb732dbdbe38e048a106f5ce5c06663` |
| Restored integration runtime 36-file SHA-256 | `c90f76cc485f6c479e64de23236785cc22cfcb5af5a282d514304f95a402ca51` |
| Native `.so` SHA-256 | `b5a5c2dc08be8fa1ab00e27dee7662d31413a99f819a760d2d2d4b16b93e8534` |
| Linux image | `sha256:5e2659e8f8d3a7e9f64d7c269ae920badd86b8a388e48e9449dda7028b920c19` |

`rejected_attempt_08_identity.json` contains every file, effective config, import
path and reviewer-script pin. The independent H4 geometry/replay files are verified
against **838dd32**, read-only and unchanged. The common Git object store,
reference sources and original data are read-only mounts. Numerical threads=1,
PYTHONHASHSEED=0, 2 GiB per worker, one author worker active at a time. No G3
protocol/cases are used. The tracker fix is authored separately; this work does not
edit tracking.py, version or freeze manifests.

## Evidence and reproduction

* `ATTEMPTS.md`: every rejected iteration and adapter clarification.
* `attempt-08-physical-comparison.json`: all physical input identities checked
  against sealed raw fixtures, correct `reported && zone==gauge` STOP derivation,
  per-variant losses, full case-44/45 witnesses and surface comparisons.
* `normal_comparison.json`: exact detection/warning outputs. Other stored
  serialized differences are explicitly classified in `normal_diff_details.json`
  as inherited H3 wall-drift/clear-range fields; this is not whole-output equality
  against the seal. Both plain rides have zero mismatches against retained H3
  candidate non-timing serialization in the worker's separate check.
* `runtime.json`, `EXTERNAL_ARTIFACTS.json`: immutable original commands, statuses,
  raw file sizes/hashes, source patches, code snapshots and outputs. Supplemental
  reconstruction/verification artifacts are separately indexed.
* `DARK_CENTER_COMPARISON.json` compares every detection center on every dark
  frame, including frames already STOP in the seal. `HASHES.json` indexes the
  package's canonical-LF text bytes; external indexes hash the original raw bytes.

Large raw root:
`C:/Users/alikh/AppData/Local/Temp/opencode/resense-h4-columns-author-20261016/`.
Every run reserves a fresh output directory and Linux source volume. The initial
installed-source eager-import failure is retained; the adapter restarts Python
after cloning and verifies the actual import before measurements.

Reconstruct the rejected source in a new Linux scratch volume, without changing
the integration working tree (use a fresh run name):

```powershell
python docs/evidence/integration_2026-10-16/h4_fixes/columns/launch.py NEW08 tests --mode witness --rejected-08
python docs/evidence/integration_2026-10-16/h4_fixes/columns/launch.py NEWDARK replay --mode dark-inherited --rejected-08
python docs/evidence/integration_2026-10-16/h4_fixes/columns/launch.py NEWCOMP components --mode all --rejected-08
python docs/evidence/integration_2026-10-16/h4_fixes/columns/launch.py NEWPROBE probes --mode critical --rejected-08
```

`--rejected-08` pins the Git base, applies only the retained owned patch inside
Linux and asserts the measured 36-file source digest. Without it, `--parent`
measures the current committed runtime. Prototype comments in the archived patch
are retained measurement bytes, not accepted new-default or measurement claims.

**No full-gate or merge approval is claimed.** The parent-owned final full gate
remains contingent on an acceptable committed fix; this attempt does not provide it.
