# F1 and Falcon false STOPs: lane P3 protocol, measurements, handoff (19.10)

> **Purpose:** the registered protocol (with eight dated amendments), the raw runs and comparisons, the one
> independent review, and the handoff of the F1 lane: which switches reduce false STOPs on the ride and on the
> Falcon recording, and what each costs.
> **Audience:** jury, P1 (integration), P3, P4 · **Owner:** P3 (`PROTOCOL.md`: "Lane: P3 (detector), ordered by P1") ·
> **Language:** EN
> **Last verified:** 2026-10-22: links resolve; the numbers below were re-read in the named raw files · **Status:**
> historical lane record; its candidate was integrated in part and F1a was changed afterwards (section 5)

## 1. What was run, when, by whom

* Lane P3, a container of 19.10 (`PROTOCOL.md`), on a branch off `main` `aec88d2` (the 1.2.0 candidate); branch
  name omitted. Protocol registered 19.10 before candidate measurements; amendments 1 to 8 are timed from about
  09:35 to 14:40 UTC the same day. `HANDOFF.md` is dated "19.10, ~15:10 UTC, stopped on P1's request".
  Run date is therefore 2026-10-19. The folder came with squash commit `0acb18c` (2026-10-19, "(#42)").
* Code under test (from `HANDOFF.md`): base `aec88d2`; switches-off `1144150`; best measured candidate `129415f`;
  ride/synthetic `8c88d5c`; handoff HEAD `18ec81d`. Runtime: scratch environment with `OPENBLAS_CORETYPE=Haswell
  OMP_NUM_THREADS=1`; the Falcon recording was streamed from a public link (not stored).
* Review: one fresh AI session, read-only, 19.10 12:45 to 12:52 UTC (`review/REVIEW_1.md` header), verdict
  PASS WITH CONDITIONS, blocking B1.

## 2. Result

* Best measured candidate `129415f` (F1a margin 0.01, H, S2): ride one-detector STOP frames/episodes/events
  130/30/28 -> 109/24/20 and low-kind episodes 4/6 -> 1/1 (`ride/episodes_base.json`, `ride/episodes_cand.json`);
  Falcon false STOP frames 12 -> 0 with all 1,360 person STOP frames kept and first person STOP at frame 2972,
  124.84 m (`falcon/score_base_positive_control.json`, `falcon/score_cand_129415f.json`); full gate exit 0 (`gates/gate_cand_129415f.txt`),
  chunked-gate ride alarm events 27 -> 18 and five-empty stop episodes 12 -> 11 (`gates/base_vs_cand_rows.txt`).
* Switch-off identity: 0 differing non-timing rows of 15,269 gate rows (`gates/A8_frames_base_vs_off.json`) and 0 of 4,443
  Falcon rows (`falcon/A8_off_vs_base.json`). Positive control: the same comparison for the candidate shows 2,716 differing
  rows (`gates/frames_base_vs_cand.json`).
* `HANDOFF.md` section 3 recommends not merging F1a as measured (review B1), and H' alone as shippable.
  The X3 battery was run for the base only (`probes/x3_base_aec88d2.json`); the candidate battery was not run (`HANDOFF.md` row A9).

## 3. Supports

* [`BACKLOG.md`](../../BACKLOG.md) card "F1 . Near-field low-object false STOPs" (line 443 onward) and
  [`DECISIONS.md`](../../DECISIONS.md) row 41 (F1a on, H' on, S2 off, from the captain's decision of 19.10).
* Assembly record: [integration_2026-10-19](../integration_2026-10-19/README.md) (table of lanes, line 14: F1 lane merged with all
  switches off, then the configuration decided). Docs front page [`docs/README.md`](../../README.md) line 71 and
  [`../README.md`](../README.md) line 37 list this folder.
* Reused by later work: `scripts/replay.py`, `scripts/cmp_frames.py`, `scripts/falcon_trace.py` (K1/K2, F1a repair, L16 and R3 reviews).

## 4. Contents (97 files)

* `HANDOFF.md`, `PROTOCOL.md`, `review/REVIEW_1.md`: lane handoff; protocol and amendments 1 to 8; the reviewer's text, unedited.
* `gates/` (13): per-gate text/JSON for base `aec88d2`, switches-off `1144150` and candidate `129415f`, row diffs, per-frame comparisons,
  `gate_frames_base_cand.tar.xz` (per-frame gate outputs, 4.2 MB).
* `falcon/` (13): Falcon scores, run metadata, `falcon_runs.tar.xz` (per-frame outputs of the runs).
* `ride/` (19 + `amend6_8/` 6): episode lists and attributions per variant; `ride_runs.tar.xz`.
* `probes/` (3 + `dynamic/` 1): standing-train and range probe summaries, base X3 battery; `synth/` (4): synthetic-bag comparison and meta.
* `six/six_base_replays.tar.xz`: base replays of the six recordings; `pictures/` (6 PNG): frames looked at for the ride and `doubleT_platform`.
* `scripts/` (28): replay, comparison, attribution, probe and driver scripts used above.

## 5. Caveats

* **Partly superseded.** The shipped configuration differs from `129415f`: F1a on without the cross-rail rule, S2 off (DECISIONS row 41).
  The F1a rail reference was repaired and then changed again: [f1a_b1_2026-10-20](../f1a_b1_2026-10-20/README.md),
  [f1a_acceptance_2026-10-20](../f1a_acceptance_2026-10-20/README.md), [f1a_bounded_2026-10-21](../f1a_bounded_2026-10-21/README.md)
  (switch `lowobj.rail_head_bounded` left off there), and CHANGELOG line 77 records that the "F1a completion" was reverted.
  I did not determine the final F1a state in 1.3.
* `HANDOFF.md` says the final HEAD `18ec81d` was not re-run through gate/Falcon with switches at 0; that proof is missing.
* Several paths in `HANDOFF.md` point to scratch directories of the container (`/tmp/...`, `/data/...`) that are not in the repository; no `gates/*.log` files exist (also noted in the review).
* The Falcon, ride and synthetic raw data are not in the repository; the compressed per-frame runs here are the only raw outputs.
