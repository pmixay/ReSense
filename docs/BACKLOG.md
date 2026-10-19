# Backlog: remaining criteria work

> **Purpose:** what is left to gain on the eight criteria of ТЗ §8 after the independent judgement of 13.10 (66/100): the
> work per role (priorities, code stop 20.10 23:59 MSK), one status table and one short entry per open card, with links to
> the evidence. Closed and superseded cards, the dated plans of 15–19.10 and the ledgers of 16–18.10 are in
> [`archive/BACKLOG_history_2026-10-19.md`](archive/BACKLOG_history_2026-10-19.md): this file as it stood before the
> clean-up of 19.10, word for word, with the full text (cause, tasks, acceptance check) of every card.
> **Audience:** P1 (to distribute the work), team · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-10-19 (evening): states against [`DECISIONS.md`](DECISIONS.md) rows 35–42 and the evidence of
> 19.10; `python3 scripts/detector_freeze.py verify` run the same day: **FAIL** (2 added and 11 changed detector files).
> **Status:** current. "Current plan" below replaces every dated target: **P0** before the code stop, **P1** before the pitch,
> **P2** after 23.10. Section numbers of the old file are kept where other documents cite them (§1, §3, §4, §6, §9);
> §2, §5, §7, §8, §9d and §9e are in the archive.

## Current plan (19.10, evening): priorities, code stop 20.10 23:59 MSK

This section replaces every dated target below. **P0** must be in before the code stop (code, configuration, seal);
**P1** before the pitch on 23.10 (evaluation, documents, deck, rehearsals; no code); **P2** after 23.10 unless time
remains. Integration branch: `claude/optimistic-mccarthy-z5nmwd` (`main` with P3's L16/S3 and R3, plus the four agent
lanes K1/K2, F1, Falcon long range and N3, merged 19.10 with an identity proof; [evidence](evidence/integration_2026-10-19/README.md)).

### Detector switches decided by the captain (19.10, [`DECISIONS.md`](DECISIONS.md) row 41)

| switch | state in 1.2.0 | why | follow-up owner |
|---|---|---|---|
| F1a local rail reference (`lowobj.local_rail_margin` 0.01, cross-rail rule off) | **on** | ride low-kind false STOP episodes 4/6 → 1/1, gate exit 0 (F1 lane) | P3: make it safe for a long low object along one rail (review B1, accepted risk) |
| H′ mount cross-check (`cluster.mount_cross_tol` 0.5) | **on** | removes the 8 false STOP frames on the Falcon tunnel ceiling; 0 gate rows change | — |
| S2 settle (`tracking.settle_min_hits`) | off | can delay an object entering the gauge | — |
| R3 cable confirmation (P3) | **on** | hanging cable in set O: first STOP 35.1 m (was 30.1), held from 40.0 m (was 31.8); gate exit 0 | P3: the set F cable sustained-median row 34.2 → 17.8 m |
| L16/S3 orientation (P3) | **on** | rotated ring-free mounts no longer adopt a wrong orientation; gate and Falcon identical | — |
| K2 axis on curves (`track.axis_joint_*`), variant B = v5b without K1 | **held off** (captain 19.10, [`DECISIONS.md`](DECISIONS.md) rows 43–44) | the jury's "gauge follows turns". Pandar gate: ride STOP episodes 24 → 9, five empty recordings 11 → 0, set O `small_center` first STOP 55.8 → 52.5 m; but on Falcon the walking person's first STOP 124.8 → 113.0 m (158 STOP frames lost) | **P4 P0**: resolve the problems, then a new decision ([package](evidence/k1_k2_gauge_2026-10-19/P4_PACKAGE.md)) |
| K1 per-distance axis smoothing (`track.walls_smoothing_distance`) | off | standing train STOP at 100 m 82 → 255 / 260, but adds a false STOP on `doubleT_platform` (gate A measured on the integration branch) | P4, in the same package |
| Falcon clear-distance model (`small_target_limit`, falcon_prime) | **on** | reports up to 48.2 m from the measured Falcon raster (density model, as for Pandar) instead of 0 | — |
| Falcon far range (`farrange.with_falcon_profile`) | off | person STOP 146 m (was 127) but rule 5.1(b) fails (9 vs 8 episodes), no long-range gain on injected targets | P3: improve (route-map variant, second boundary) |
| Dust guard (`dust.enabled`) | off | fails its own acceptance; the organizers' dust gives no STOP/CAUTION on 1.1.0 (re-checked on the final configuration) | P4, only if that re-check fails |

### P1 · captain

| prio | work | state / depends on |
|---|---|---|
| P0 | Repair CI (account billing): 0 of the last 100 runs succeeded, the jobs stop before any step | blocks E1 and a hosted check of the release |
| P0 | Reseal 1.2.0 after the last code change (`scripts/detector_freeze.py`), with P4's review and the final gate/X3 | needs P4 P0 and P1's agent P0 |
| P1 | E1: tag and release 1.2.0, verify the archive | needs CI and the reseal |
| P1 | Final numbers into the deck and speech; two rehearsals with P2, P3, P4 | needs the reseal |
| P1 | S5: bench of the final image on the available hardware (2–4 cores accepted) | needs an image |
| P1 | Read the 29.09 safety review yourself ([`CAPTAIN.md`](CAPTAIN.md) §3 item 8) | — |
| P1 | Send the organizers the Falcon results and the 1.2.0 status if updates are allowed (O1 unanswered) | — |

### P1's agent (Claude, integration branch)

| prio | work | state |
|---|---|---|
| P0 | Final measurements of the shipped configuration (K2 off) on the final commit: gate per frame (identity with `11bb1ab`), X3, whole Falcon; for the reseal | running |
| P0 | Final gate (without `--allow`), X3 and the whole Falcon recording on the final commit; integration evidence for the reseal | after K2 |
| P0 | The organizers' dust (13 frames of the marked synthetic bags) on the final configuration: no STOP or CAUTION from it → the dust guard stays off; otherwise hand to P4 | after K2 |
| P1 | Documentation clean-up: remove old handoffs and unused documents, fix stale statements, compact the long documents | agent |
| done | merge of the four agent lanes with identity proof; F1a and H′ switched on; decisions recorded | 19.10 |

### P2 · frontend / visuals

| prio | work | state / depends on |
|---|---|---|
| P0 | Move the three photos out of the repository root (`1591221.jpeg`, `IMG_8349.jpeg`, `IMG_8350.jpeg`, commit `7e38c01`): into the deck's assets if used and licensed, otherwise delete | nothing links to them |
| P1 | Short Falcon demo bag with the person: a window of `falcon_test` around 280–330 s (not the 100-frame prefix: it holds a false STOP at 115 m); check that `ros2 bag play` opens it; update the demo handoff | — |
| P1 | Second demo device (RViz / web) and a fallback clip re-recorded on the 1.2.0 image (the clip is from 23.09) | needs an image |
| P1 | Deck visuals: range-by-geometry chart (straight / curve / double track) and the Falcon slide | deck text updated 19.10 |
| P1 | Final numbers in the documents and GitBook | after the reseal and J1 |

### P3 · detector

| prio | work | state / depends on |
|---|---|---|
| P0 | Answer P4's review of R3 and L16/S3; explain the set F cable sustained-median row (34.2 → 17.8 m) under R3; no detector edits after the code stop except review fixes the captain approves | P4 P0 |
| P1 | Q&A preparation and mock jury: the algorithm, curves (what K2 ships and costs), why not 300 m, dust, the second lidar, false alarms; technical check of `ALGORITHM.md` and the slides | — |
| P1 | H1 (tall narrow objects, the open High finding): document the proposed approach, no code | cause reproduced ([R3/H1](evidence/r3_h1_2026-10-19/README.md)) |
| P2 | F1a without the B1 risk (a long low object along one rail raises its own reference); Falcon far range (route-map variant, second boundary); M1 moving-object probes (the organizers: objects may move); C1, R1/R2, S4, N6 | after 23.10 |

### P4 · data / evaluation

| prio | work | state / depends on |
|---|---|---|
| **P0 (first)** | **K2 / K1 (held off): resolve the problems and bring a variant back to the captain.** In order: the Falcon person stopped 12 m later (the reach cap cuts the trusted range), set O `small_center` 3.3 m later (the only gate failure), the standing person at 150 m, X3, curve accuracy (K2-1/2/3, B6), new ride and near-field STOP episodes, K1's false STOP, the review items. Each candidate goes to the captain with its row table, including the whole Falcon recording; the review is by P3 or a fresh agent, because P4 is its author. A switch-on before the code stop needs the captain's decision and P1's final measurement | [package](evidence/k1_k2_gauge_2026-10-19/P4_PACKAGE.md) |
| P0 | Independent review of what ships on: L16/S3, R3, F1a, H′ (`DETECTOR_FREEZE.md` step 3); K2 is reviewed by P3 or a fresh agent (see above) | blocks the reseal |
| P0 | Review the integration identity proof (gate per frame, Falcon) | [evidence](evidence/integration_2026-10-19/README.md) |
| P1 | On the final seal: J1 (retarget [`RELEASE_DAY.md`](evidence/rejudge_2026-10-16/RELEASE_DAY.md) from 1.1.0) and the G3 held-out run by a fresh agent | needs the reseal |
| P1 | N5 labels: add the missed tunnel cube (marker id 18, frames 4–60), mark the 12 unmatched rows, re-score the final 1.2.0 against the markers | [markers](evidence/synth_markers_2026-10-19/README.md) |
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

## 3. Status of every item (19.10, evening)

Priorities are those of "Current plan"; items it does not list are P2. Section 2 (the 16.10 integration ledger), the
point estimates and the former dates of every row are in the archive.

| id | item | state | prio |
|---|---|---|---|
| CI | repair CI (account billing) | 0 of the last 100 runs succeeded, jobs stop before any step; blocks E1 | P0 |
| reseal | reseal 1.2.0 after the last code change | `detector_freeze.py verify` FAILS now; P1 + P4, needs P4's review and the final gate/X3 | P0 |
| L16/S3 | ring-free orientation + bounded orientation search | done by P3, **on**; P4 review pending ([evidence](evidence/l16_s3_2026-10-19/README.md)) | P0 |
| R3 | thin cables (hanging 5 cm: first STOP 30.1 → 35.1 m) | done by P3, **on**; P4 review pending; set F cable row 34.2 → 17.8 m open | P0 |
| F1 | near-field low-object false STOPs | F1a **on** (review finding B1 accepted), H′ **on**, S2 settle off; final gate/Falcon pending | P0 / P2 |
| K1 / K2 | gauge on curves, standing train | **on**; variant chosen from v3/v4/v5 on 20.10; P4 develops it | P0 / P2 |
| N3 | dust | guard written, **off** (fails its acceptance); re-check the organizers' dust on the final configuration | P0 |
| N7 | Falcon to 300 m | `farrange` **off**: person STOP 146 m (was 127 m), no gain on injected targets, rule 5.1(b) fails | P2 |
| H1 | tall narrow objects (the open High finding, 8.1) | cause reproduced, approach proposed, no code | P1 |
| N5 | labels of the new synthetic bags | done 17.10; the organizers' markers are now the reference; add the missed cube, mark 12 rows, re-score 1.2.0 | P1 |
| J1 | re-judge the final seal | retarget [`RELEASE_DAY.md`](evidence/rejudge_2026-10-16/RELEASE_DAY.md) from 1.1.0; needs the reseal | P1 |
| G3 | held-out run by a fresh agent | spec registered, no run; on the final 1.2.0 seal | P1 |
| E1 | tag and release 1.2.0 (1.1.0 is not released) | needs CI, the reseal and the final image | P1 |
| S5 | bench of the final image | 2–4 cores accepted; needs an image | P1 |
| PT1 / PT2 | pitch content; live demo and two rehearsals | deck text updated 19.10; rehearsals 20.10 and 22.10; visuals and final numbers after the reseal | P1 |
| D1 | stale statements in the docs | done in the clean-up of 19.10; final numbers after the reseal and J1 | P1 |
| O1 | questions to the organizers | sent; partly answered 19.10 ([`answers.md`](organizers/answers.md) §12); open: filter, playback, O1 | P1 |
| M1 | moving-object probes (new 19.10) | not started | P2 |
| C1 | CAUTION policy | v2 failed offline; the answer "in gauge = obstacle" settles it for in-gauge objects | P2 |
| R1 / R2 | 0.3 m objects from ~45 m; sparse far objects | the five cheap overrides were rejected 15.10; wait for X1-style attribution | P2 |
| F2 / X2 | far-onset false STOPs; false-STOP ledger | not started | P2 |
| S2 / S4 | 360° per-frame cost; dual-return duplicates | not started (S2 here is the card, not the F1 lane's settle switch) | P2 |
| N6 | late STOP on the platform person | candidate rejected, **off** | P2 |
| G1 / G2 / T1 | rule provenance; doubt model; next-seal clean-up | not started | P2 |
| D2 | archive the 28.09 layer | the documents are moved (19.10); personal-path tests and orphan scripts open | P2 |
| closed | H0–H6, S1, X1, X3, C2, N1, N2, N4 | 16–18.10 ledger, results and failed S1 in the archive | done |

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
Done by P3 together with L16 (sample once to ≤ 60,000 points before the candidate loop), **on**; P4 review pending
([evidence](evidence/l16_s3_2026-10-19/README.md)).

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
the pin to 1.1.0 is dropped, so the runbook is retargeted to the final 1.2.0 seal; Docker steps wait for the image. P4, P1.

#### N5 · Labels and scoring for the new synthetic bags
Done 17.10 ([labels](evidence/n5_labels_2026-10-17/README.md)); on 19.10 checked against the organizers' markers
([evidence](evidence/synth_markers_2026-10-19/README.md)): 1,672 of 1,684 rows match, 12 sparse rows do not, one object is
missing (first small cube of `synthetic_tunnels`, marker id 18, frames 4–60). Open for P4: add it, mark the 12 rows, use the
markers as the reference, re-score 1.2.0.

#### X2 · False-STOP ledger with pass-by ground truth and a fast window replay
36 episodes / 173 STOP frames in 13,558 empty frames (~91/h); enabler for F2 and K2. P4 lane, P2 priority.

### Detector: range and false alarms

#### H1 · Tall narrow objects (the inherited High finding, 8.1)
**OPEN.** The free-top fix was dropped after review ([withdrawal](evidence/integration_2026-10-16/h4_fixes/columns/WITHDRAWAL_RESULTS.md));
the cause was reproduced on 19.10 and a new approach proposed ([R3/H1](evidence/r3_h1_2026-10-19/README.md)). P3: document it, no code.

#### K1 · Standing train: far axis jitter → STOP flicker at 100–150 m, perturbation-sensitive platform false STOPs
Distance-based smoothing of the wall fit (`track.walls_smoothing_distance`), **on**. v4: standing person at 100 / 150 m
255 / 197 STOP frames (base 82 / 90), but the full gate exits 1 (19 rows) and false STOPs are added; a v5 attempt runs and
the variant is chosen on 20.10 ([handoff](evidence/k1_k2_gauge_2026-10-19/HANDOFF.md),
[gauge stability](evidence/gauge_stability_2026-10-18/README.md)).

#### K2 · Curve and double-track axis — read the round-3 evidence first
Joint axis fit (`track.axis_joint_fit`), **on** (variant from v3/v4/v5). The jury's "gauge follows turns": on `roundT_doubleT`
the axis curvature was 3.6× too small. Measured v3/v4: wall error on C 0.40–0.56 m at 80–120 m (base 0.72–3.43 m), but the
held range of the C person falls (91.6 → 69.5 m). P0: measure the chosen variant on the integration commit; P4 develops it (P2).

#### R1 · R2 · Small and sparse far objects
R1: 0.3 m objects confirmed only from ~45 m (hardware rule, low stage ends at 60 m). R2: the point bar leaves an 80–100 m
hole for 0.5 m cubes. The five cheap config overrides were rejected 15.10 ([range screen](evidence/range_screen_2026-10-15/README.md));
a new candidate needs X1-style attribution first. P3, P2.

#### R3 · Thin cables
Done by P3, **on**: set O hanging 5 cm first STOP 30.1 → 35.1 m (held from 40.0 m), standing 5 cm cable first / held 59.8 /
43.4 → 86.25 / 61.28 m on the node replica; set F cable sustained-median row 34.2 → 17.8 m is worse and open. P4 review
pending ([evidence](evidence/r3_h1_2026-10-19/README.md)).

#### F1 · Near-field low-object false STOPs at the rail-head plane
F1a local rail reference **on** (ride low-kind episodes 4/6 → 1/1; review finding B1, a long low object along one rail,
accepted; P3 improves it), H′ mount cross-check **on** (8 false STOP frames on the Falcon tunnel ceiling), S2 settle off
([handoff](evidence/f1_false_alarms_2026-10-19/HANDOFF.md)). Final gate and Falcon run on `11bb1ab`: pending.

#### F2 · Far-onset false STOPs at ≥ 100 m (half of all episodes)
18 of 36 episodes; every earlier filter cost range. Needs the X2 audit and the final seal. P3, P2.

#### N3 · Dust / suspension
Generator and complete measurement done 18.10 ([evidence](evidence/n3_dust_2026-10-18/README.md)); the guard
(`resense/dust_guard.py`) is written and **off** (`dust.enabled: false`): on the registered battery only 6 of 15 empty-recording
rows pass ([handoff](evidence/n3_dust_fix_2026-10-19/HANDOFF.md)). The organizers' dust (11 bursts, 13 frames) gives no `STOP`
or `CAUTION` on 1.1.0; P1's agent re-checks it on the final configuration, P4 acts only if that fails.

#### N6 · Late STOP on the synthetic person at the platform
Candidate revision 3 (first STOP 44.01 → 51.12 m) rejected, **off**: the 60 m target is unmet and the false-alarm bound
widens 38 → 47 ([evidence](evidence/n6_platform_2026-10-18/README.md)). P3, P2.

#### N7 · Stable obstacle detection to 300 m on the Falcon Prime
`farrange` (far straight axis, crop 400 m) is **off**: on the real recording the person's first STOP is 146 m (was 127 m)
with 0 false episodes, but there is no long-range gain on injected targets and rule 5.1(b) fails (9 vs 8 STOP episodes).
**No 300 m and no 250 m claim.** To improve: a route-map variant (`declared_straight_to`) or a second boundary. P3, P2
([report](evidence/falcon_long_range_2026-10-19/REPORT.md), [check](evidence/falcon_head_check_2026-10-19/README.md)).

#### M1 · Moving-object probe set (new 19.10)
The organizers: objects may move, even chaotically. A probe set (crossing, receding, lateral random walk, stop-and-go at
30–150 m) through the judge's ray-cast tool, measured on the final seal; any rule that loses an in-gauge moving object is
fixed or switched off (`ego_veto`, weak far evidence, settle, dust guard). P3 + P4, P2.

### Generalization and technical quality

#### G1 · G2 · T1 · After the final seal
**G1** ablate every rule justified by a named recording (333 YAML leaves, 30 cite a recording; ~17 full gates).
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
Rehearsals 20.10 and 22.10 (P3, P4 as mock jury); a fallback clip re-recorded on the 1.2.0 image (the clip is from 23.09), a
second demo device, a short Falcon bag with the person (window of `falcon_test` around 280–330 s, not the 100-frame prefix).

## 9. State of 19.10: decisions, the jury's comments, the new lidar

Owner P1. Checked on 19.10 against `DECISIONS.md` rows 35–42, GitHub (releases, tags, CI runs) and the evidence of the day.

### 9a. Decisions (captain, 19.10; [`DECISIONS.md`](DECISIONS.md) rows 35–42)

* **1.1.0 will not be released.** Development continues on **1.2.0**; the next release, J1 and the G3 run use the **final
  1.2.0 seal**, the J1 pin to 1.1.0 is dropped (row 35). Tagging waits for CI (0 of the last 100 runs succeeded).
* **The questions to the organizers were sent and were partly answered on 19.10** ([`answers.md`](organizers/answers.md)
  §12, §9f below); open: the filter (Q3), bag playback (Q5), O1.
* **The four agent lanes** (K1/K2, F1, Falcon long range, N3) are merged with `main` (L16/S3, R3) into the integration
  branch with an identity proof (every new switch off: full gate per frame and the whole Falcon recording identical;
  [evidence](evidence/integration_2026-10-19/README.md); row 40). **Switches:** F1a, H′, R3, L16/S3, K2 and the Falcon
  clear-distance model on; S2 settle, Falcon far range and the dust guard off (row 41; table in "Current plan").
* **Code stop 20.10 23:59 MSK**, priorities instead of dates (row 42). The detector seal currently fails `verify`; the
  combined reseal is pending (P1 + P4).

### 9b. The jury's comments and criteria: state on 19.10

| comment / criterion | state | evidence | next |
|---|---|---|---|
| **Gauge stability** (box blinks, vanishes, leaves the track) | **partly done**: N1 draws a stable box (visible-edge jitter p90 at 40/80/120 m within 0.05/0.08/0.15 m) by drawing less (on the curve a median 52 m of 142 m supported); the detector's own axis still jitters; on the Falcon the trusted range changes by ≥ 20 m between frames in 34 % of frames | [N1/N4](evidence/n1_n4_2026-10-18/README.md), [B6](evidence/gauge_stability_2026-10-18/README.md), [check](evidence/falcon_head_check_2026-10-19/README.md) | K1/K2 on; variant on 20.10 |
| **Gauge synchronised with turns** | **K2 switched on**, numbers on the final commit pending; before: on `roundT_doubleT` (R ≈ 400 m) the axis curvature was 3.6× too small, 1.6 m off the driven path at 60 m | [B6](evidence/gauge_stability_2026-10-18/README.md), [K1/K2](evidence/k1_k2_gauge_2026-10-19/HANDOFF.md) | K2 |
| detection range (first detect) | Pandar (judge method): person-size box 218 m straight, 52–83 m on curves, 1 m cube 151 m, 0.3 m ~45 m; Falcon real person: first STOP ~125 m (visible in the raw cloud from ~249 m) | [RELEASE_DAY prebuild](evidence/rejudge_2026-10-16/RELEASE_DAY.md), [check](evidence/falcon_head_check_2026-10-19/README.md) | K2, N7, R1/R2 |
| gauge range | trusted axis median 120–175 m on Pandar recordings, reported 80–157 m; Falcon 123 m (no bed return beyond ~150 m) | B6, check | K1/K2, N7 |
| no false positives | judge 13.10 (v1.0.0): ~91 false STOP episodes per hour of empty tunnel, ~2.5 per km on the ride, CAUTION on 43 % of empty frames; Falcon: 12 false STOP frames in 444 s (8 under 10 m removed by H′), CAUTION 69 % | [SCORECARD](SCORECARD.md), check | F1 (on); C1 in P2 |
| no false negatives | tall narrow objects (H1, OPEN 8.1), small far objects (R1/R2 screens rejected 15.10), curves (K2) | [range screen](evidence/range_screen_2026-10-15/README.md) | K2 on; H1 documented; R1/R2 P2 |
| real time 10 Hz | Falcon decode+detect ~17–21 ms per frame; Pandar 360° p95 106–119 ms on 4 vCPU (judge); the literal `ros2 bag play` gives stale results (S1 failed) | [N1/N4](evidence/n1_n4_2026-10-18/README.md), SCORECARD | S2, S5 |
| "the filter" | meaning asked, no answer; tracker confirmation and false-alarm rules exist | [QUESTIONS](QUESTIONS.md) | wait |
| extra features | N1 box, N4 interactive launch, Falcon profiles, web prototype, N5 labels | CHANGELOG [1.2.0] | P2 `ui-improvement` (unmerged) |
| ease of launch | N4 done locally (pause, rate, several bags in one node, Pandar → Falcon switch, software RViz); no published 1.2.0 image | [HOWTO](evidence/n1_n4_2026-10-18/HOWTO.md) | E1 after CI |
| dust | generator and complete measurement; the guard is written and off (fails its own acceptance); the organizers' dust gives no STOP/CAUTION on 1.1.0 | [N3](evidence/n3_dust_2026-10-18/README.md), [handoff](evidence/n3_dust_fix_2026-10-19/HANDOFF.md) | P0 re-check on the final configuration |
| second lidar, different axes | profiles `falcon_ros` / `falcon_native`; the default launch adopts the right orientation at frame 1 on the supplied recording; L16/S3 (ring-free orientation, a 90°-rolled mount) done by P3, on, P4 review pending | [N2](evidence/n2_falcon_2026-10-18/README.md), [L16/S3](evidence/l16_s3_2026-10-19/README.md) | P4 review |

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
| **No labels; marked bags + order of appearance** | intake done 19.10 ([evidence](evidence/synth_markers_2026-10-19/README.md)): same clouds as 16.10, markers = `obstacles.md` 24/24, N5 matches 1,672 / 1,684 rows; objects inside 2.5–250 m count, beyond is not a miss (synthetic returns reach 737 m), a missing marker is not a negative | P4 (N5) |
| **Dust in every new synthetic bag, at least twice** | the 17.10 "no dust in this delivery" was wrong: 11 bursts of 1–4 boxes, 1–14 points, 1–2 frames, 3.4–7.2 m ahead; 1.1.0 gives no `STOP` and no `CAUTION` on it (13 frames) → a non-regression set for the dust guard. The N5 "false STOPs on background" are structures, not dust | P1's agent (re-check), P4 |
| Not answered: the filter (Q3), bag playback (Q5), O1 | unchanged assumptions | P1 |

## History

Closed and superseded cards (S1, X1, X3, C2, E2, N1/N2/N4, D1 detail), the 16.10 integration ledger (§2), the dated plans of
15–22.10 (§4, §5, §8d), the competitor-survey table (§7), the 17.10 update (§8) and the per-role tables of 19.10 (§9d) are in
[`archive/BACKLOG_history_2026-10-19.md`](archive/BACKLOG_history_2026-10-19.md).
