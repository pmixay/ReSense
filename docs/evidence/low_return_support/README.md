# Low-ray support candidate: pilot screen and full gate (rejected)

> **Purpose:** index of the whole folder: the synthetic pilot that motivated the candidate and the full regression gate that rejected it; points to the existing gate README instead of repeating it.
> **Audience:** team, jury · **Owner:** lane not recorded in the folder or the docs · **Language:** EN
> **Last verified:** 2026-10-22: the 28 files of `full_gate/artifact_manifest.json` re-hashed, all 28 match; numbers below read from the named files and compared with
> [`full_gate/README.md`](full_gate/README.md); the dataset is not available, so no run was repeated ·
> **Status:** final record of a rejected candidate (not integrated into the detector)

Details of the gate result are in [`full_gate/README.md`](full_gate/README.md) (not edited here). The pilot has its own [`pilot/README.md`](pilot/README.md).

## 1. What was run, when, by whom

* **Pilot** (development screen): clean source `75ef4e20e587203a394e365c4fa601c822adb164`, native library sha256 `b5a5c2dc...`, default config, v2 cache; baseline and candidate results are [`pilot/baseline_clean75.json`](pilot/baseline_clean75.json) and [`pilot/candidate_clean75.json`](pilot/candidate_clean75.json) (`full_gate/protocol.json`, block `development_screen_previously_run`). The pilot files carry no date.
* **Full gate:** candidate commit `1e2a3ffe9307e1aba4d5a61304a34c58a3874f12`, built on base `292397833edf9db649a24f16807b2cfb15812194` (`protocol.json`, `branch_base`). Run by `full_gate/run_gate.py` with `protocol.json`; `gate.json` field `created` is 2026-09-28T21:32:47+00:00 and `completion.json` has `finished_unix` 1790631167 (the same instant, as I converted it with `date -u`). Machine from `gate.json`: 8 CPUs, Python 3.10.12, NumPy 1.26.4, 4 jobs.
* **Dates:** `protocol.json` says `registered_at` 2026-09-29, one day after the run time in `gate.json`. The two dates disagree (see section 5). The index `../README.md` gives "28-29.09". **Import date** into this repository: 2026-10-16, squash commit `44b462e`; not a run date.
* **Who:** the lane is not recorded in the folder or the docs. Branch name omitted (none is recorded: `gate.json` has `branch: None`).

## 2. Result

* Pilot: on the 30 cm compact target at 50 m, matched STOP frames 0/16 to 12/16 in float32 and compact16 (`pilot/baseline_clean75.json` and `pilot/candidate_clean75.json`, case `compact_box30_50m_1`, first matched STOP frame 4; I counted `matched_stop` in both files). Synthetic only.
* Full gate: **FAIL, exit code 1**, 685.5 s (`full_gate/completion.json`); one gated metric worse, `ride.stop_episodes` 31 to 32; 207 gated metrics same, 0 better (`full_gate/gate.txt` last lines, `gate.json`). Ride alarm frames 130, alarm events 32 (`gate.json`, `ride`). Set F: 3060 rows, 30 sequences, 0 changed rows; 585 changed recorded rows overall, 53 with changed detections, 533 with changed warning text (`full_gate/comparison.json`).

## 3. Supports

* `docs/evidence/README.md` section 2, row `low_return_support/`: "full gate FAIL (exit 1), not integrated".
* `docs/archive/SCORECARD_history_2026-10-19.md` line 86: the candidate is not integrated and does not raise the score.
* Baseline: `../cycle_2026-09-28/complete_timing/default/gate.json` (exists), commit `bc75abe04a0b13c29c555a7baf64b4745603c02a` (`protocol.json`).
* No row for it was found in `docs/DECISIONS.md`, `BACKLOG.md`, `EXPERIMENTS.md` or `VM_GUIDE.md` (grep for "low_return", "low-ray", "low ray").

## 4. Contents (33 files)

* [`README.md`](README.md): this file.
* [`pilot/`](pilot) (4 files): `README.md`; the two result JSONs (8 cases, 2 input types each, 16 frames per case); `low_ray_support.patch` (240 lines, the pilot diff).
* [`full_gate/`](full_gate) (29 files): `README.md`; `protocol.json` (registered before the gate); `run_gate.py` (wrapper); `identity_pre.json`, `completion.json` (identities before and after, exit code); `cache_identity.json`, `cache/new_data_intake_manifest.json` (input provenance); `candidate-source.patch` (240 lines); `gate.json`, `gate.txt` (gate result and its table); `comparison.json` (row-level comparison with the baseline); `artifact_manifest.json` (sha256 of 28 files); `work/` (17 files: 8 ride chunks `new_data_0..7.jsonl.gz`, 6 recordings, `cloud_with_fake_obj`, `setF_straight.json`, `config.yaml`).

## 5. Caveats

* **Date disagreement:** `gate.json` `created` (2026-09-28 21:32 UTC) is before `protocol.json` `registered_at` (2026-09-29), although the protocol says `registered_before_full_gate: true`. Possible time-zone or editing explanation; not established. Not fixed here.
* **Two patches, not equal:** `pilot/low_ray_support.patch` (sha256 `262ed8bb...`) is the patch recorded in the protocol; `full_gate/candidate-source.patch` (sha256 `7805bb5b...`, listed in `artifact_manifest.json`) differs in content (for example a different state variable next to the same hunk). The gate tested the second; the pilot screen used the first. So the 12/16 pilot figure is for a different source revision than the gate (the source digest `f7e38ec6...` in `protocol.json` is the gate's).
* The candidate commit `1e2a3ff...` is not an object in this repository (`git cat-file` fails), so the gate cannot be re-built from this checkout; the patch files are the record.
* `full_gate/README.md` says "Six Set F approaches across five kinds"; `comparison.json` says 30 sequences, 3060 rows. Not reconciled (possibly 6 approaches x 5 kinds = 30).
* Latency rows in `gate.txt` show "better"; `full_gate/README.md` says timing is informational because other work ran on the machine. No speed claim.
* Synthetic screen only: not held-out evidence. Not integrated; superseded status is not recorded anywhere I found.
