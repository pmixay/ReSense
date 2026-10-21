# Backlog: remaining criteria work

> **Purpose:** what is left to gain on the eight criteria of ТЗ §8 after the independent judgement of 13.10 (66/100): the
> work per role (priorities, code stop 20.10 23:59 MSK), one status table and one short entry per open card, with links to
> the evidence. Closed and superseded cards, the dated plans of 15–19.10 and the ledgers of 16–18.10 are in
> [`archive/BACKLOG_history_2026-10-19.md`](archive/BACKLOG_history_2026-10-19.md): this file as it stood before the
> clean-up of 19.10, word for word, with the full text (cause, tasks, acceptance check) of every card.
> **Audience:** P1 (to distribute the work), team · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-10-20 (evening): main `f56ad5e` with the **F1a completion** merged (decision 46):
> the local rail reference now compares like with like — the rail head's own top surface — so the B1
> repair's ride cost is gone (ride events **23 → 18**, STOP episodes **26 → 24**, alarm frames **111 → 102**,
> the pre-repair values) with no detection lost. Strict gate PASS without waivers, whole Falcon
> 4,443 rows identical, X3 0 of 260 comparisons failed, 363 affected tests pass; the integrity reseal
> follows the last code change. [`DECISIONS.md`](DECISIONS.md) rows 35–46;
> [record](evidence/f1a_completion_2026-10-20/README.md). Independent final-bundle acceptance and the
> release remain open.
> **Status:** current. "Current plan" below replaces every dated target: **P0** before the code stop, **P1** before the pitch,
> **P2** after 23.10. Section numbers of the old file are kept where other documents cite them (§1, §3, §4, §6, §9);
> §2, §5, §7, §8, §9d and §9e are in the archive.

## Current plan (checked 20.10): priorities, code stop 20.10 23:59 MSK

This section replaces every dated target below. **P0** must be in before the code stop (code, configuration, seal);
**P1** before the pitch on 23.10 (evaluation, documents, deck, rehearsals; no code); **P2** after 23.10 unless time
remains. **Current detector source: main's 19.10 integration, the user-authorized partial H1 improvement,
off-by-default K2 v5c from PR #43, the published F1a B1 repair, L16 A1 repair, R3 B2/B3 completion and the
F1a completion below**. H1 was published at `cefd4c4`;
its measured merge was `0f02b28`. The first R3 follow-up changed reporting; the final repair adds current-frame support for accumulation and preserves moving-cable STOP.
H1 is still **OPEN**
([publication](evidence/h1_partial_integration_2026-10-20/README.md)). The former integration branch
`claude/optimistic-mccarthy-z5nmwd` has already landed through PR #42.

**H1 independent closure check, evening 20.10: BLOCKED.** All 63 misses are now traced and independently
reviewed; actual wrong-selected-pair and no-rail tests are complete, with failures rather than acceptance.
Fresh replay on the F1a-completion source `520e7dc` preserves all 63 misses and the directed wrong-pair
counterexamples. An independently validated far-axis reference is still missing. See the
[current-source check](evidence/h1_current_source_2026-10-20/README.md),
[independent review](evidence/h1_final_review_2026-10-20/README.md) and
[publication summary](evidence/h1_publication_2026-10-20/README.md).

**PR #43 merged 20.10** ([PR #43](https://github.com/pmixay/ReSense/pull/43), squash `8c2bf51`): main now also carries
the off-by-default K2 v5c switch (`track.axis_joint_reach_dual`, 0 = off; code in `resense/track.py`,
`resense/detector.py`, `resense/config.py` and both YAMLs), P4's reviews, the N5 supplement and the data handoff.
Merging accepts nothing: v5c stays off and unmeasured on data, and the review findings stay reported/proposed. With every
K2 switch off, `8c2bf51` equals `a5b0ede` on 180 synthetic frames; the per-frame identity on the recordings (row ID) is
pending. P4 re-ran A1, B1 and B2 on `8c2bf51` (H1 on): identical results, so H1 does not change them. Later, F1a's
author repair was published as `f07f4b8` and merged with PR #43 at `060bde7`; its measured ride cost and independent
acceptance remain open ([record](evidence/f1a_b1_2026-10-20/README.md)). Real-data exposure T1/T4 remains open.
P4's findings concern pre-H1 source `4cf8e27`. L16 A1 was reproduced on current main and repaired (`4bf62f3`); the other findings remain subject to their own current-source verification.
Pinned reports: [shipping review][p4-shipping], [integration review][p4-integration], [N5][p4-n5], [data handoff][p4-handoff].

### Current detector switches (decisions 41, 44–45; checked against class defaults and both YAMLs)

| switch | state in current 1.2.0 source | why | follow-up owner |
|---|---|---|---|
| F1a local rail reference (`lowobj.local_rail_margin` 0.01, cross-rail rule off) | **on; completion merged 20.10** | ride low-kind false STOP episodes 4/6 → 1/1; the B1 repair's ride cost is removed (events 23 → 18, episodes 26 → 24, alarm frames 111 → 102 — the pre-repair values) with no detection lost | P3 author completion: the reference now reads the rail head's **own top surface**, the same feature the uncapped top reads; strict gate PASS, X3 0/260 failed, Falcon 4,443 rows identical, 363 affected tests pass ([record](evidence/f1a_completion_2026-10-20/README.md)); P4's review and exposure of the B1 repair are in [record](evidence/f1a_b1_2026-10-20/README.md) and [exposure](evidence/f1a_exposure_2026-10-20/README.md); independent final-bundle review remains |
| H′ mount cross-check (`cluster.mount_cross_tol` 0.5) | **on** | removes the 8 false STOP frames on the Falcon tunnel ceiling; 0 gate rows change | P4 review 20.10: the 8 frames confirmed on the raw returns, gate 0 of 15,269 rows, X3 0/260, no STOP lost on the person; the gate and X3 hardly arm the check ([record][p4-h-falcon]) |
| S2 settle (`tracking.settle_min_hits`) | off | can delay an object entering the gauge | — |
| R3 cable confirmation (P3) | **on; author work complete** | B2 co-moving physical targets correctly retain STOP; B3 uses current-frame support inside accumulated clusters (76 →78 m in the directed scene); no lost hit or added recorded alarm | B2/B3 author disposition complete; P4 final-bundle review 20.10: numbers reproduce from raw rows, **B2 recommended accept (captain's decision)** ([final-bundle review](evidence/p4_review_final_bundle_2026-10-20/README.md) §5); STOP can drop for a frame where the current frame has no return of the object ([completion](evidence/r3_completion_2026-10-20/README.md)) |
| L16/S3 orientation (P3) | **on** | directional recovery and ≤60k search retained; A1 false-forward cue repaired (`4bf62f3`), T1 measured | author acceptance complete: 27,580 paired rows; final F1a-main merge gate/X3/Falcon pass, 489 affected tests pass ([record][l16-open-air]); final-bundle P4 review remains |
| K2 axis on curves (`track.axis_joint_fit=false`), variant B = v5b without K1 | **held off** (decision 44) | original Falcon attribution was revised in PR #43 (122.27 m first person STOP, 37 person frames without STOP); the marked tunnels cube still loses STOPs (29 → 13 in the 2.5–250 m crop). `small_center` gate loss also remains | **P4 P0**: measured candidate and independent review, then captain's decision; v5c merged off by default ([report][p4-k2]) |
| K1 per-distance axis smoothing (`track.walls_smoothing_distance`) | off | standing train STOP at 100 m 82 → 255 / 260, but adds a false STOP on `doubleT_platform` (gate A measured on the integration branch) | P4, in the same package |
| Falcon clear-distance model (`small_target_limit`, falcon_prime) | **on**, only in the node's non-default `clear_range_policy` (conservative / small_candidate) | reports up to 48.2 m from the measured Falcon raster (density model, as for Pandar) instead of 0 | P4 review 20.10: 48.2 m reproduced, no decision changes; it lets the detector's clear distance through where there was 0, and that value is wrong in 38 frames at the recording's end ([record][p4-h-falcon]) |
| Falcon far range (`farrange.with_falcon_profile`) | off | person STOP 146 m (was 127) but rule 5.1(b) fails (9 vs 8 episodes), no long-range gain on injected targets | P3: improve (route-map variant, second boundary) |
| Dust guard (`dust.enabled`) | off | fails its own acceptance; 13 organizer dust frames checked on `4cf8e27`, no dust-attributed STOP/CAUTION | P1/P4: repeat on H1 main / final reseal source; old check is not a dense-dust robustness result |
| H1 positive collision core (`cluster.column_core_margin` 0.02) | **on**, partial improvement; independent acceptance **BLOCKED** | A-axis 82 →114/177; 63 misses remain on `520e7dc`. Actual wrong-pair scenes produce false core/STOP and inside misses | Independent review completed; P3/P4 must repair the measured failures and obtain a validated far-axis reference ([current check](evidence/h1_current_source_2026-10-20/README.md)); withdrawn `column_free_max_top=0` stays off |

### P1 · captain

| prio | work | state / depends on |
|---|---|---|
| P0 | Repair CI account billing / spending limit: main run [39382006663](https://github.com/pmixay/ReSense/actions/runs/39382006663) on `cefd4c4` failed before any step; GitHub's annotation confirms billing/limit | blocks E1 and a hosted check of the release; verified 20.10 |
| done (integrity) | Reseal the integrated R3 source with the full strict gate |40 frozen files; gate/X3/Falcon retained; independent P4 bundle acceptance is still P0 ([record](evidence/r3_completion_2026-10-20/README.md)) |
| P1 | E1: tag and release 1.2.0, verify the archive | needs CI and the reseal |
| P1 | Final numbers into the deck and speech; two rehearsals with P2, P3, P4 | needs the reseal |
| P1 | S5: bench of the final image on the available hardware (2–4 cores accepted) | needs an image |
| P1 | Read the 29.09 safety review yourself ([`CAPTAIN.md`](CAPTAIN.md) §3 item 8) | — |
| P0 | Decide B2: accept the R3 STOP for a thin in-gauge target that moves with the train (37 m), or keep the veto's CAUTION | P4 recommends **accept** (organizers 19.10: moving objects, everything in the gauge is an obstacle; no real-data exposure; [final-bundle review](evidence/p4_review_final_bundle_2026-10-20/README.md) §5) |
| P0 | Accept or reject the R3 reseal as the 1.2.0 bundle; then J1 (`release_day.sh`) and the G3 receipt ([`FINAL_RUN_HANDOFF.md`](evidence/heldout_2026-10-15/FINAL_RUN_HANDOFF.md) §6) | P4 found no blocker; conditions in the [final-bundle review](evidence/p4_review_final_bundle_2026-10-20/README.md) §1; the evaluation adapter for G3 does not exist (time-box decision D4) |
| P1 | Send the organizers the Falcon results and the 1.2.0 status if updates are allowed (O1 unanswered) | — |

### P1's agent · source measurements and integration

| prio | work | state |
|---|---|---|
| done | Current H1 main source: full gate without `--allow`, X3 and whole Falcon; A/C/cable probes and physical replay | measured `0f02b28`, same detector bytes as `cefd4c4`; gate PASS, X3 PASS (40 cases /29,765 rows), Falcon 4,443 rows ([record](evidence/h1_partial_integration_2026-10-20/README.md)) |
| done | Combined L16 repair + current F1a/K2-off main source | measured `afbf9fc`: fresh gate PASS without waivers, standard X3 PASS (40 cases /29,765 rows), whole4,443-row Falcon retained, 489 affected tests pass; all raw artifacts supplied ([record][l16-open-air]) |
| done (author acceptance) | R3 B2/B3 completion merged with `5d83c5b` | measured `0a472d6`, same production bytes at `47b220c`: gate PASS,208 non-timing metrics and18,329 gate/Set F rows exact; X3 40 cases /29,765 rows and whole Falcon4,443 rows exact;448 affected tests pass ([record](evidence/r3_completion_2026-10-20/README.md)) |
| P0 | After any accepted detector fix / K2 change: repeat affected checks and final gate/X3/Falcon on the exact reseal source; supply raw outputs for independent review | current checks are complete, final reseal acceptance is pending; the whole Falcon record independently reproduced on `cc6226e` and `f56ad5e` ([P4 review][p4-h-falcon]) |
| done | Organizer dust and all three marked bags on H1 main / final reseal source | **done 20.10 on `f56ad5e`** (R3 reseal bytes; 1,667 frames, 13 dust frames, [record](evidence/p4_dust_markers_final_2026-10-20/README.md)): 0 STOP, 0 detection, 0 warning at any of the 30 dust boxes (6 CAUTION from warnings 1.8–152 m away); all fields equal 1.1.0 except `clear` in 4 frames (F1a switch-on); M-1 on K2 off = the `8c2bf51` rows; 12 background false STOPs still present; guard stays off, not a dense-dust result |
| done (P4, 20.10) | Resolve or explicitly disposition full-suite failures before final acceptance | independent run on the `f56ad5e` bytes in the CI-like configuration (package installed, native kernels built): **2,387 of 2,387 passed**, 8 data-dependent tests deselected. The proxy-hook failure is a test-environment artefact (package on `PYTHONPATH` instead of installed: fails/passes reproduced both ways); the timing and node failures are wall-clock effects of the loaded first run (node: `clear_distance` 0.0 reproduced by a 0.7 s delay, fail-safe by design). Say "2,387 of 2,387 in the CI-like configuration, 8 need recorded data", not "all green" without that ([final-bundle review](evidence/p4_review_final_bundle_2026-10-20/README.md) §4) |
| P1 | Documentation clean-up and final numerical pass | backlog reconciled 20.10; final release numbers still depend on reseal/J1 |
| done | merge of the four agent lanes with identity proof; F1a and H′ switched on; decisions recorded | 19.10 |

### P2 · frontend / visuals

| prio | work | state / depends on |
|---|---|---|
| done (20.10) | Remove the unused reference photos from the repository root | all five root images deleted at the user's request; local gallery links removed |
| **done (21.10)** | ~~Short Falcon demo bag with the person: 280–330 s; verify actual playback and update handoff~~ | 499 exact CDR messages, archive/raw SHA-256 match, metadata + `ros2 bag info`, DDS/RViz; first person STOP in 3.79 s after command. [Receipt and checklist](evidence/p2_defence_2026-10-21/README.md), [handoff](evidence/p2_defence_2026-10-21/HANDOFF.md) |
| P1 (part prepared 21.10) | Second demo device (RViz / web) and fallback clip on 1.2.0 | local `31154690` image and actual Pandar/Falcon recording prepared; P1 selection, physical device and forced-switch rehearsal remain; see P2 checklist |
| P1 (review draft 21.10) | Deck visuals: range-by-geometry chart (straight / curve / double track) and Falcon slide | source-labelled PPTX/PDF prepared; historical range explicitly 1.1.0, final J1/P1 sign-off pending; see P2 checklist |
| P1 | Final numbers in documents and GitBook | dated corrections and local demo handoff prepared 21.10; final pass still depends on J1 |

### P3 · detector

| prio | work | state / depends on |
|---|---|---|
| done (author acceptance) | Repair L16/S3 shipping A1 and measure original-start exposure T1 | `4bf62f3`: 450 FAULT →450 GO, all446 positive rows kept; 120 raw frames /12 starts measured; 27,580 paired recorded rows exact; final combined source `afbf9fc`: gate/X3/Falcon pass, 489 affected tests pass ([record][l16-open-air]) |
| done (author acceptance) | Complete F1a: remove the B1 repair's ride cost without losing a detection | the reference reads the rail head's **own top surface**, the same feature the uncapped top reads; ride events 23 → 18, episodes 26 → 24, alarm frames 111 → 102 (the pre-repair values), 9 STOP frames removed and 0 added, every set O object unchanged, Falcon 4,443 rows identical, X3 0 of 260 failed, 363 affected tests pass ([record](evidence/f1a_completion_2026-10-20/README.md)) |
| done (P3 response); P0 bundle acceptance | Respond to P4 shipping A1/B1/B2/B3 and B4 mount-height limit | Current-source responses and limits delivered: F1a 72 arms /864 scans; R3 320 exact plain/traced rows; L16 1,350 analytic rows; 257 tests pass. B4 is a **confirmed support limit**, not repaired or universally accepted: +0.8 m height error at 5 m can hide a new hanging body; existing STOP retention is bounded by the 10 s keep cap and zone vote. P4 final-bundle review done 20.10 ([final-bundle review](evidence/p4_review_final_bundle_2026-10-20/README.md)); B4 and the captain's decisions remain separate ([P3 response](evidence/p3_review_response_2026-10-20/README.md), [review][p4-shipping]) |
| done (author acceptance) | Complete R3 B2/B3 on current main | current-only voxel/shape support in accumulated clusters; resolved moving cables are not demoted by static-world ego-veto; strict gate, paired X3/Falcon/E6,576 analytic rows and448 affected tests verified ([record](evidence/r3_completion_2026-10-20/README.md)) |
| done | Investigate Set F cable sustained median 34.2 →17.8 m and repair aggregate-only reporting | fresh 30-sequence paired run, 3,060 rows/side: 0 lost hits, 9 added cable hits, no false-detection increase; coverage 2/6 →4/6, original-success cohort unchanged ([record](evidence/r3_sustained_2026-10-20/README.md)) |
| P1 | Q&A preparation and mock jury: the algorithm, curves (what K2 ships and costs), why not 300 m, dust, the second lidar, false alarms; technical check of `ALGORITHM.md` and the slides | P4 pack with stale-answer corrections and 14 new questions: [`MOCK_JURY.md`](evidence/p4_review_final_bundle_2026-10-20/MOCK_JURY.md); P3's set and the 20.10 / 22.10 rehearsals open |
| P1 | H1: obtain a validated far-axis reference and repair the attributed misses and actual wrong-pair failures | **OPEN/BLOCKED**. Independent audit/review complete; all 63 misses and wrong-pair failures reproduced on F1a-completion `520e7dc`, with 104 H1 tests passing ([current check](evidence/h1_current_source_2026-10-20/README.md)) |
| P2 | F1a B1: author repair and its completion both implemented on user request; the independent final-bundle review and the captain's decision on the (now removed) ride cost remain ([completion](evidence/f1a_completion_2026-10-20/README.md)); Falcon far range (route-map variant, second boundary); M1 moving-object probes (the organizers: objects may move); C1, R1/R2, S4, N6 | F1a worked on 20.10; other items after 23.10 |

### P4 · data / evaluation

| prio | work | state / depends on |
|---|---|---|
| done (T1 measurement) | Measure real-start exposure to L16/S3's open-air FAULT | first10 raw frames of all12 starts independently decoded: 0/120 A1 exposure, minimum above-sensor share 28.2693%; known analytic A1 detected as positive control ([record][l16-open-air]) |
| P0 (T4) | Measure F1a capped-top exposure and hand findings to P3 | registered in [data handoff][p4-handoff]; remains separate from completed L16 T1 |
| **P0 (K2/K1)** | **Keep both off.** K2 v5c revision 1 is in main, off (PR #43 merged); registered gate/X3/Falcon/standing-person/marked-bag rows are not run. Resolve both the corrected Falcon loss and the in-gauge tunnels cube loss, set O `small_center`, K1 false STOPs and the review items. P3 or a fresh agent reviews P4's candidate; captain decides switch-on | [existing package](evidence/k1_k2_gauge_2026-10-19/P4_PACKAGE.md), [v5c][p4-k2], T2/T3 in [handoff][p4-handoff] |
| P0 | Complete acceptance of what ships on, including **H1**: resolve reported L16/S3, R3 and F1a findings, verify fixes on recordings and review combined source | pre-H1 synthetic shipping review in main (PR #43); its A1/B1/B2 re-run on H1 main `8c2bf51` gave identical results before the A1 repair; **not clean acceptance**, reseal still blocked ([review][p4-shipping]) |
| done (P4, 20.10) | Finish independent integration verification from raw outputs of the exact combined source | R3 reseal `f56ad5e` re-derived from raw rows: gate 15,269 + Set F 3,060 rows, 208 of 208 metrics, X3 29,765 rows / 260 comparisons, Falcon 4,443 rows, 0 differences, planted-change controls found; a third run by P4 on the same commit agrees on every decision-bearing field. H1 raw archives (`0f02b28`): hashes and sources verified, physical replay repeated on `f56ad5e` (320 of 320, 0 of 280). No blocker; H1-specific review stays BLOCKED ([review](evidence/h1_final_review_2026-10-20/README.md), [current check](evidence/h1_current_source_2026-10-20/README.md)); conditions in the [final-bundle review](evidence/p4_review_final_bundle_2026-10-20/README.md) §1 |
| P1 | On the final seal: J1 (retarget [`RELEASE_DAY.md`](evidence/rejudge_2026-10-16/RELEASE_DAY.md) from 1.1.0) and the G3 held-out run by a fresh agent | J1 retargeted 20.10 to the R3 seal with `release_day.sh` (identity step tested; the rest untested, no recordings; Docker waits for the image); G3 handoff written ([`FINAL_RUN_HANDOFF.md`](evidence/heldout_2026-10-15/FINAL_RUN_HANDOFF.md)): the registered validator fails on Linux (CRLF), fixed by a wrapper, the evaluation adapter does not exist; **G3 not run** |
| done with findings (P4, 20.10) | N5: review the merged marker supplement, then re-score final 1.2.0 | the 34 cube rows are right but the scorer rejects the file (`n_points: null`; fix before use); 3 of the 12 flagged rows match under the looser STOP-matching rule, 6 lie 3.4–5.0 m in front of marker 13; N5 report of the final run equals v1.1.0 in all three bags ([final-bundle review](evidence/p4_review_final_bundle_2026-10-20/README.md) §6) |
| P1 | Mock jury at both rehearsals | pack ready ([`MOCK_JURY.md`](evidence/p4_review_final_bundle_2026-10-20/MOCK_JURY.md)); rehearsals 20.10 and 22.10 not yet held |
| P2 | The dust guard if the organizers' dust re-check fails; X2 false-STOP ledger | after 23.10 |

## 1. How to use it

* **Roles** (the repo names roles, not people; [`PLAN.md`](PLAN.md) §roles, ownership map [`CAPTAIN.md`](CAPTAIN.md) §8):
  **P1** captain (ROS node, Docker, CI except pytest, release, docs, the detector seal, the pitch) · **P2** frontend /
  visualization (`web/`, RViz, deck visuals, video) · **P3** CV engineer (`resense/` detector modules, `native/`, config
  values) · **P4** data / evaluation (datasets, metrics, eval scripts, regression gate, labels, tests). If nobody takes a
  role, P1 runs its items with agents.
* **Mode:** **H** needs a human (organizers, a tag push, hardware, rehearsal); **A** an agent can do it and a human merges;
  **H+A** both. **Priority:** P0 / P1 / P2 as in "Current plan". **Points** in the archive are the judge's own deductions
  (`docs/evidence/judgement_2026-10-13/scores.json`) that an item can win back: estimates, not additive.
* **Every detector item** (anything under `resense/`, `native/`, `configs/`, `ros2_ws/src/resense_ros/config/`, `setup.py`,
  `pyproject.toml`) follows [`DETECTOR_FREEZE.md`](DETECTOR_FREEZE.md): branch from the latest seal, acceptance test first,
  full regression gate exit 0 without `--allow`, independent safety review, then P1 reseals (the version bump is inside the
  reseal). Detector items ship as **one bundle per seal**.
* **Evaluation and judging runs** (P4, J1, X-series) never modify detector code (`resense/`, `native/`, `configs/`, the ROS
  package); detector changes are P3's, made and sealed separately. Nobody runs or tunes on the held-out G3 set except the
  fresh agent of the final check ([`CLAUDE.md`](../CLAUDE.md)).
* **Data and tools:** recordings and caches as in [`VM_GUIDE.md`](VM_GUIDE.md) §2; the gate is `scripts/regression_gate.py`
  (`--cache <cache> --jobs 2 --baseline <the baseline of the current seal>`, ~10 min on 4 vCPU); the judge's tools are in
  `docs/evidence/judgement_2026-10-13/scripts/` (`range_test.py`, `probe.py`, `judge_runner.py`; their `run_*.sh` wrappers
  hard-code the judge's paths). To run a worktree's detector set both `PYTHONPATH=<worktree>` and `RESENSE_REPO=<worktree>`
  and check `resense.__file__`: the editable install otherwise imports the main checkout silently.

## 3. Status of every item (checked 20.10)

Priorities are those of "Current plan"; items it does not list are P2. Section 2 (the 16.10 integration ledger), the
point estimates and the former dates of every row are in the archive.

| id | item | state | prio |
|---|---|---|---|
| CI | repair CI (account billing) | checked main run on `cefd4c4` fails before steps with billing/spending-limit annotation; blocks E1 | P0 |
| reseal | reseal 1.2.0 after the last code change | the F1a completion reseals the 40 frozen files on the strict full gate; final independent bundle acceptance remains P0 | integrity delivered; P0 review |
| L16/S3 | ring-free orientation + bounded orientation search | **on; A1 repair/T1 delivered**, paired recordings/gate/X3 pass; F1a-main merge verified on gate/X3/Falcon +489 tests; general unsupported mounts and final-bundle review remain separate ([record][l16-open-air]) | delivered; P0 bundle review |
| R3 | thin cables | **on; author completion delivered**: B2 correct STOP label and order-independent moving-cable confirmation, B3 current-frame support in accumulation; first/held E6 86.25/61.28 m, hanging48.19 m float32 (35.1 m compact); gate/X3/Falcon unchanged,448 affected tests pass | delivered; P0 bundle review |
| F1 | near-field low-object false STOPs | F1a and H′ **on**, S2 settle off. The B1 repair's ride cost is **removed** by the F1a completion: the reference reads the rail head's own top surface, so the head's own top is no longer reported as an object's body (ride 23 → 18 events, 26 → 24 episodes, 111 → 102 alarm frames — the pre-repair values; no detection lost, set O and Falcon identical). Strict gate PASS, X3 0 of 260 failed ([completion](evidence/f1a_completion_2026-10-20/README.md)); the independent final-bundle review remains | delivered; P0 bundle review |
| K1 / K2 | gauge on curves, standing train | **both off** (`walls_smoothing_distance=0`, `axis_joint_fit=false`), decision 44; v5c merged off by default, real-data acceptance pending | P0 / P2 |
| N3 | dust | guard **off** (fails acceptance); organizer dust checked on `4cf8e27`, H1/final-source replay pending | P0 |
| N7 | Falcon to 300 m | `farrange` **off**: person STOP 146 m (was 127 m), no gain on injected targets, rule 5.1(b) fails | P2 |
| H1 | tall narrow objects (the open High finding, 8.1) | **OPEN/BLOCKED after independent review**. A-axis 114/177, all 63 misses attributed; actual wrong-pair false core/STOP and inside misses confirmed. Fresh F1a-source check: all 858 directed/A outputs identical. Far-axis reference and repairs remain ([record](evidence/h1_publication_2026-10-20/README.md)) | P1 |
| N5 | labels of the new synthetic bags | initial labels done; organizer markers independently checked; merged PR #43 supplement adds cube/flags 12 rows; final scoring pending | P1 |
| J1 | re-judge the final seal | retarget [`RELEASE_DAY.md`](evidence/rejudge_2026-10-16/RELEASE_DAY.md) from 1.1.0; needs the reseal | P1 |
| G3 | held-out run by a fresh agent | spec registered, no run; on the final 1.2.0 seal | P1 |
| E1 | tag and release 1.2.0 (1.1.0 is not released) | needs CI, the reseal and the final image | P1 |
| S5 | bench of the final image | 2–4 cores accepted; needs an image | P1 |
| PT1 / PT2 | pitch content; live demo and two rehearsals | deck text updated 19.10; rehearsals **planned** 20.10 and 22.10, no completion receipt in reviewed records; visuals/final numbers after reseal | P1 |
| D1 | stale statements in the docs | 19.10 clean-up and 20.10 backlog reconciliation; final numbers after reseal/J1 | P1 |
| O1 | questions to the organizers | sent; partly answered 19.10 ([`answers.md`](organizers/answers.md) §12); open: filter, playback, O1 | P1 |
| M1 | moving-object probes (new 19.10) | historical crossing/receding probes and 12 H1 train-approach physical sequences exist; expanded chaotic-object battery / final-seal replay pending | P2 |
| C1 | CAUTION policy | v2 failed offline; the answer "in gauge = obstacle" settles it for in-gauge objects | P2 |
| R1 / R2 | 0.3 m objects from ~45 m; sparse far objects | the five cheap overrides were rejected 15.10; wait for X1-style attribution | P2 |
| F2 / X2 | far-onset false STOPs; false-STOP ledger | not started | P2 |
| S2 / S4 | 360° per-frame cost; dual-return duplicates | not started (S2 here is the card, not the F1 lane's settle switch) | P2 |
| N6 | late STOP on the platform person | candidate rejected, **off**; object-dependent visibility hides conflicting rail evidence; 60 m target/uncertain box rows also unresolved | P2 |
| G1 / G2 / T1 | rule provenance; doubt model; next-seal clean-up | not started | P2 |
| D2 | archive the 28.09 layer | the documents are moved (19.10); personal-path tests and orphan scripts open | P2 |
| recorded outcomes | historical integration H0–H6, S1, X1, X3, C2, N1, N2, N4 | 16–18.10 ledger (including withdrawn H1/free-top and failed S1) in the archive; **not closure of current H1/High**. Fresh X3 also passes on combined H1 source | recorded |

## 4. Order up to the defence (23.10)

Superseded by "Current plan" at the top: the calendar of 15–22.10 (cut-off, bundle `det/1.2.0`, rehearsal dates) and the
per-role queues of 15–16.10 are in the archive. The anchor of this section is kept because evidence READMEs link it.

## 6. Open cards

One short entry per open card; the full text (evidence, cause, tasks, acceptance check) is in the archive under the same id.

### Organizers and release

#### O1 · E1 · E2 · Release and organizers
* **O1** (pitch format; whether an updated version counts): sent; answered in part on 19.10 ([`answers.md`](organizers/answers.md)
  §12, [`QUESTIONS.md`](QUESTIONS.md)). Open: the filter (Q3), bag playback (Q5) and O1 itself; P1 sends the Falcon results
  and the 1.2.0 status if updates are allowed.
* **E1** tag and release **1.2.0**: needs a working CI, the reseal and the final image. P4 accepted the merged B4 source
  `0779db7` on 19.10 ([review](evidence/p4_review_b4_merged_2026-10-19/README.md)); that is no release. Done when
  `scripts/verify_release.sh v1.2.0` exits 0 from a logged-out machine and `detector_freeze.py verify` passes on the tag.
* **E2** offline rebuild from the release archive: local PASS ([evidence](evidence/offline_rebuild_2026-10-15/README.md));
  the release-workflow step has not run on a tag.

### Speed and launch

#### S2 · 360° per-frame cost (native single-pass decode, then a per-stage profile)
Judge, 4 vCPU: decode + detect p50 78–86 / p95 106–119 ms, 18–34 of 200 frames over 100 ms. Plan: `rs_decode_xyzir` in
`native/`, profile per stage, worker thread only if p95 stays above 100 ms. P2, not started.

#### S3 · Cap the orientation-search cost
Implemented with L16 (sample once to ≤ 60,000 points before the candidate loop), **on**
([evidence](evidence/l16_s3_2026-10-19/README.md)). P4 A1 was reproduced on main and repaired at `4bf62f3`:
the signed-forward cue now also requires a bounded forward cone, so the ground half-space cannot claim forward -Z.
Analytic open-air startup changes 450 FAULT →450 GO; all446 matched positive rows remain. T1 is measured on120 raw
frames /12 original starts (no A1 exposure, known analytic positive control detected). Paired 24-rotation startups and
full representative recordings are exact over27,580 rows per side. Original paired gate/X3 pass; final F1a-main source
`afbf9fc` also passes fresh gate/X3/Falcon and489 affected tests ([record][l16-open-air]). General
ring-free/unknown physical mounts without independent orientation evidence remain unsupported; final-bundle review/reseal is separate.

#### S4 · Dual-return duplicates: the track model counts raw points
Judge probe: deduplication moves squareT CAUTION 446 → 99 frames and doubleT_obstacle STOP 193 → 189. Bisect with
`probe.py --dedup`; go / no-go is the captain's. P2, not started.

#### S5 · Available-hardware bench of the final image including the literal player
2–4 cores are accepted (captain, 17.10); `scripts/bench_8core.sh` (historical name, no core-count check), results with the
hardware named. P1, needs an image.

### Decision outputs

#### C1 · CAUTION policy: one shared decision function, CAUTION only where it carries information
Shared v1 is selected; offline v2 FAILED (30.46 % CAUTION against ≤ 25 %, 19 lost labelled alerts;
[screen](evidence/caution_policy_2026-10-15/EVIDENCE.md)). The organizers' answer ("everything in the gauge is an obstacle")
settles in-gauge objects: `CAUTION` stays for objects outside or at the edge. P2 (after 23.10); re-scoped by P1.

### Evaluation tooling (P4 lane)

#### G3 · Pre-registered held-out test battery: spec now, one run on the final seal
Specification registered ([`heldout_2026-10-15`](evidence/heldout_2026-10-15)); no run. A fresh agent that did no tuning runs
`range_test.py` and `probe.py` once on the final 1.2.0 seal; nobody tunes on it. P1 priority.

#### J1 · Re-judge the shipped seal with the judge's tools; one table against 13.10
Dry run reproduces 13.10, range jobs and six bags were pre-built on 1.1.0 ([runbook](evidence/rejudge_2026-10-16/RELEASE_DAY.md));
the pin to 1.1.0 is dropped. The runbook has a 1.2.0 note, but its commands/expectations still need retargeting to the
final 1.2.0 seal (old 1.1.0 identities are not current); Docker steps wait for the image. P4, P1.

#### N5 · Labels and scoring for the new synthetic bags
Done 17.10 ([labels](evidence/n5_labels_2026-10-17/README.md)); on 19.10 checked against the organizers' markers
([evidence](evidence/synth_markers_2026-10-19/README.md)): 1,672 of 1,684 rows match, 12 sparse rows do not, one object is
missing (first small cube of `synthetic_tunnels`, marker id 18, frames 4–60). Main still needs the supplement and scoring
against markers. **20.10 update:** PR #43 (merged) adds a non-destructive supplement with 34 cropped
cube rows and the 12 flagged rows, plus per-object scoring of historical runs; review and scoring
of the H1/final source are pending ([supplement][p4-n5]). Independent intake also verifies all 1,667 cloud messages
byte for byte against the old archive; marker boxes give obstacle support, not surveyed rail-axis truth
([intake](evidence/organizer_markers_2026-10-19/README.md)).

#### X2 · False-STOP ledger with pass-by ground truth and a fast window replay
36 episodes / 173 STOP frames in 13,558 empty frames (~91/h); enabler for F2 and K2. P4 lane, P2 priority.

### Detector: range and false alarms

#### H1 · Tall narrow objects (the inherited High finding, 8.1)
**OPEN, partially improved (20.10).** The old free-top fix remains withdrawn
([withdrawal](evidence/integration_2026-10-16/h4_fixes/columns/WITHDRAWAL_RESULTS.md)). A new positive current-frame
collision core with fresh rail anchors is implemented (`column_core_margin=0.02`); it releases only column suppression
after ordinary uninterrupted confirmation. A-axis improves **82 ->114/177**, leaving **63 visible unmatched frames**.
All 32 stationary physical scenes match after confirmation; 280 historical outside controls have no false STOP. Nominal moving
physical scenes have continuous STOP from **130.8 /135.2 m**, a simulation result only. Merged source `0f02b28` passes
the full gate; fresh combined-tree X3 passes 40 cases /29,765 rows. The full suite retains one inherited proxy-hook
failure (2,276 passed +17 subtests). The user explicitly authorized publishing this partial improvement in main without
claiming closure. Still needed: independently validated far rail axis/trajectory, remaining miss resolution,
repair of the observed failures and independent final acceptance/reseal.

**Evening 20.10 independent review: completed, acceptance BLOCKED.** Fresh A replay on `f56ad5e`
checks all 340 raw results with exact plain/traced equality and independently matches all 177 visible rows.
The 63 misses have actual executed primary mechanisms: **43 column hold, 9 axis limit, 7 zone-vote delay,
2 merged wall-segment filters, 1 height-reference limit, 1 tracker confirmation**. All labels are checked
against full snapshots; primary labels do not claim a unique counterfactual cause
([miss audit](evidence/h1_miss_audit_2026-10-20/README.md)).

The new physical matrix actually selects distractor rails. Four outside-target sequences produce
**56 false-core rows /40 false target-STOP rows**; four inside-target sequences miss all 14 scans each.
For the ±1.50 m targets the entire body is outside the true host envelope by at least **0.22 m**.
Rail-free cold starts produce no fresh core in 42 scans, but a visible target's old STOP survives rail loss
for four scans through the unchanged zone vote. These are bounded synthetic results, not a prevalence
estimate or universal guarantee ([rail limits](evidence/h1_rail_limits_2026-10-20/README.md)).

A fresh independent reviewer re-derives all 63 labels, 837 rail-estimator calls and 518 directed outputs;
the far-reference audit checks 11 raw databases and all 36 failed direct comparisons. The supplied
Falcon and organizer-folder links identify the already investigated data, not an external rail/pose
reference ([reference audit](evidence/h1_independent_2026-10-20/README.md),
[final review](evidence/h1_final_review_2026-10-20/README.md)).

After concurrent F1a completion, fresh plain replay on pinned **`520e7dc`** reproduces **all 858 outputs**
(A340 + directed518) exactly outside timing, including all 63 miss IDs and wrong-pair failures;
104 H1 tests and the current 40-file F1a integrity seal pass
([delta acceptance](evidence/h1_current_source_2026-10-20/README.md)). No H1 repair or safety reseal is
claimed. Required next input: independently checked left/right rail-head geometry and host-path identity
at 100–150 m in identified A/C frames, with uncertainty, or validated synchronized relative SE(3) and
extrinsics/error budget. The **63 misses remain unresolved**.
[Publication](evidence/h1_partial_integration_2026-10-20/README.md),
[repair](evidence/h1_reference_2026-10-19/README.md),
[rejected reference attempts](evidence/h1_trajectory_2026-10-19/README.md).

**H1-REF — required missing input, explicitly confirmed by the user (20.10). Status: MISSING / BLOCKED.**
To continue H1 validation, obtain either:

1. **Verified geometry of both rail heads and the correct host-path identity at 100–150 m in specific A/C
   frames, with quantified spatial uncertainty**; or
2. **An independently verified synchronized trajectory**, with sensor extrinsics and an error budget,
   sufficient to transfer independently checked rail-head observations into those A/C frames.

Here **A** is `roundT_squareT_pressureGate_squareT` and **C** is `roundT_pressureGate_roundT`.
The handoff must identify the source recording, frame IDs and timestamps, coordinate system and
sensor transforms, measurement support, uncertainty, and the independent validation method/reviewer.
The supplied Falcon and organizer-folder links have already been checked; access to those recordings
alone does not satisfy H1-REF. Until the spatial input is received and independently validated,
**H1 remains OPEN/BLOCKED**. Receiving it enables the remaining repairs and acceptance checks;
it does not by itself resolve the 63 misses or the wrong-pair failures.

#### K1 · Standing train: far axis jitter → STOP flicker at 100–150 m, perturbation-sensitive platform false STOPs
Distance-based smoothing of the wall fit is **off** (`track.walls_smoothing_distance=0`). Historical v4: standing person
at 100 /150 m 255 /197 STOP frames (base 82 /90), but full gate exit 1 (19 rows) and added false STOPs. No accepted
replacement is enabled. P4's candidate package needs measured rows, independent review and the captain's decision
([package](evidence/k1_k2_gauge_2026-10-19/P4_PACKAGE.md), [gauge stability](evidence/gauge_stability_2026-10-18/README.md)).

#### K2 · Curve and double-track axis — read the round-3 evidence first
Joint axis fit is **off** (`track.axis_joint_fit=false`), decision 44. Historical v3/v4 improves wall error on C but loses
person range; variant B also loses set O `small_center` and the marked in-gauge tunnels cube. P4's PR #43 corrects the
old axis-dependent Falcon matching: first person STOP **122.27 m**, 37 person frames without STOP, instead of the
original 112.97 m /158-frame-loss report. That correction does **not** validate switch-on. Its K2 v5c revision 1 is
off by default (in main since PR #43); registered real-data rows (including the cube, which v5c does not repair) remain pending.
P4 authors; P3/fresh agent reviews; captain decides ([v5c][p4-k2], [N5][p4-n5], T2/T3 in [handoff][p4-handoff]).

#### R1 · R2 · Small and sparse far objects
R1: 0.3 m objects confirmed only from ~45 m (hardware rule, low stage ends at 60 m). R2: the point bar leaves an 80–100 m
hole for 0.5 m cubes. The five cheap config overrides were rejected 15.10 ([range screen](evidence/range_screen_2026-10-15/README.md));
a new candidate needs X1-style attribution first. P3, P2.

#### R3 · Thin cables
Done by P3, **on**: set O hanging 5 cm first STOP 30.1 → 35.1 m (held from 40.0 m), standing 5 cm cable first / held 59.8 /
43.4 → 86.25 / 61.28 m on the node replica ([initial evidence](evidence/r3_h1_2026-10-19/README.md)).
**Set F aggregate concern resolved on 20.10:** the conditional median remains **34.2 →17.8 m**, but success coverage
grows **2/6 →4/6**. The original-success cohort stays **19.0 /49.5 m**; two new successes enter at **16.6 /16.4 m**.
Fresh R3-off/on replay covers all 30 fixed sequences (3,060 rows per side): no lost matched hit, nine added cable hits,
no false-detection increase. Reporting now retains per-sequence evidence and prints paired cohorts beside the original
scalar; all 208 historical non-timing gate metrics and every gating bit are unchanged
([follow-up](evidence/r3_sustained_2026-10-20/README.md)).

**20.10 R3 author completion (`0a472d6`, merged with main `5d83c5b` at `47b220c`):**
**B2 disposition:** P4's co-moving physical boxes occupy the gauge and are real obstacles under the organizers'19.10
answer. Retain their STOP; a fully resolved current-frame cable run is no longer dependent on whether ego-veto becomes
ready first. **B3 repaired:** accumulated clusters carry current-only footprint, height and distinct strict voxels;
historical/duplicate/flat/sparse/outside support cannot shorten confirmation. Directed speed-known80 m approach first
STOP76 →78 m; co-moving80 m target0 →16/18 matched rows. All old analytic detection payloads retained across576 rows.
Fresh gate PASS without waivers:208 non-timing metrics,15,269 ordinary rows and3,060 Set F rows exact; fresh X3
40 cases /29,765 rows /260 comparisons and whole Falcon4,443 rows exact. E6 retains86.25/61.28 m and34/59 matched
visible rows; node-faithful Set O hanging retains48.19 m /19 rows.448 affected tests pass; full suite2386 passed,
one inherited proxy-hook failure reproduced on both sources. Raw archives, actual-return trace equality, planted-loss
controls and integrity seal supplied ([completion](evidence/r3_completion_2026-10-20/README.md)).
**R3 implementation and author acceptance are complete.** Independent final-bundle P4 review remains separate;
general M1 is still open (the directed receding80 m scene retains only three matched STOP frames).

#### F1 · Near-field low-object false STOPs at the rail-head plane
F1a local rail reference **on** (ride low-kind episodes 4/6 → 1/1; review finding B1, a long low object along one rail,
accepted; P3 improves it), H′ mount cross-check **on** (8 false STOP frames on the Falcon tunnel ceiling), S2 settle off
([handoff](evidence/f1_false_alarms_2026-10-19/HANDOFF.md)). Gate and whole Falcon are complete on `4cf8e27` and the
combined H1 source. **New P4 shipping B1** is distinct from the previously accepted long-object B1: a low cluster's top
is capped at the model envelope floor, so a raised local rail reference can weaken a genuine low obstacle (8 →0 STOP
frames in P4's synthetic case). The user-requested repair below replaces that capped-top check; P4 T4 measures real
exposure and independent acceptance remains pending ([review][p4-shipping], [handoff][p4-handoff]).

**20.10 author repair (published to main on user request, `f07f4b8`):** both B1 mechanisms are addressed with independent low-footprint-free
rail support and the observed full-footprint top. Fragment controls retain ordinary confirmation (all 12 two-rail tracks);
the P4 raised-rail box regains its 8 STOP rows. Full gate against the seal baseline **PASS without exceptions**; Set F
matches starting main, Falcon's 4,443 detection/warning rows match. There is a measured ride cost against starting main:
chunked gate events **18 →23**, STOP episodes **24 →26**; the continuous replay adds 11 STOP rows (**109 →120**),
with low-kind episodes **1 →3**. This is **not** clean non-regression against main or final P4 acceptance; the ride
trade-off needs disposition before final acceptance/reseal. Publication is not independent acceptance.
[Repair, source receipts and raw checks](evidence/f1a_b1_2026-10-20/README.md).
Author X3 also passes all 40 cases /29,765 rows with identical STOP row sets; this dirty-source byte-identified run
does not replace final committed-source acceptance or independent P4 review.
Publication was merged with current remote main (`2a58369`, K2 v5c still off) at `060bde7` without textual conflicts;
219 affected F1a/K2 tests pass on that combined source ([publication](evidence/f1a_b1_2026-10-20/PUBLICATION.md)).

**20.10 F1a completion (author work, merged into main on user request, decision 46):** the repair's ride cost is
**removed** and nothing is lost. The cause was measured in the raw frames: the frame's rail returns are **bimodal** —
the lower mode is the rail *web*, the upper mode the head's *top surface* — and on the ride both rails read both modes
synchronously, so the model's rail-head plane sits about 0.1 m below the real head top. The F1a reference was the
**median** of the band (the web), while the repair's uncapped top reads the head's top: the comparison was between two
different features, and the head's own top was reported as an object's body. The completion reads the **same feature**
on both sides — the head's top surface in the candidate's own lateral band, from low-free points only, supported by at
least two distinct returns, on the same height window the top uses. Measured on the committed source: chunked ride
**events 23 → 18, STOP episodes 26 → 24, alarm frames 111 → 102** — exactly the pre-repair values; **9 STOP frames
removed, 0 added**; every set O object unchanged (`long_low_on_rails` 52 frames / 87.2 m, `small_on_rail` 23 / 42.7 m,
`thin_hanging` 18 / 35.1 m), `doubleT_obstacle`'s labelled hits unchanged, the other five recordings identical except
`doubleT_platform`'s 2 advisory frames; the P4 raised-rail scenes and the empty controls unchanged (32 scenes, 0
differing rows); the whole Falcon **4,443 rows identical**; X3 **0 of 260 comparisons failed** over 40 cases; **363
affected tests pass**. The new rule can only reject a cluster the **pre-repair** rule rejected, so its rejection set is
a subset of the pre-repair rule's — which on the recordings held no real object (T4's independent visual exposure).
13 of P4's 98 flipped clusters stay unexplained (a head whose top no ring crosses in the window); the rule then fails
open. This is **author evidence on committed source**, not independent P4 acceptance and not a release:
[completion, protocol and raw checks](evidence/f1a_completion_2026-10-20/README.md).

#### F2 · Far-onset false STOPs at ≥ 100 m (half of all episodes)
18 of 36 episodes; every earlier filter cost range. Needs the X2 audit and the final seal. P3, P2.

#### N3 · Dust / suspension
Generator and complete measurement done 18.10 ([evidence](evidence/n3_dust_2026-10-18/README.md)); the guard
(`resense/dust_guard.py`) is written and **off** (`dust.enabled: false`): on the registered battery only 6 of 15 empty-recording
rows pass ([handoff](evidence/n3_dust_fix_2026-10-19/HANDOFF.md)). The organizers' dust (11 bursts, 13 frames) causes no
dust-attributed `STOP` or `CAUTION` on 1.1.0 and was re-checked on `4cf8e27` (all 1,667 marked-bag frames). That completes the
pre-H1 integration check, **not** the H1/final-reseal check, which remains pending. Independent raw subtraction verifies
31 organizer-marked dust returns in platform frames 0–314; this tiny-particle case is not evidence of dense sustained
dust robustness ([intake](evidence/organizer_markers_2026-10-19/README.md)). P4 acts if the final-source check regresses.

#### N6 · Late STOP on the synthetic person at the platform
Candidate revision 3 (first STOP 44.01 →51.12 m) rejected, **off** (`track.rails_axis_extension=false`). The decisive
source check found that removing object points exposes farther conflicting rail evidence (frames 145/146), so support
is not independent of the object. The 60 m target is also unmet and the uncertain false-STOP bound widens 0–38 →0–47;
the narrower-band remedy was rejected ([evidence](evidence/n6_platform_2026-10-18/README.md)). P3, P2.

#### N7 · Stable obstacle detection to 300 m on the Falcon Prime
`farrange` (far straight axis, crop 400 m) is **off**: on the real recording the person's first STOP is 146 m (was 127 m)
with 0 false episodes, but there is no long-range gain on injected targets and rule 5.1(b) fails (9 vs 8 STOP episodes).
**No 300 m and no 250 m claim.** To improve: a route-map variant (`declared_straight_to`) or a second boundary. P3, P2
([report](evidence/falcon_long_range_2026-10-19/REPORT.md), [check](evidence/falcon_head_check_2026-10-19/README.md)).

#### M1 · Moving-object probe set (new 19.10)
The organizers: objects may move, even chaotically. A probe set (crossing, receding, lateral random walk, stop-and-go at
30–150 m) through the judge's ray-cast tool, measured on the final seal; any rule that loses an in-gauge moving object is
fixed or switched off (`ego_veto`, weak far evidence, settle, dust guard). P3 + P4, P2.
The 12 H1 physical sequences cover a train approaching a stationary body at 22 m/s and variants; they do not close
this independently moving/chaotic-object requirement. Historical J1 prebuild also includes crossing/receding probes;
the expanded battery and final-seal replay remain open. P4's R3 carried-along-target finding is an additional synthetic
interaction case, not completion of the M1 battery ([review][p4-shipping]).

### Generalization and technical quality

#### G1 · G2 · T1 · After the final seal
**G1** ablate every rule justified by a named recording; repeat the provenance inventory on the final seal
(historical audit: 333 YAML leaves, 30 cite a recording; ~17 full gates, not a count of today's expanded config).
**G2** doubt model: cross-fit on the current detector, keep only if it earns its place. **T1** remove dead switches, move
code-only parameters into the YAML, the decision function into `resense/`. P3, P2.

#### D2 · Archive the 28.09 layer
The documents are moved to `docs/archive/2026-09-28/` (19.10); open: tests with personal paths (`git grep -nE 'D:/Datasets|C:/Users' -- tests scripts resense`)
and orphan scripts. P2.

### Pitch (23.10)

#### PT1 · Pitch content for the shipped seal
Deck text updated 19.10 (P1, separately); open: the range-by-geometry chart (straight / curve / double track) from J1, the
Falcon slide, final numbers after the reseal; ≤ 80 words per slide. Queue: [`web/P2_STATUS.md`](../web/P2_STATUS.md).

#### PT2 · Live demo and two timed rehearsals with a fallback
Rehearsals **planned** 20.10 and 22.10 (P3, P4 as mock jury; no newer completion receipt in reviewed records); a fallback
clip to be re-recorded on the 1.2.0 image (the clip is from 23.09), a
second demo device, a short Falcon bag with the person (window of `falcon_test` around 280–330 s, not the 100-frame prefix).

## 9. State checked 20.10: decisions, the jury's comments, the new lidar

Owner P1. Reconciled on 20.10 against decisions 35–45, current source/configuration, committed evidence and GitHub
(release, main CI, open PR #43). Dated measurements below keep their original source/scope; they are not a new J1 score.

### 9a. Decisions (19–20.10; [`DECISIONS.md`](DECISIONS.md) rows 35–45)

* **1.1.0 will not be released.** Development continues on **1.2.0**; the next release, J1 and the G3 run use the **final
  1.2.0 seal**, the J1 pin to 1.1.0 is dropped (row 35). GitHub still publishes only **v1.0.0**; main's 20.10 CI is blocked
  before steps by billing/spending limit.
* **The questions to the organizers were sent and were partly answered on 19.10** ([`answers.md`](organizers/answers.md)
  §12, §9f below); open: the filter (Q3), bag playback (Q5), O1.
* **The four agent lanes** (K1/K2, F1, Falcon long range, N3) are merged with `main` (L16/S3, R3) into the integration
  branch with an identity proof (every new switch off: full gate per frame and the whole Falcon recording identical;
  [evidence](evidence/integration_2026-10-19/README.md); row 40), now in **main**. **Current switches:** F1a, H′, R3,
  L16/S3, H1 positive core and Falcon clear-distance model on; **K1/K2**, S2 settle, Falcon far range and dust guard off
  (rows 41, 44–45; table in "Current plan").
* **H1 partial improvement published in main** (row 45): A-axis 82 →114/177, 63 misses remain. H1/High stays OPEN;
  independent far-axis truth and final review are not obtained. Full combined gate, X3 and Falcon checks are complete
  ([record](evidence/h1_partial_integration_2026-10-20/README.md)). PR #43 (merged 20.10, `8c2bf51`) adds the off-by-default v5c switch and P4 review work; nothing in it is accepted.
* **F1a completion merged into main** (row 46, 20.10 evening): the local rail reference now compares the candidate's
  uncapped top with the rail head's **own top surface** — the same feature, not the web's median. The B1 repair's ride
  cost is gone (events 23 → 18, episodes 26 → 24, alarm frames 111 → 102 — the pre-repair values; 9 STOP frames
  removed, 0 added) and no detection is lost (set O, the labelled recording, the raised-rail physical scenes, the whole
  Falcon and X3 unchanged). Author evidence on committed source; the independent final-bundle review remains P0
  ([record](evidence/f1a_completion_2026-10-20/README.md)).
* **Code stop 20.10 23:59 MSK**, priorities instead of dates (row 42). The detector seal currently fails `verify`; the
  combined reseal is pending (P1 + P4).

### 9b. The jury's comments and criteria: status checked 20.10 (historical numbers labelled)

| comment / criterion | state | evidence | next |
|---|---|---|---|
| **Gauge stability** (box blinks, vanishes, leaves the track) | **partly done**: N1 draws a stable box (visible-edge jitter p90 at 40/80/120 m within 0.05/0.08/0.15 m) by drawing less (on the curve a median 52 m of 142 m supported); the detector's own axis still jitters; on the Falcon the trusted range changes by ≥ 20 m between frames in 34 % of frames | [N1/N4](evidence/n1_n4_2026-10-18/README.md), [B6](evidence/gauge_stability_2026-10-18/README.md), [check](evidence/falcon_head_check_2026-10-19/README.md) | K1/K2 **off**; candidate measurements/review pending |
| **Gauge synchronised with turns** | **K2 held off**, not solved; historical `roundT_doubleT` (R ≈ 400 m): axis curvature 3.6× too small, 1.6 m off driven path at 60 m | [B6](evidence/gauge_stability_2026-10-18/README.md), [v5c][p4-k2] | P4 candidate; independent review and captain decision |
| detection range (first detect) | Pandar (judge method): person-size box 218 m straight, 52–83 m on curves, 1 m cube 151 m, 0.3 m ~45 m; Falcon real person: first STOP ~125 m (visible in the raw cloud from ~249 m) | [RELEASE_DAY prebuild](evidence/rejudge_2026-10-16/RELEASE_DAY.md), [check](evidence/falcon_head_check_2026-10-19/README.md) | K2, N7, R1/R2 |
| gauge range | trusted axis median 120–175 m on Pandar recordings, reported 80–157 m; Falcon 123 m (no bed return beyond ~150 m) | B6, check | K1/K2, N7 |
| no false positives | judge 13.10 (v1.0.0): ~91 false STOP episodes per hour of empty tunnel, ~2.5 per km on the ride, CAUTION on 43 % of empty frames; Falcon: 12 false STOP frames in 444 s (8 under 10 m removed by H′), CAUTION 69 % | [SCORECARD](SCORECARD.md), check | F1 (on); C1 in P2 |
| no false negatives | H1 partially improved **82 →114/177**, inherited High OPEN; small far objects and curves unresolved; the P4 F1a capped-top miss is repaired and the F1a completion removes its ride cost without losing a detection | [H1](evidence/h1_partial_integration_2026-10-20/README.md), [range screen](evidence/range_screen_2026-10-15/README.md), [F1a completion](evidence/f1a_completion_2026-10-20/README.md), [P4][p4-shipping] | K2 **off**; H1 reference/review; F1a final-bundle review; R1/R2 P2 |
| real time 10 Hz | Falcon decode+detect ~17–21 ms per frame; Pandar 360° p95 106–119 ms on 4 vCPU (judge); the literal `ros2 bag play` gives stale results (S1 failed) | [N1/N4](evidence/n1_n4_2026-10-18/README.md), SCORECARD | S2, S5 |
| "the filter" | meaning asked, no answer; tracker confirmation and false-alarm rules exist | [QUESTIONS](QUESTIONS.md) | wait |
| extra features | N1 box, N4 interactive launch, Falcon profiles, web prototype, N5 labels | CHANGELOG [1.2.0] | P2 `ui-improvement` (unmerged) |
| ease of launch | N4 done locally (pause, rate, several bags in one node, Pandar → Falcon switch, software RViz); no published 1.2.0 image | [HOWTO](evidence/n1_n4_2026-10-18/HOWTO.md) | E1 after CI |
| dust | guard written and **off** (fails acceptance); no dust-attributed STOP/CAUTION in 13 organizer dust frames on 1.1.0 /`4cf8e27`; sparse particles, not dense-dust proof | [N3](evidence/n3_dust_2026-10-18/README.md), [integration](evidence/integration_2026-10-19/README.md) | P0 H1/final-source re-check |
| second lidar, different axes | Falcon profiles and L16/S3 **on**; A1 repaired, T1 measured; 27,580 paired recorded rows retained; final merged gate/X3 and whole4,443-row ordinary Falcon checked | [L16/S3](evidence/l16_s3_2026-10-19/README.md), [A1/T1][l16-open-air] | final-bundle independent review/reseal |

### 9c. Card N7 · Stable obstacle detection to 300 m on the Falcon Prime (goal of 19.10)

Sensor physics: datasheet 250 m at 10 % reflectivity, 500 m maximum; the recording has returns to 510 m but the person has
5–8 returns at 240–248 m, ~4 at 300 m by the datasheet model, and the bed gives none beyond ~150 m. Result of the lane
(`det/falcon-long-range`, merged **off**): see card N7 above; a 300 m claim is made only for the targets and reflectivities a
validated injector table supports, and none is made today. Details: [report](evidence/falcon_long_range_2026-10-19/REPORT.md).

### 9f. The organizers' answers of 19.10 and what they change

Verbatim in [`organizers/answers.md`](organizers/answers.md) §12; the order of the objects in
[`organizers/obstacles_2026-10-19.md`](organizers/obstacles_2026-10-19.md).

| answer | consequence | owner / where |
|---|---|---|
| **Everything inside the train's gauge is an obstacle** | an in-gauge object reported as `CAUTION` or `GO` is a **miss**; `CAUTION` stays only for objects outside or at the edge. Demotions of in-gauge clusters to advisory are miss risks to measure: the `column` demotion and `column_hold` (H1), `beyond_axis` where the axis is wrong (K2), `explained_run`, the dust guard, the settle switch | P3; C1 re-scoped by P1 |
| **Objects may move, even chaotically** | review every rule that assumes a static or approaching object: `tracking.ego_veto_min_speed` 4 m/s, the approach requirement of weak far evidence, settle tests, the dust guard, the far confirmation of the Falcon lane. Card **M1** | P3 + P4 |
| **No labels; marked bags + order of appearance** | intake done 19.10: all 1,667 serialized clouds independently verified byte-identical; N5 matches 1,672 /1,684 rows. Merged PR #43 supplies the missing cube supplement/12 flags. Markers establish obstacle support, **not rail-axis truth**; a missing marker is not a negative | P4 (N5); [intake](evidence/organizer_markers_2026-10-19/README.md), [supplement][p4-n5] |
| **Dust in every new synthetic bag, at least twice** | 17.10 blanket absence claim corrected: 11 tiny bursts over 13 frames; raw platform subtraction independently verifies 31 dust returns. No dust-attributed STOP/CAUTION on 1.1.0 /`4cf8e27`; H1/final-source replay pending. Background false STOPs are structures, not dust; dense-dust robustness unproved | P1's agent, P4; [intake](evidence/organizer_markers_2026-10-19/README.md) |
| Not answered: the filter (Q3), bag playback (Q5), O1 | unchanged assumptions | P1 |

### Verification scope of this reconciliation (20.10)

* Main and remote main were checked at `cefd4c4`; 47 current source files were compared with the source hashes of the
  H1 gate/probe/full-suite and X3 receipts. Existing measurements were inspected, not re-run for this documentation edit.
* Switch states were checked in `resense/config.py`, `configs/default.yaml` and the ROS YAML; release and CI state were
  queried live on GitHub. Freeze verification was re-run and fails against the old B4 seal, as expected before resealing.
* The initial reconciliation checked 71 local link occurrences; the R3 follow-up adds its verified evidence links.
  The five pinned PR #43 document targets exist in the fetched commit. Personal
  Windows-path references in tests/scripts and the three tracked root photos still exist, so their clean-up stays open.
* PR #43 was inspected at pinned head `972d19a`; GitHub confirms its merge at `8c2bf51`. Its K2 candidate stays off.
  The L16 follow-up reproduces A1 on that exact main, repairs the cue and independently measures T1 raw inputs.
  Capped-top/ego-veto findings remain open. Fresh evidence, including full-suite failures, is linked in the L16 record.
* Hardware/image acceptance, rehearsals, organizer replies and final J1/G3 have **no newer completion receipt in the
  reviewed records**; their existing pending states are retained, not independently observed human outcomes.

[p4-shipping]: https://github.com/pmixay/ReSense/blob/972d19a17aabfe223fd0f45551a2262b9a82e260/docs/evidence/p4_review_shipping_2026-10-20/README.md
[l16-open-air]: evidence/l16_open_air_2026-10-20/README.md
[p4-integration]: https://github.com/pmixay/ReSense/blob/972d19a17aabfe223fd0f45551a2262b9a82e260/docs/evidence/p4_review_integration_2026-10-20/README.md
[p4-n5]: https://github.com/pmixay/ReSense/blob/972d19a17aabfe223fd0f45551a2262b9a82e260/docs/evidence/n5_markers_2026-10-20/README.md
[p4-k2]: https://github.com/pmixay/ReSense/blob/972d19a17aabfe223fd0f45551a2262b9a82e260/docs/evidence/k2_v5c_2026-10-20/README.md
[p4-handoff]: https://github.com/pmixay/ReSense/blob/972d19a17aabfe223fd0f45551a2262b9a82e260/docs/evidence/p4_handoff_2026-10-20/HANDOFF.md
[p4-h-falcon]: evidence/p4_review_h_mount_falcon_2026-10-20/README.md

## History

Closed and superseded cards (S1, X1, X3, C2, E2, N1/N2/N4, D1 detail), the 16.10 integration ledger (§2), the dated plans of
15–22.10 (§4, §5, §8d), the competitor-survey table (§7), the 17.10 update (§8) and the per-role tables of 19.10 (§9d) are in
[`archive/BACKLOG_history_2026-10-19.md`](archive/BACKLOG_history_2026-10-19.md).
