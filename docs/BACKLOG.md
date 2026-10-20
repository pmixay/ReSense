# Backlog: remaining criteria work

> **Purpose:** what is left to gain on the eight criteria of ТЗ §8 after the independent judgement of 13.10 (66/100): the
> work per role (priorities, code stop 20.10 23:59 MSK), one status table and one short entry per open card, with links to
> the evidence. Closed and superseded cards, the dated plans of 15–19.10 and the ledgers of 16–18.10 are in
> [`archive/BACKLOG_history_2026-10-19.md`](archive/BACKLOG_history_2026-10-19.md): this file as it stood before the
> clean-up of 19.10, word for word, with the full text (cause, tasks, acceptance check) of every card.
> **Audience:** P1 (to distribute the work), team · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-10-20: `main` detector bytes from `0f02b28` (H1 publication `cefd4c4`), current defaults,
> [`DECISIONS.md`](DECISIONS.md) rows 35–45; fresh paired R3 Set F investigation on `69cf4b8`;
> committed integration/H1 evidence, GitHub release/CI and open PR #43. `python3 scripts/detector_freeze.py verify`
> re-run: **FAIL** (2 added and 12 changed detector files against the B4 seal). No new seal or release.
> **Status:** current. "Current plan" below replaces every dated target: **P0** before the code stop, **P1** before the pitch,
> **P2** after 23.10. Section numbers of the old file are kept where other documents cite them (§1, §3, §4, §6, §9);
> §2, §5, §7, §8, §9d and §9e are in the archive.

## Current plan (checked 20.10): priorities, code stop 20.10 23:59 MSK

This section replaces every dated target below. **P0** must be in before the code stop (code, configuration, seal);
**P1** before the pitch on 23.10 (evaluation, documents, deck, rehearsals; no code); **P2** after 23.10 unless time
remains. **Current detector source: main's 19.10 integration plus the user-authorized partial H1 improvement**
(published at `cefd4c4`). Its detector bytes equal measured merge `0f02b28`; the R3 follow-up changes reporting only.
H1 is still **OPEN**
([publication](evidence/h1_partial_integration_2026-10-20/README.md)). The former integration branch
`claude/optimistic-mccarthy-z5nmwd` has already landed through PR #42.

**Work outside main:** draft [PR #43](https://github.com/pmixay/ReSense/pull/43), head `972d19a`, contains an off-by-default
K2 v5c candidate, P4 reviews and an N5 supplement. These are available for review, **not merged or accepted as fixes**.
P4's findings concern pre-H1 source `4cf8e27`; their exposure on current main and any fix still need verification.
Pinned reports: [shipping review][p4-shipping], [integration review][p4-integration], [N5][p4-n5], [data handoff][p4-handoff].

### Current detector switches (decisions 41, 44–45; checked against class defaults and both YAMLs)

| switch | state in current 1.2.0 source | why | follow-up owner |
|---|---|---|---|
| F1a local rail reference (`lowobj.local_rail_margin` 0.01, cross-rail rule off) | **on** | ride low-kind false STOP episodes 4/6 → 1/1, gate exit 0 (F1 lane) | P3 author repair of both B1 mechanisms measured 20.10; independent review and decision on ride low-kind 1 →3 pending ([record](evidence/f1a_b1_2026-10-20/README.md)); P4 T4 exposure |
| H′ mount cross-check (`cluster.mount_cross_tol` 0.5) | **on** | removes the 8 false STOP frames on the Falcon tunnel ceiling; 0 gate rows change | — |
| S2 settle (`tracking.settle_min_hits`) | off | can delay an object entering the gauge | — |
| R3 cable confirmation (P3) | **on** | hanging cable improves; Set F median 34.2 →17.8 m explained by successful coverage 2/6 →4/6, no lost hits ([follow-up](evidence/r3_sustained_2026-10-20/README.md)) | P3: P4 shipping B2 fast confirmation / ego-veto interaction and B3 accumulation limit remain open |
| L16/S3 orientation (P3) | **on** | rotated ring-free mounts no longer adopt a wrong orientation; gate and Falcon preserved | P3/P4: P4 shipping A1 reports persistent FAULT on synthetic open-air startup; real exposure T1 pending |
| K2 axis on curves (`track.axis_joint_fit=false`), variant B = v5b without K1 | **held off** (decision 44) | original Falcon attribution was revised in PR #43 (122.27 m first person STOP, 37 person frames without STOP); the marked tunnels cube still loses STOPs (29 → 13 in the 2.5–250 m crop). `small_center` gate loss also remains | **P4 P0**: measured candidate and independent review, then captain's decision; v5c exists only in PR #43 ([report][p4-k2]) |
| K1 per-distance axis smoothing (`track.walls_smoothing_distance`) | off | standing train STOP at 100 m 82 → 255 / 260, but adds a false STOP on `doubleT_platform` (gate A measured on the integration branch) | P4, in the same package |
| Falcon clear-distance model (`small_target_limit`, falcon_prime) | **on** | reports up to 48.2 m from the measured Falcon raster (density model, as for Pandar) instead of 0 | — |
| Falcon far range (`farrange.with_falcon_profile`) | off | person STOP 146 m (was 127) but rule 5.1(b) fails (9 vs 8 episodes), no long-range gain on injected targets | P3: improve (route-map variant, second boundary) |
| Dust guard (`dust.enabled`) | off | fails its own acceptance; 13 organizer dust frames checked on `4cf8e27`, no dust-attributed STOP/CAUTION | P1/P4: repeat on H1 main / final reseal source; old check is not a dense-dust robustness result |
| H1 positive collision core (`cluster.column_core_margin` 0.02) | **on**, partial improvement | A-axis 82 →114/177; merged gate/X3 pass; inherited High remains OPEN (decision 45) | P3/P4: far-axis reference, 63 misses, independent review; withdrawn `column_free_max_top=0` stays off |

### P1 · captain

| prio | work | state / depends on |
|---|---|---|
| P0 | Repair CI account billing / spending limit: main run [39382006663](https://github.com/pmixay/ReSense/actions/runs/39382006663) on `cefd4c4` failed before any step; GitHub's annotation confirms billing/limit | blocks E1 and a hosted check of the release; verified 20.10 |
| P0 | Reseal 1.2.0 after the last code change (`scripts/detector_freeze.py`), with P4's review and the final gate/X3 | needs P4 P0 and P1's agent P0 |
| P1 | E1: tag and release 1.2.0, verify the archive | needs CI and the reseal |
| P1 | Final numbers into the deck and speech; two rehearsals with P2, P3, P4 | needs the reseal |
| P1 | S5: bench of the final image on the available hardware (2–4 cores accepted) | needs an image |
| P1 | Read the 29.09 safety review yourself ([`CAPTAIN.md`](CAPTAIN.md) §3 item 8) | — |
| P1 | Send the organizers the Falcon results and the 1.2.0 status if updates are allowed (O1 unanswered) | — |

### P1's agent · source measurements and integration

| prio | work | state |
|---|---|---|
| done | Current H1 main source: full gate without `--allow`, X3 and whole Falcon; A/C/cable probes and physical replay | measured `0f02b28`, same detector bytes as `cefd4c4`; gate PASS, X3 PASS (40 cases /29,765 rows), Falcon 4,443 rows ([record](evidence/h1_partial_integration_2026-10-20/README.md)) |
| P0 | After any accepted detector fix / K2 change: repeat affected checks and final gate/X3/Falcon on the exact reseal source; supply raw outputs for independent review | current checks are complete, final reseal acceptance is pending |
| P0 | Organizer dust and all three marked bags on H1 main / final reseal source | **done on `4cf8e27`** (1,667 frames, 13 dust frames); not repeated after H1. No dust-attributed STOP/CAUTION in the old run; guard stays off |
| P0 | Resolve or explicitly disposition the inherited proxy-hook test failure before final acceptance | current full suite: 2,276 passed +17 subtests, one failure, eight external-data deselections ([audit](evidence/h1_trajectory_2026-10-19/audit-final.json)) |
| P1 | Documentation clean-up and final numerical pass | backlog reconciled 20.10; final release numbers still depend on reseal/J1 |
| done | merge of the four agent lanes with identity proof; F1a and H′ switched on; decisions recorded | 19.10 |

### P2 · frontend / visuals

| prio | work | state / depends on |
|---|---|---|
| P0 | Move the three photos out of the repository root (`1591221.jpeg`, `IMG_8349.jpeg`, `IMG_8350.jpeg`, commit `7e38c01`): into the deck's assets if used and licensed, otherwise delete | all three still tracked at root, checked 20.10 |
| P1 | Short Falcon demo bag with the person: a window of `falcon_test` around 280–330 s (not the 100-frame prefix: it holds a false STOP at 115 m); check that `ros2 bag play` opens it; update the demo handoff | — |
| P1 | Second demo device (RViz / web) and a fallback clip re-recorded on the 1.2.0 image (the clip is from 23.09) | needs an image |
| P1 | Deck visuals: range-by-geometry chart (straight / curve / double track) and the Falcon slide | deck text updated 19.10 |
| P1 | Final numbers in the documents and GitBook | after the reseal and J1 |

### P3 · detector

| prio | work | state / depends on |
|---|---|---|
| P0 | Triage P4 shipping findings A1 (L16 open-air FAULT), B1 (F1a capped-top miss), B2 (R3 ego-veto race), plus B3/B4 limits; verify on H1 main, propose measured fixes | review reports available in PR #43, not closed; real-data T1/T4 pending ([review][p4-shipping], [handoff][p4-handoff]); after code stop, captain-approved review fixes only |
| done | Investigate Set F cable sustained median 34.2 →17.8 m and repair aggregate-only reporting | fresh 30-sequence paired run, 3,060 rows/side: 0 lost hits, 9 added cable hits, no false-detection increase; coverage 2/6 →4/6, original-success cohort unchanged ([record](evidence/r3_sustained_2026-10-20/README.md)) |
| P1 | Q&A preparation and mock jury: the algorithm, curves (what K2 ships and costs), why not 300 m, dust, the second lidar, false alarms; technical check of `ALGORITHM.md` and the slides | — |
| P1 | H1 (tall narrow objects, the open High finding): retain the implemented partial improvement; obtain a validated far-axis reference, resolve remaining misses and complete independent review | user-authorized main integration, **overall OPEN**; A-axis 82 ->114/177, 63 misses remain ([publication](evidence/h1_partial_integration_2026-10-20/README.md)) |
| P2 | F1a B1: author repair implemented on user request, final review/decision on the measured ride cost pending ([record](evidence/f1a_b1_2026-10-20/README.md)); Falcon far range (route-map variant, second boundary); M1 moving-object probes (the organizers: objects may move); C1, R1/R2, S4, N6 | F1a worked on 20.10; other items after 23.10 |

### P4 · data / evaluation

| prio | work | state / depends on |
|---|---|---|
| P0 (urgent T1) | Measure real-start exposure to L16/S3's open-air FAULT and F1a capped-top exposure (T4), then hand findings to P3 | registered in [data handoff][p4-handoff]; not measured there (cloud session lacked bag access) |
| **P0 (K2/K1)** | **Keep both off.** K2 v5c revision 1 is proposed in PR #43; registered gate/X3/Falcon/standing-person/marked-bag rows are not run. Resolve both the corrected Falcon loss and the in-gauge tunnels cube loss, set O `small_center`, K1 false STOPs and the review items. P3 or a fresh agent reviews P4's candidate; captain decides switch-on | [existing package](evidence/k1_k2_gauge_2026-10-19/P4_PACKAGE.md), [v5c][p4-k2], T2/T3 in [handoff][p4-handoff] |
| P0 | Complete acceptance of what ships on, including **H1**: resolve reported L16/S3, R3 and F1a findings, verify fixes on recordings and review combined source | pre-H1 synthetic shipping review available in PR #43; **not clean acceptance**, reseal still blocked ([review][p4-shipping]) |
| P0 | Finish independent integration verification from raw outputs of the exact combined source | historical review done where committed files allow; some old per-frame outputs missing. New H1 raw archives exist, independent review pending ([review][p4-integration], [current record](evidence/h1_partial_integration_2026-10-20/README.md)) |
| P1 | On the final seal: J1 (retarget [`RELEASE_DAY.md`](evidence/rejudge_2026-10-16/RELEASE_DAY.md) from 1.1.0) and the G3 held-out run by a fresh agent | needs the reseal |
| P1 | N5: review/integrate the marker supplement, then re-score final 1.2.0 | PR #43 adds 34 missing-cube rows and flags 12 unmatched rows; not in main; final H1/reseal scoring pending ([supplement][p4-n5]) |
| P1 | Mock jury at both rehearsals | — |
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
| reseal | reseal 1.2.0 after the last code change | `detector_freeze.py verify` FAILS now; P1 + P4, needs P4's review and the final gate/X3 | P0 |
| L16/S3 | ring-free orientation + bounded orientation search | **on**; P4 synthetic review reports open-air startup FAULT (PR #43 A1); real exposure/fix/current-source review pending | P0 |
| R3 | thin cables (hanging 5 cm: first STOP 30.1 → 35.1 m) | **on**; Set F aggregate concern resolved: coverage 2/6 →4/6, fixed cohort 34.2 →34.2 m, 0 lost hits. P4 B2/B3 review findings remain open | P0 |
| F1 | near-field low-object false STOPs | F1a and H′ **on**, S2 settle off. Author repair of both B1 mechanisms measured in working tree; seal gate PASS, main ride gate FAIL (18 →23 events, 24 →26 episodes); review/ride-cost decision pending ([record](evidence/f1a_b1_2026-10-20/README.md)) | P0 / P2 |
| K1 / K2 | gauge on curves, standing train | **both off** (`walls_smoothing_distance=0`, `axis_joint_fit=false`), decision 44; v5c proposed only in PR #43, real-data acceptance pending | P0 / P2 |
| N3 | dust | guard **off** (fails acceptance); organizer dust checked on `4cf8e27`, H1/final-source replay pending | P0 |
| N7 | Falcon to 300 m | `farrange` **off**: person STOP 146 m (was 127 m), no gain on injected targets, rule 5.1(b) fails | P2 |
| H1 | tall narrow objects (the open High finding, 8.1) | **partial positive-core improvement implemented and accepted for main; overall OPEN**. A-axis 82 ->114/177, physical controls and merged gate/X3 pass; independent far-axis reference and final review pending ([record](evidence/h1_partial_integration_2026-10-20/README.md)) | P1 |
| N5 | labels of the new synthetic bags | initial labels done; organizer markers independently checked; PR #43 supplement adds cube/flags 12 rows, not merged; final scoring pending | P1 |
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
([evidence](evidence/l16_s3_2026-10-19/README.md)). P4's synthetic shipping review is available in PR #43:
sampling checks pass there, but the associated directional cue can lock the wrong forward axis on an open-air start
(A1). P3 verifies/fixes it; real-start exposure and final-source acceptance remain open ([review][p4-shipping], T1 in [handoff][p4-handoff]).

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
against markers. **20.10 update:** PR #43 contains a non-destructive supplement with 34 cropped
cube rows and the 12 flagged rows, plus per-object scoring of historical runs; review/integration into main and scoring
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
All 32 stationary physical scenes match after confirmation; 280 outside controls have no false STOP. Nominal moving
physical scenes have continuous STOP from **130.8 /135.2 m**, a simulation result only. Merged source `0f02b28` passes
the full gate; fresh combined-tree X3 passes 40 cases /29,765 rows. The full suite retains one inherited proxy-hook
failure (2,276 passed +17 subtests). The user explicitly authorized publishing this partial improvement in main without
claiming closure. Still needed: independently validated far rail axis/trajectory, remaining miss resolution,
wrong-pair/no-rail limits and independent final review/reseal.
[Publication](evidence/h1_partial_integration_2026-10-20/README.md),
[repair](evidence/h1_reference_2026-10-19/README.md),
[rejected reference attempts](evidence/h1_trajectory_2026-10-19/README.md).

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
off by default and not in main; registered real-data rows (including the cube, which v5c does not repair) remain pending.
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
([follow-up](evidence/r3_sustained_2026-10-20/README.md)). **Independent final R3 review is still open.**
P4's PR #43 shipping review reports **B2**: fast
confirmation can earn STOP before the ego veto has enough history on a carried-along thin target (synthetic onset difference);
**B3**: tall-cable shortcut is inert on accumulated clusters (reviewer-only limitation). P3 verifies on H1 main and
measures any fix; no clean final acceptance is claimed ([review][p4-shipping]). The target's correct STOP/advisory label
must also respect the organizers' moving-in-gauge obstacle rule (M1), not be inferred from the veto alone.

#### F1 · Near-field low-object false STOPs at the rail-head plane
F1a local rail reference **on** (ride low-kind episodes 4/6 → 1/1; review finding B1, a long low object along one rail,
accepted; P3 improves it), H′ mount cross-check **on** (8 false STOP frames on the Falcon tunnel ceiling), S2 settle off
([handoff](evidence/f1_false_alarms_2026-10-19/HANDOFF.md)). Gate and whole Falcon are complete on `4cf8e27` and the
combined H1 source. **New P4 shipping B1** is distinct from the previously accepted long-object B1: a low cluster's top
is capped at the model envelope floor, so a raised local rail reference can weaken a genuine low obstacle (8 →0 STOP
frames in P4's synthetic case). Committed main still uses that capped top. P3 verifies/fixes; P4 T4 measures real exposure;
ride/Falcon non-regression and independent review follow ([review][p4-shipping], [handoff][p4-handoff]).

**20.10 author repair (working tree, user-requested):** both B1 mechanisms are addressed with independent low-footprint-free
rail support and the observed full-footprint top. Fragment controls retain ordinary confirmation (all 12 two-rail tracks);
the P4 raised-rail box regains its 8 STOP rows. Full gate against the seal baseline **PASS without exceptions**; Set F
matches starting main, Falcon's 4,443 detection/warning rows match. There is a measured ride cost against starting main:
chunked gate events **18 →23**, STOP episodes **24 →26**; the continuous replay adds 11 STOP rows (**109 →120**),
with low-kind episodes **1 →3**. This is **not** clean non-regression against main or final P4 acceptance; the ride
trade-off needs disposition before integration/reseal. [Repair, source receipts and raw checks](evidence/f1a_b1_2026-10-20/README.md).
Author X3 also passes all 40 cases /29,765 rows with identical STOP row sets; this dirty-source byte-identified run
does not replace final committed-source acceptance or independent P4 review.

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
  ([record](evidence/h1_partial_integration_2026-10-20/README.md)). PR #43 is separate, unmerged candidate/review work.
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
| no false negatives | H1 partially improved **82 →114/177**, inherited High OPEN; small far objects and curves unresolved; new P4 F1a miss reported on synthetic scenes | [H1](evidence/h1_partial_integration_2026-10-20/README.md), [range screen](evidence/range_screen_2026-10-15/README.md), [P4][p4-shipping] | K2 **off**; H1 reference/review; F1a fix/exposure; R1/R2 P2 |
| real time 10 Hz | Falcon decode+detect ~17–21 ms per frame; Pandar 360° p95 106–119 ms on 4 vCPU (judge); the literal `ros2 bag play` gives stale results (S1 failed) | [N1/N4](evidence/n1_n4_2026-10-18/README.md), SCORECARD | S2, S5 |
| "the filter" | meaning asked, no answer; tracker confirmation and false-alarm rules exist | [QUESTIONS](QUESTIONS.md) | wait |
| extra features | N1 box, N4 interactive launch, Falcon profiles, web prototype, N5 labels | CHANGELOG [1.2.0] | P2 `ui-improvement` (unmerged) |
| ease of launch | N4 done locally (pause, rate, several bags in one node, Pandar → Falcon switch, software RViz); no published 1.2.0 image | [HOWTO](evidence/n1_n4_2026-10-18/HOWTO.md) | E1 after CI |
| dust | guard written and **off** (fails acceptance); no dust-attributed STOP/CAUTION in 13 organizer dust frames on 1.1.0 /`4cf8e27`; sparse particles, not dense-dust proof | [N3](evidence/n3_dust_2026-10-18/README.md), [integration](evidence/integration_2026-10-19/README.md) | P0 H1/final-source re-check |
| second lidar, different axes | Falcon profiles and L16/S3 implemented, **on**; full 4,443-row Falcon check retained on H1 main. P4 reports synthetic open-air startup FAULT outside these recordings | [L16/S3](evidence/l16_s3_2026-10-19/README.md), [H1 checks](evidence/h1_partial_integration_2026-10-20/README.md), [P4][p4-shipping] | real-start T1, P3 fix and final review |

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
| **No labels; marked bags + order of appearance** | intake done 19.10: all 1,667 serialized clouds independently verified byte-identical; N5 matches 1,672 /1,684 rows. PR #43 supplies the missing cube supplement/12 flags, not yet in main. Markers establish obstacle support, **not rail-axis truth**; a missing marker is not a negative | P4 (N5); [intake](evidence/organizer_markers_2026-10-19/README.md), [supplement][p4-n5] |
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
* PR #43 was inspected at pinned head `972d19a`. Its review findings and N5 work are recorded as **reported/proposed**;
  neither the candidate nor its proposed fixes are credited to main. Current code still contains the reviewed cue,
  capped-top rail check and fast-confirmation/ego-veto interaction.
* Hardware/image acceptance, rehearsals, organizer replies and final J1/G3 have **no newer completion receipt in the
  reviewed records**; their existing pending states are retained, not independently observed human outcomes.

[p4-shipping]: https://github.com/pmixay/ReSense/blob/972d19a17aabfe223fd0f45551a2262b9a82e260/docs/evidence/p4_review_shipping_2026-10-20/README.md
[p4-integration]: https://github.com/pmixay/ReSense/blob/972d19a17aabfe223fd0f45551a2262b9a82e260/docs/evidence/p4_review_integration_2026-10-20/README.md
[p4-n5]: https://github.com/pmixay/ReSense/blob/972d19a17aabfe223fd0f45551a2262b9a82e260/docs/evidence/n5_markers_2026-10-20/README.md
[p4-k2]: https://github.com/pmixay/ReSense/blob/972d19a17aabfe223fd0f45551a2262b9a82e260/docs/evidence/k2_v5c_2026-10-20/README.md
[p4-handoff]: https://github.com/pmixay/ReSense/blob/972d19a17aabfe223fd0f45551a2262b9a82e260/docs/evidence/p4_handoff_2026-10-20/HANDOFF.md

## History

Closed and superseded cards (S1, X1, X3, C2, E2, N1/N2/N4, D1 detail), the 16.10 integration ledger (§2), the dated plans of
15–22.10 (§4, §5, §8d), the competitor-survey table (§7), the 17.10 update (§8) and the per-role tables of 19.10 (§9d) are in
[`archive/BACKLOG_history_2026-10-19.md`](archive/BACKLOG_history_2026-10-19.md).
