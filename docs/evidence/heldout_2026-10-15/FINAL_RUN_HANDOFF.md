# G3 final run: handoff to the fresh agent (written 20.10 by P4; P4 does not run G3)

> **For:** the one fresh-context agent that runs G3 on the accepted 1.2.0 seal (planned 21.10) · **Status:** handoff only,
> nothing here was run against a detector · **The registration is unchanged:** `spec.json`, `README.md`, `validate.py`,
> `input_metadata.json` are exactly as registered on 15.10 (canonical spec sha256 `36d2c867…6093`, case table `0e799d28…8232`,
> input metadata `a7a95222…bf80`). This file only removes ambiguity; where it and the README differ, the README wins and
> you report the difference. Rule of the repository ([`CLAUDE.md`](../../../CLAUDE.md)): nobody runs or tunes on G3 except you.

## 0. What you are, what you may read

You have **not** tuned ReSense and must not have read its results. Read only: this folder (`README.md`, `spec.json`,
`validate.py`, `validate_linux.py`, `input_metadata.json`, this file), `docs/DATASET.md`, `docs/SENSOR.md`, `CLAUDE.md`,
`docs/evidence/judgement_2026-10-13/scripts/` as **input contracts only** (decoder, ray-cast, matching), the seal manifest
and `scripts/detector_freeze.py`. Do **not** open `docs/BACKLOG.md`, `docs/evidence/**` result folders, `CHANGELOG.md` or
any range/probe output: they contain development results on these very backgrounds. The captain gives you the seal in a
**seal receipt** (section 6); you need nothing else about the detector.

## 1. What G3 can and cannot claim (say it in the report's first paragraph)

New synthetic placements, motions and perturbations on **real backgrounds that development has already seen**: the whole
`new_data` ride is in the regression gate (false-alarm counts, F1a's tuning) and Set F injects its own objects into six
spans of it. It is a held-out *placement* test, not a held-out *background* test, and it cannot estimate real-obstacle
recall. Window w04 (global 8823–9536) shares **59 frames, 8823–8881, with a Set F background span (8772–8881)**; all 59 are
in w04's 60-frame warm-up (insertion at 8883), none of the scored frames (≥ 8883) is in a Set F span. w01–w03 share nothing
with Set F. Report this as it is; do not drop w04.

## 2. Preconditions (stop and report `not executed` if one fails)

| # | precondition | how you check it |
|---|---|---|
| P1 | the captain has accepted the seal and gave you the receipt (commit, tag, archive sha256, image digest, manifest path, digest `6d091081…2452` unless a later reseal) | receipt file, section 6 |
| P2 | the checkout is the sealed tree | `git ls-tree -r <commit> -- resense native configs setup.py pyproject.toml ros2_ws/src/resense_ros/config \| sha256sum` equals the receipt (R3 seal: `014ad8fd…3e54`) |
| P3 | the registration validates | `python3 -B docs/evidence/heldout_2026-10-15/validate_linux.py --self-test --check-inputs --data-root <root> --original-root <ride root>` prints `PASS`; **use `validate_linux.py`, not `validate.py`** (section 3, finding A) |
| P4 | one runtime for everything: Python 3.12, numpy 1.26.4, scipy 1.13.1, scikit-learn 1.5.2, open3d 0.19.0 (ICP only), `OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1`, native kernels built from the sealed source | record versions and `_resense_native` sha256; do not mix runtimes (section 3, finding D) |
| P5 | the 56 original DB3 splits of `new_data` (20–33, 50–63, 124–137, 173–186) are present with the intake's sha256 | `input_metadata.json` lists the names; hash the payload yourself and add it to the scene manifest |
| P6 | your adapter and scene manifest are committed **before** the first detector call, and a second reader has confirmed the adapter follows the spec | commit hash in the report; recommended: P4 reads the adapter against the spec without seeing any detector output |

## 3. Things in the registration that will trip you (found 20.10, all resolved here, none needs a registration change)

**A. The validator fails on Linux as committed.** `validate.py` compares SHA-256 of the three judge shell scripts with values
taken on a Windows checkout (CRLF). On an LF checkout it stops with `harness input definitions changed`. The files are the
same: the hash of each file with LF turned into CRLF equals the stored value for all three. `validate_linux.py` (new, beside
`validate.py`) makes exactly that one comparison on the CRLF form and calls `validate.main()` unchanged. Checked: it prints
`PASS` with the registered hashes above, and still rejects a file with one appended line. Do not edit `validate.py`, `spec.json`
or `input_metadata.json` to make it pass; an edit after registration ends the held-out status.

**B. `spec.json.paths` are the registration machine's Windows paths** (`C:/Users/...`, `D:/Datasets/...`). They are
placeholders. Map them with `--data-root` / `--original-root` and your own scene root; write the mapping into the run manifest.
Do not change the file.

**C. "No detector calls ... including through helper imports" has a trap.** `cache_decoded.py` imports `judge_runner`, which
imports `resense.detector.Detector` at the top; `resense_ros.fastcloud` imports `resense.pointcloud`, and `resense/__init__.py`
imports the detector. Any helper that touches `resense` loads detector code. Resolution (decision D2, default): the
geometry preparation (decode, ICP, rails, scenes) uses **no `resense` import at all**: read the DB3 with `sqlite3`, parse
PointCloud2 with `numpy`, and apply the 2.5–250 m bounds of the node decoder yourself. After the scene manifest is frozen and
committed, you may check your decoder against `fastcloud.decode` on a stated sample of frames in a separate process; a
mismatch is reported, not repaired by editing scenes. Constructing a `Detector`, `NodeReplica` or `DetectorConfig` before the
first scheduled replay is a protocol violation.

**D. Results depend on the runtime.** The same physical replay of the same source moved a moving body's onset by up to 6.6 m
(three scans) between Python 3.12/numpy 1.26/native kernels and Python 3.13/numpy 2.5 without the native kernels
([review](../p4_review_final_bundle_2026-10-20/README.md) §3). Run all 924 replays in the P4 runtime and say so.

**E. The adapter does not exist.** The registration specifies it (README §3–§6); nobody has written it. It is the larger part
of the work: decode, full ICP (CPU point-to-plane, parameters in `spec.geometry`), station and tangent, rail and bed support,
category tests, analytic ray-cast of nine shapes on the measured ring/azimuth grid, eleven one-factor variants, the match
rule and the hazard envelope. Time-box it. If it cannot be finished, reviewed and committed before the first detector call,
report G3 as `not executed` with the reason; do not shorten the spec, run a subset, or reuse `range_test.py` /
`icp_odometry.py` (they call `baseline()` / `NodeReplica`, i.e. the detector).

**F. w04 has four timestamp gaps above 0.25 s (max 4.40 s).** Registered as is; invalid spans are reported as flags
(`README` §2, §4). Do not trim.

## 4. Run order (single write-once batch)

1. `git checkout <commit>`; run P2, P3; save both outputs.
2. Prepare detector-free: decode → ICP → station/tangent → rails/bed → category tests → scenes (84 cases × 11 variants =
   924 scheduled replays). Write the scene manifest (all source payload hashes, decoder and library versions, thread
   settings, per-window fits and flags). **Commit 1** = adapter + manifest. Nothing detector-related has run.
3. Read-through of the adapter by a second reader (P6). Fix defects **before** commit 1 is tagged; a fix after the first
   detector call is a protocol violation and ends the held-out status.
4. `python3 scripts/detector_freeze.py verify --manifest <receipt manifest>` → must print PASS. Save the log (verify log 1).
5. Execute the 924 replays once, in lexicographic `(case_id, variant_id)` order, one fresh detector and its own warm-up per
   replay; outputs under `docs/evidence/heldout_2026-10-15/run_final/<case>/<variant>/`. No retries, no early exit, no
   substitution, no overwrite (the output directories are created exclusively). A technical failure is a result row; an
   unexecuted row is `not_executed`.
6. Verify the same manifest again (verify log 2). Only then write `results.json`, `results.md`, the 924-row table, and the
   frame/miss/control artifacts named in `spec.json`.
7. **Commit 2** = run outputs + both verify logs + results. Publish every miss, every negative/empty STOP, every blocked,
   unobservable and incomplete case, paired variant deltas, full scheduled denominators next to the geometry-valid, hazardous
   and visible subsets. No pass threshold is invented after seeing results.

## 5. After the run

* A defect found by G3 is a **finding**, not a patch: you change no code. A detector change follows
  `docs/DETECTOR_FREEZE.md` (new gate, review, reseal); it makes this battery development data and G3 cannot be reused for
  another held-out headline.
* Do not compute anything that makes a number look better (re-fitted rails for one variant, a different window, a different
  match radius). If you notice a registration error, report it with the evidence and keep the registered result.
* Hand the captain: the receipt, the two verify logs, the commit hashes, the results, and the list of deviations from the
  registration (an empty list is a result).

## 6. Seal receipt (the captain fills this in; template)

```json
{
  "seal": "1.2.0",
  "commit": "<40 hex>", "tag": "<tag or null>", "archive_sha256": "<hex or null>", "image_digest": "<sha256:... or null>",
  "manifest": "docs/evidence/detector_freeze_2026-10-20_1.2.0_r3.json",
  "manifest_source_sha256": "6d091081769104657ecc2c0b06f53049647d4f6c7327b7429bbda92673782452",
  "sealed_tree_sha256": "014ad8fd61f1a4b6962952505cc0274c95744f476c0d8d501a9c8cbe27873e54",
  "accepted_by": "<captain>", "accepted_on": "<date>",
  "data_root": "<path>", "original_ride_root": "<path>", "runtime": "<python, numpy, scipy, sklearn, open3d, OPENBLAS_CORETYPE>"
}
```
The image digest is optional for the Python replays; if the image is part of the claim, run the image's own `resense` package
and compare its sources with the commit.

## 7. Decisions the captain still owns (defaults given, nothing blocks on them except D1)

| id | decision | default |
|---|---|---|
| D1 | which seal G3 binds (the R3 reseal `f56ad5e`, or a later one) and the date | the R3 reseal, 21.10; a later reseal needs a new receipt |
| D2 | the "helper imports" reading in finding C | geometry prep with no `resense` import (stricter than needed) |
| D3 | who reads the adapter before the first detector call (P6) | P4, spec-adherence only, no detector output |
| D4 | time-box for the adapter, after which G3 is reported `not executed` | decided by the captain; the jury is 23.10 |
