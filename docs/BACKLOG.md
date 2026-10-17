# Backlog: remaining criteria work

> **Purpose:** what is left to gain on the eight criteria of ТЗ §8 after the independent judgement of
> 13.10 (66/100): one card per work item with its evidence, cause, tasks, acceptance check, owner
> role, mode and size; the order up to the defence on 23.10 and the load per role. What the agent
> session of 13–16.10 measured and selected is listed separately (§2).
> **Audience:** P1 (to distribute the work), team · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-10-15: every cause and line reference against the sealed `707ea9c`
> (v1.0.0 detector) by four read-only researchers and one critic; numbers recounted from the judge's
> per-frame outputs (`docs/evidence/judgement_2026-10-13/out/`, `raw.tar.xz`). Line numbers in
> `resense/` have shifted with the 1.1.0 reseal (§2): search for the named function.
> **Updated:** 2026-10-16: selected scope `c9aea87`, H1 DROP; replacement H3/probes and fresh
> independent H4 complete; H5 DONE at `5211565`, 1.1.0 sealed 16.10. Inherited High 8.1 OPEN;
> H6/CI/main and E1 PENDING.
> **Status:** current; §2/§2a are the integration ledger, later dates are conditional planning targets;
> §2a hands the session's unfinished work over, §5 distributes all of it per role (15.10);
> §7 (16.10) attaches the competitor survey and the experts' message of 16.10 (cards N1–N4)

## 1. How to use it

* **Roles** (the repo names roles, not people; [`PLAN.md`](PLAN.md) §roles, ownership map
  [`CAPTAIN.md`](CAPTAIN.md) §8): **P1** captain (ROS node, Docker, CI except pytest, release,
  docs, the detector seal, the pitch since 29.09) · **P2** frontend / visualization (`web/`, RViz,
  deck visuals, video) · **P3** CV engineer (`resense/` detector modules, `native/`, config values)
  · **P4** data / evaluation (datasets, metrics, eval scripts, regression gate, labels, tests;
  standing duties dropped 25.09: if nobody takes the role, P1 runs P4's items with agents). Assign a
  person to each role before handing out cards; §5 says who does what and where to start.
* **Mode:** **H** needs a human (organizers, a tag push, hardware, rehearsal); **A** an agent can do
  it and a human merges; **H+A** both. **Size:** S < 0.5 day, M 1–2 days, L 3+ days.
* **Points** are the judge's own deductions (`docs/evidence/judgement_2026-10-13/scores.json`)
  that the item can win back; they are estimates and not additive with certainty.
* **Every detector item** (anything under `resense/`, `native/`, `configs/`,
  `ros2_ws/src/resense_ros/config/`, `setup.py`, `pyproject.toml`) follows
  [`DETECTOR_FREEZE.md`](DETECTOR_FREEZE.md): branch from the latest seal, commit the acceptance
  test first, full regression gate exit 0 without `--allow`, independent safety review, then P1
  reseals with the version bump inside the reseal (the bump touches sealed files) and pushes the
  tag. Detector items are therefore shipped as **one bundle per seal**, not one by one.
* **Data and tools:** recordings and caches as in [`VM_GUIDE.md`](VM_GUIDE.md) §2 (the ride cache
  is ~5 GB with `scripts/cache_extended_ride.py`). Gate:
  `python scripts/regression_gate.py --cache <cache> --jobs 2 --baseline docs/evidence/results/regression_baseline_2026-09-29_shell_off.json`
  (~10 min at `--jobs 2` on 4 vCPU, ~7 min at `--jobs 4` on the team VM). The judge's tools are in
  `docs/evidence/judgement_2026-10-13/scripts/`: `range_test.py` (ray-cast object on real frames),
  `probe.py` (whole recording with perturbations), `judge_runner.py` (the node's decode and decision
  rule); their `run_*.sh` wrappers hard-code the judge's sandbox paths, so set the cache directory
  yourself, and build node-decoded caches with `cache_decoded.py`. To run a worktree's detector set
  both `PYTHONPATH=<worktree>` and `RESENSE_REPO=<worktree>` and check `resense.__file__`: the
  editable install otherwise imports the main checkout silently.

## 2. Integration outcomes and selected scope (16.10)

Authoritative scope/acceptance links: [integration checkpoint](evidence/integration_2026-10-16/README.md).
Reviewed committed scope is **`c9aea87cb5322092070158cd8987115ee44833c9`**,
after shipping default withdrawal **`795a243`**. Final measured **1.1.0** source is
**`52115654417a660669b8dddfce447692c1d782cc`**, with the numerical core/config unchanged.
The [current 16.10 seal](evidence/detector_freeze_2026-10-16_1.1.0.json) was committed at
`d6319c2` from source/evidence commit `21e1d61`; clean-LF proof `ec81e78` is retained in
[H5](evidence/integration_2026-10-16/h5/README.md). Published tag/archive remains **v1.0.0**;
1.1.0 is sealed but **unreleased**, H6/CI/main and E1 pending; no new J1 score.
Original handoffs remain dated evidence; their branch names are historical identities.

| what | judge problem | actual state on 16.10 |
|---|---|---|
| H1 / original column free-top and hardening | #1 critical | **DROP after H4**, per ship-at-no-cost-or-drop plan. Nominal gates passed, but exact dark excess remained **9+5**; inherited tall miss and returning-hit gap confirmed. Zero-dark author attempt lost A-axis **157→139/177** and other positives; rejected. `column_free_max_top=0` in class/YAML/ROS. Withdrawal measured **82/177**, exact sealed scored frame set; entire dark pieces 1/3 **14/2 STOP**, zero extras/losses and feature/observer calls. Inherited High tall miss **OPEN 8.1** |
| Structure-surface cut + H2 physical evidence bar | #2 high | **Integrated/selected, revised-scope H4 accepted.** Residual 1.3 m, ≥8 voxels and full physical **0.1°** azimuth span. Separate H2 candidate: mast false matches **2→0**; selected withdrawal reconfirms C person **82.77 m / 55** (sealed 73.94 m / 49), six added matched frames, none lost. Independent H4 covers physical boundaries and paired clustering; ordinary H3 emits no cut candidates |
| Honest monitored range (`track.axis_wall_drift=0.8`) | #2, part of #4 | **Integrated/selected, replacement H3 PASS / fresh H4 accepted.** Complete 18,329-frame audit explains only intended range/additive effects after registered timing normalization; monitored reduced in **2,131**, clear in **1,834** frames, no increases. Axis/corridor not moved; K2 remains open |
| Curve-entry axis-weighting trials | #4 | **Rejected**, three failed gates (ride +6/+9/+7 events); preserved in archive/history, not shipping |
| S1 | startup / freshness | **FAIL, removed from runtime.** Queue 40, startup step 0, lag 20 s, original freshness/drop accounting; no S1 Python cap/adaptive step/one-period allowance |
| C1 | informative CAUTION | Shared v1 and strict raw validation selected; runtime v2 rejected. **Offline experimental v2 FAIL:** 30.46% CAUTION, 19 lost labelled frame alerts |
| E2 | offline rebuild / non-root player | **Local PASS**; new release-workflow check implemented, new tag execution still pending |
| H0 / X3 / G3 | evaluation | H0 **PASS**, 208/208 non-latency rows identical. X3 **40-case v1.0.0 baseline**, not candidate PASS. G3 **spec only**, no held-out result |
| P2 D1 / PT1 | documentation / pitch | Pass 1 integrated; final numerical pass waits for J1. Current score/numbers remain explicitly **v1.0.0**, no new judge score |
| O1 | organizer permission / format | Prepared **not sent**, no reply |
| Version 1.1.0 / seal / main | release | **H5 DONE:** all four versions 1.1.0 before final gate; 208/208 non-latency rows identical, same 146 gated rows passed, all 18,329 frames unchanged vs reviewed scope outside registered timing. Current 16.10 manifest/clean-LF verification **PASS**. **H6/CI/main and E1 pending**; no new tag/archive or score |

### 2a. Acceptance results and remaining handoff (16.10)

The preserved [old H3 PASS](evidence/integration_2026-10-16/h3/README.md) measured **`f8c088d`**
with H1 enabled. The [old H4 safety BLOCKED](evidence/integration_2026-10-16/h4_safety/README.md)
and [correctness PASS](evidence/integration_2026-10-16/h4_correctness/README.md) keep their exact
scope/verdicts. Disabling H1 selects a smaller bundle; it does not rewrite these measurements.

| step | owner | current state / remaining acceptance |
|---|---|---|
| H0 | P4 | **PASS:** exact `707ea9c`, verified caches, 208/208 rows; [P4](evidence/p4_start_2026-10-15/README.md) |
| H1 | P3 → P1/P4 | **DROP; withdrawal checks DONE.** [Results](evidence/integration_2026-10-16/h4_fixes/columns/WITHDRAWAL_RESULTS.md), published `829b243`, measured `c9aea87`: **260 passed, 6 existing external-data deselections**, no failures/errors/skips; A-axis **82/177**, C-person **82.77 m / 55**; entire 1,409-frame pieces 1/3 **14/2 STOP**, zero extra/lost STOPs or feature/observer calls. Registered protocol and failed acceptance bytes preserved |
| H2 | P3 → P1/P4 | **DONE for selected scope:** integrated, full selected gate PASS, C-person retention reconfirmed and fresh independent H4 accepted, including **36 angular/voxel boundary cases** and the paired clustering route |
| H3 | P1 | **DONE — replacement PASS**, [selected H3](evidence/integration_2026-10-16/h3_selected/README.md), published `5282d6f`, measured exact `c9aea87`: clean Linux/native full gate exit 0, no waivers/overrides; **208/208 non-latency rows identical**, same **146 gated rows passed**; **18,329/18,329 raw/serialized frames** compared against same-runtime sealed `707ea9c`, all differences explained |
| H4 | P4, independent of authors | **DONE — revised-scope ACCEPTED**, [fresh independent H4](evidence/integration_2026-10-16/h4_selected/README.md), published `70072f1`, reviewed `707ea9c..c9aea87`: **306 passed**, zero failures/skips/deselections, **1,344 paired Tracker updates per source**; no supported **NEW medium-or-higher** finding remains. Inherited **High tall miss OPEN 8.1**; original safety **BLOCKED** unchanged |
| H5 | P1 | **DONE — 1.1.0 sealed 16.10:** [final H5](evidence/integration_2026-10-16/h5/README.md), measured `5211565`, all four version declarations 1.1.0 before gate. **208/208 non-latency rows identical**, same **146 gated rows passed**; all **18,329 raw/serialized frames**, zero non-latency changes vs reviewed `c9aea87`. [Manifest](evidence/detector_freeze_2026-10-16_1.1.0.json) source/evidence `21e1d61`, seal `d6319c2`, proof `ec81e78`: **PASS before/after native rebuild** in clean LF Linux. Parent owns default-pointer/freeze-overview integration |
| H6 | P1 | **PENDING:** complete CI and normal history-preserving merge into `main`; E1 tag/archive verification remains separate. [Verified archive](evidence/integration_2026-10-16/branch_archive/README.md) prepared; parent verifies final-main restore and refreshed refs/worktrees before retirement |

## 3. Starting point and summary

Judgement of 13.10 on v1.0.0: 8.1 **15**/25 · 8.2 **9**/15 · 8.3 **7**/10 · 8.4 **8**/15 · 8.5 **7**/10 ·
8.6 **8**/10 · 8.7 **8**/10 · 8.8 **4**/5 = **66**/100. Points still lost: 8.1 −10, 8.4 −7, 8.2 −6,
8.3 −3, 8.5 −3, 8.6 −2, 8.7 −2, 8.8 −1.

**Before you start:** the upload closed 29.09 and the expertise of 30.09–14.10 ran on v1.0.0.
Whether anything after v1.0.0 can still count is the organizers' answer (card O1, today). The
"when" column assumes it can; if not, see §4 "if O1 says v1.0.0 only".

| id | item | criteria | owner | mode | size | points | when |
|---|---|---|---|---|---|---|---|
| H0 | PASS: verified local data/caches, baseline gate on exact `707ea9c`, 208/208 rows identical | enabler for all detector work | P4 | H+A | S | enabler | done 16.10 |
| H1 | DROP: free-top off at class/YAML/ROS defaults; withdrawal probes/dark complete, inherited High tall miss OPEN | 8.1, 8.4 | P3 | A | S | no #1 fix credited | done 16.10 |
| H2 | Physical 0.1° azimuth-span bar integrated; C-person retention and independent boundaries/route accepted | 8.1 | P3 | A | S | protects #2 fix | done 16.10 |
| H3 | PASS: replacement full gate and complete explained frame diff on exact selected `c9aea87` (§2a) | 8.1, 8.2 | P1 | A | S | enabler | done 16.10 |
| H4 | Revised difference ACCEPTED; no NEW medium+, inherited High OPEN; old safety BLOCKED / correctness PASS preserved | 8.1 (DETECTOR_FREEZE step 3) | P4 | A | S | enabler | done 16.10 |
| H5 | DONE: all four versions 1.1.0 before passing final gate, 16.10 seal and clean-LF verification (§2a) | 8.6 | P1 | A | S | enabler | done 16.10 |
| H6 | 17.10: integration merged into `main` as **squash** PR #33 (`44b462e`, detector = sealed 1.1.0); no tag yet; history-preserving merge still needed for the branch archive (§8) | 8.6 | P1 | H | S | enabler | merge done; history fix + E1 next |
| O1 | Ask the organizers: pitch format, whether v1.1.x may be shown or re-run, results before 23.10 | 8.8 (gates 8.1–8.6) | P1 | H | S | decides ~3–6 | 15.10 |
| E1 | Ship 1.1.0: PR to `main`, tag `v1.1.0`, verify the release, fix the jury block; repeat as v1.2.0 | 8.6 (enabler) | P1 | H+A | S | +0.25 | 18.10, 20.10 |
| S1 | FAIL; runtime removed, published queue/freshness retained; new diagnosis remains open | 8.3, 8.6 | P1 | A | M | ~+2 if accepted later | reopen after diagnosis |
| E2 | Local offline PASS; new release-workflow check awaits tagged execution | 8.6 | P1 | A | S | +0.5 | local done; E1 pending |
| C1 | Shared v1 selected; v2 offline-only FAIL (30.46%, 19 lost alerts), runtime rejects v2 | 8.1 | P1 | H+A | M | +1 if v2 accepted later | acceptance open |
| C2 | `clear_distance` consistent with the advisory output; publish the overclaim scorer | 8.1 | P3 | H+A | S | +0.5 | 19–20.10 |
| X1 | DONE 16.10: cause tables on 707ea9c and 1.1.0, traced tracker branches, label check 64/64 per version ([X1](evidence/range_attribution_2026-10-16/README.md)) | 8.2 (enabler) | P4 | A | S | enabler | done 16.10 |
| X3 | DONE 16.10: 1.1.0 PASS, all 40 cases identical to v1.0.0; Linux = Windows with the OpenBLAS kernel pinned ([P4](evidence/p4_eval_1.1.0_2026-10-16/README.md)) | 8.4, 8.7 | P4 | A | S | +0.5 | done 16.10 |
| G3 | Specification registered; no held-out execution/result | 8.7, 8.4 | P4 | A | M | up to +1.5 after actual run | spec done; run target 21.10 |
| J1 | Re-judge the shipped seal; dry run reproduces 13.10, 37 range jobs + six bags pre-built on 1.1.0 ([runbook](evidence/rejudge_2026-10-16/RELEASE_DAY.md)); release-only steps wait for E1 | evidence for all | P4 (P1 reads `delta.md`) | A | M | protects 8.2, +0.5 8.5, +0.5 8.8 | ~3–4 h after E1; run 2 21.10 |
| K1 | Standing train: far axis jitter → STOP flicker at 100–150 m and perturbation-sensitive platform false STOPs | 8.2, 8.4, 8.1 | P3 | A | M | +1 to +1.75 | 18–20.10 |
| R1 | 0.3 m objects confirmed only from ~45 m (hardware rule, low stage ends at 60 m) | 8.2, 8.1 | P3 | A | M | ~+0.5 | screen 16–17.10, ship 18–20.10 |
| R2 | Sparse far objects: the point bar leaves an 80–100 m hole (0.5 m cube, set O small_center) | 8.2, 8.1 | P3 | A | M | +0.5 to +1 | screen 16–17.10, ship 18–20.10 |
| R3 | Thin cables: hanging 5 cm object STOP only from 30 m, standing 5 cm cable from 60 m | 8.1, 8.2 | P3 | A | M | ~+0.5 | 19–20.10 if time |
| F1 | Near-field low-object false STOPs at the rail-head plane (5 of 6 ride episodes below 40 m) | 8.1, 8.4 | P3 | A | M | +0.5 to +1 | 18–20.10 |
| S2 | 360° per-frame cost: native single-pass decode, per-stage profile | 8.3 | P3 + P1 | A | M | +0.5 to +1 | 19–20.10 if time |
| S3 | Cap the orientation-search cost while the configured mount has not passed | 8.3, 8.4 | P3 | A | S | protects ~1 | 18–19.10 |
| S5 | Measure the selected node on available hardware, including the literal player; 8-core host optional (captain, 17.10) | 8.3 | P2 / available operator | H | S | ~+0.5 | 21.10 |
| D1 | Fix ~28 stale or contradictory statements in 13 docs; SCORECARD and ownership map current | 8.5, 8.8 | P2 (agent; P1 approves the PR) | A | S | ~+0.5 | 15–16.10, 21.10 |
| PT1 | Pitch content for the shipped seal: lighter deck, honest range by track shape, node-path numbers | 8.8 | P1 | H+A | M | up to +1 | 18–21.10 |
| PT2 | Live demo on the shipped image and two timed rehearsals with a fallback | 8.8 | P1 | H | M | protects 1–2 | 19.10, 22.10 |
| X2 | False-STOP ledger with pass-by ground truth and a fast window replay | 8.1, 8.7 (enabler) | P4 lane | H+A | M | +0.25 | after 23.10 |
| F2 | Far-onset false STOPs at ≥ 100 m (half of all episodes), after the X2 audit | 8.1 | P3 | A | L | +0.5 to +1 | after 23.10 |
| K2 | Curve and double-track axis (curve-entry lag, 60 m cap when walls disagree) — read the round-3 evidence first | 8.2, 8.4, 8.1 | P3 | A | L | +1 to +2.5 | after 23.10 unless round 3 (B) shipped |
| S4 | Dual-return duplicates: the track model counts raw points, so decisions follow the driver's return mode | 8.4, 8.3 | P3 | H+A | L | up to +1.5 | after 23.10 |
| G1 | Rule provenance: ablate every rule justified by a named recording | 8.4, 8.7 | P3 | A | M | up to +1.5 | after 23.10 |
| G2 | Doubt model: cross-fit on the current detector, keep only if it earns its place | 8.4 | P3 | A | M | ~+0.5 | after 23.10 |
| T1 | Next seal: remove dead switches, code-only parameters into the YAML, decision function into `resense/` | 8.5, 8.4 | P3 | A | M | +0.75 to +1.25 | after 23.10 |
| D2 | Archive the 28.09 experiment layer: 20 process notes, personal-path tests, orphan scripts | 8.5, 8.7 | P2 (agent; P1 approves) | A | S | ~+0.75 | after 23.10 |

## 4. Order up to the defence (23.10)

The bottleneck is CPU for ride replays and full gates: run them on the team VM. Detector items go
into **one bundle** (`det/1.2.0` from the 1.1.0 seal) with one combined gate, one safety review
and one reseal; items that miss the cut-off do not ship.

The calendar below is the **original conditional plan**, not completion evidence. The actual
16.10 ledger is §2/§2a: H1 dropped, S1 and offline C1 v2 failed, replacement H3/probes/H4 and
H5 complete; **1.1.0 sealed 16.10**. H6/E1 target 18.10 and a later 18–20.10 bundle remain
conditional; the calendar's original H5 date below is superseded by the actual H5 receipt.

* **15–16.10:** P1 sends O1 first (its answer is the branch point) and sets the C1 semantics; P1's
  agents start S1, E2 and the C1 policy module (node lane, no seal). P4 builds the data and caches
  on the team VM and reproduces the baseline gate (H0), commits the G3 spec (before anyone tunes,
  or it is not held-out), then X3. P3 starts H1 and H2 in two worktrees and screens the R2 / R1
  config variants with `--set` on `final/silent-misses` (re-checked after the 1.1.0 rebase). P2 runs
  D1 pass 1 and starts PT1's slide cuts (no numbers needed yet).
* **Next acceptance:** replacement H3, withdrawal probes/dark and independent H4 completed
  on `c9aea87`; H5 completed on version-bumped `5211565` with the 16.10 seal. P1 proceeds to
  parent-owned H6/CI/main and later E1, still PENDING until actual receipts.
* **18.10:** review fixes (P3), then P1: H5 (bump to 1.1.0, final gate, reseal) and H6 / E1 (PR,
  CI green, tag `v1.1.0`, release verified). P4: J1 run 1 on v1.1.0 (its range table feeds the deck)
  and X1 on 1.1.0 and on `707ea9c`. P3 opens `det/1.2.0` from the 1.1.0 seal, cheapest first:
  the R2 / R1 variant that passed screening → K1 (after X1) → F1 → S3 → C2 (after C1) → R3 → S2.
* **19.10:** each bundle item measured on its own; only passing items join `det/1.2.0`. P1 + P2
  put J1's numbers into the deck (PT1); rehearsal 1 (PT2) on v1.1.0.
* **20.10, noon cut-off:** P3 combined gate on `det/1.2.0`; P4 independent safety review; P1
  reseals with the version bump, tags `v1.2.0`, releases if accepted. E2/shared v1 are selected;
  S1 and C1 v2 require new passing acceptance before any later shipping decision.
* **21.10:** P4: J1 run 2 on the final seal and the G3 run (a fresh agent). P2: D1 pass 2, S5 on
  available hardware (2–4 cores are acceptable; no 8-core prerequisite), final video cards.
  P1: final numbers in the deck and the speech. New release timing follows the CI repair.
* **22.10:** rehearsal 2 on the final image with the fallback and Q&A drills (P3, P4 as mock jury).
* **After 23.10** (or earlier only if O1 says updates count and CPU allows): K2 unless round 3 (B)
  shipped, X2 then F2, S4, G1 and G2 then T1, D2, J1's raw-path gate mode.
* **If O1 says v1.0.0 only:** keep O1, E1, J1, D1, PT1, PT2 and S1/E2/C1 (they improve the live
  demo and the Q&A); shrink the detector bundle to the evidence the Q&A needs (K1, R1/R2
  measurements); everything else moves after the defence.

## 5. Who does what, and where to start

The repo names roles; write the person next to each role before handing this out. Rules that shaped
the split: the detector lane (P3) writes detector changes; the evaluation lane (P4) prepares the data
and reviews them **independently** (an agent that wrote a change never reviews it); the captain (P1)
integrates, reseals, tags and owns the pitch; P2 takes the docs and the bench off the captain.
If a person is unavailable, P1 runs that role's items with agents in the same order.

| role | original planned queue before 23.10 (resume status below) | estimated load |
|---|---|---|
| **P1** captain | O1 → C1 semantics → H3 → H5 → H6 / E1 (v1.1.0) → PT1 speech and deck → PT2 rehearsal 1 → reseal + tag v1.2.0 → PT2 rehearsal 2; agents on S1, E2, C1 code from 15.10 | human ~3.5 of 8 days (O1 0.5 h, C1 decision 1 h, two integrations / reseals / tags with the review reads ~6 h, J1 reading 2 h, deck and speech 1.5 days, rehearsals 1.5 days); CAPTAIN §3 item 8 (the human read of the 29.09 safety review) is still open |
| **P2** frontend / visuals | D1 pass 1 → PT1 slide cuts → C1 display (`caution_reason` in RViz and the web view) once C1's contract lands → PT1 range chart from J1 → PT2 fallback clip on v1.1.0 and the second demo device → D1 pass 2, S5, video cards (21.10) | ~3 days |
| **P3** detector | H1 + H2 (parallel) + R2 / R1 screening → review fixes after H4 → `det/1.2.0`: R2 / R1 → K1 → F1 → S3 → C2 → R3 → S2 (as many as pass by 20.10 noon) → combined gate | ~10 agent-days in ~5 days: needs 3–4 agents in parallel and the team VM's CPU; the person validates X1's attribution and reads the reviews |
| **P4** data / evaluation | H0 → G3 spec → X3 → H4 (independent review of `final/silent-misses`) → J1 run 1 + X1 → independent review of `det/1.2.0` (20.10) → J1 run 2 + G3 run (21.10) → mock jury | ~3 days, mostly agent time on the team VM |

**Where each role resumes (16.10):**

* **P1:** send prepared O1; read completed H3/probes/H4/H5, finish H6 (§2a).
  Keep failed S1/v2 excluded. Complete the archive/main/cleanup receipt and later E1.
* **P2:** D1/PT1 pass 1 is integrated; synchronize final numerical docs/chart only after J1.
  PT2 rehearsals, S5 and release-matched video remain open.
* **P3:** H1 is DROP, H2 selected; preserve rejected reports. Withdrawal critical/dark
  evidence and revised-scope review are complete; inherited High tall miss remains OPEN 8.1.
  All five cheap R1/R2 overrides were rejected; X1 attribution precedes another candidate.
* **P4:** H0/X3 v1.0.0, G3 registration and fresh independent H4 are delivered.
  Next: new-seal X3/J1; G3 execution remains a separate future final-seal stage.

Original publication identities are pinned in the
[checkpoint's stable handoff table](evidence/integration_2026-10-16/README.md#stable-original-handoffs).
For judge range work **B = roundT_doubleT**, **C = roundT_pressureGate_roundT**;
P4's [intake README](evidence/p4_start_2026-10-15/README.md#shared-data-paths) now records the
dated alias-only correction; full recording names and measured data are unchanged.

**P4 execution, 15–16.10:** the user designated the Windows computer as the team runtime.
H0's local intake is verified: six gate bags + Set O 1,510 + ride 11,271, all receive stamps
checked against raw DB3; node-decoded float32 A/B/C/S, doubleT_obstacle and Set O are ready.
The exact detached `707ea9c` full gate exits 0 without waivers, with **208/208 non-latency
rows identical** to the 29.09 baseline. Shared root:
`C:/Users/alikh/AppData/Local/Temp/opencode/resense-p3-data/{for_hackathon,cache,decoded,odometry}`.
See [P4 evidence and X3 report](evidence/p4_start_2026-10-15/README.md) for exact identities,
paths and commands. This is Windows-native local replay, not Linux VM/node timing; the raw
Windows checkout freeze check fails on CRLF/generated `.pyd`, while all 36 committed seal
blobs match. H5's separate clean-LF Linux seal proof now passes; the 1.1.0 standing X3 baseline
remains future evaluation work, not supplied by the final regression gate.

Rough gain if the pre-defence items land and count (judge's estimates): 8.1 +2 to +3, 8.2 +1 to +2,
8.3 +1.5 to +2.5, 8.4 +0.5 to +1, 8.5 +1, 8.6 +1 to +1.5, 8.7 +1, 8.8 +1.

## 6. Cards

### Organizers and release

#### O1 · Ask the organizers: pitch format, whether v1.1.x may be shown or re-run, results before 23.10
**Progress 16.10:** three-question message prepared, **not dispatched**, no organizer reply.
**Criteria** 8.8; decides whether post-deadline work on 8.1–8.6 counts · **Owner** P1 (an agent
drafts the message) · **Mode** H · **Size** S · **Depends on** nothing; first, 15.10
* **Evidence:** the upload closed 29.09 and the expertise of 30.09–14.10 ran on v1.0.0
  ([`PLAN.md`](PLAN.md) dates; the judge's `scores.json` commit is v1.0.0).
  [`organizers/answers.md`](organizers/answers.md) has no entry after 29.09; the pitch length was
  never fixed (answers.md row 7 withdrawn 24.09; [`PRESENTATION.md`](PRESENTATION.md) "Длительность
  не названа — готовим 5 минут"). The hidden check is full rides through other tunnels with the
  organizers' synthetic obstacles, control data in "Last and Strongest" dual return.
* **Tasks:** one message to the organizers' chat today with three questions: (a) pitch length, Q&A
  length, screen share, whether a live demo is wanted; (b) may the team present or hand over v1.1.x,
  which fixes faults found after submission (tall narrow objects, the curve merge), and can it change
  any score; (c) will hidden-check results or expert scores be shared before 23.10, and can an
  updated archive be re-run. Record the answer verbatim and dated in answers.md; update the
  requirements section of PRESENTATION.md. If (b) is "v1.0.0 only", mark K2, F2, S4, G1, G2, T1
  post-defence in CAPTAIN §3 and shrink the bundle (§4).
* **Done when:** answers.md has a new dated row answering (a)–(c); the pitch-duration line of
  PRESENTATION.md is updated.

#### E1 · Ship 1.1.0: PR to `main`, tag `v1.1.0`, verify the release, fix the jury block (repeat as v1.2.0)
**Criteria** 8.6 (enabler: no post-seal gain reaches the jury without a published archive) ·
**Owner** P1 (an agent does docs and verification) · **Mode** H+A · **Size** S · **Points** +0.25
on 8.6 directly · **Depends on** the session's 1.1.0 reseal (§2); O1; E2 for the doc part
(failed S1 is excluded from the selected release scope)
* **Evidence:** v1.0.0 is on `5d6e9b5`; the judge verified its archive (477 MB, sha256 OK). Stale:
  README "Пока релиза нет", build times the judge could not reproduce, `--read-ahead-queue-size 10`
  "Обязательно"; CAPTAIN §5 "No tag or release exists yet". `release.yml` triggers on `v*`, and
  `scripts/release_meta.py` rejects a tag whose version differs from the four declarations
  (`pyproject.toml`, `resense/__init__.py`, the ROS `package.xml` and `setup.py`).
* **Tasks:** (1) open a PR from the session's branch to `main`; CI green including the docker job;
  P1 merges. (2) `git tag -a v1.1.0 <merge commit> -m 'ReSense 1.1.0' && git push origin v1.1.0`;
  wait for `release.yml` (30–40 min). (3) Logged out: `scripts/verify_release.sh v1.1.0`, then
  `IMAGE_TAR=resense-image-v1.1.0.tar.gz OFFLINE=1 scripts/dry_run.sh` on doubleT_obstacle and
  roundT_doubleT. (4) An agent updates README, the GitBook acceptance-test page and CAPTAIN §2/§5;
  after S1 the literal `ros2 bag play <bag>` with its measured freshness and the flag made optional;
  after E2 the offline rebuild. (5) Repeat as v1.2.0 for the 20.10 bundle.
* **Done when:** `python scripts/release_meta.py check-tag v1.1.0` succeeds on the merge commit;
  `scripts/verify_release.sh v1.1.0` exits 0 from a logged-out machine; `detector_freeze.py verify`
  passes on the tagged commit; `grep -n 'Пока релиза нет' README.md` returns nothing.

#### E2 · Offline rebuild from the release archive; non-root player without `-e HOME`
**Progress 16.10:** local clean offline rebuild **PASS**; [E2 evidence](evidence/offline_rebuild_2026-10-15/README.md).
New release-workflow check implemented; tagged execution remains pending E1.
**Criteria** 8.6 · **Owner** P1 (agent) · **Mode** A · **Size** S · **Points** +0.5 (the judge's
second −1) · **Depends on** a published archive (E1); `docker/` is not sealed; ships with the next tag
* **Evidence:** judge 8.6 −1: `docker build` needs the internet; a containerised non-root player needs
  HOME. `docker/Dockerfile` says "The build needs the internet" (FROM `ros:humble-ros-base-jammy`,
  apt and pip); `scripts/play_bag.sh` works around HOME with `-e HOME=/tmp`.
* **Cause:** the only offline path is the prebuilt archive; the image sets neither `ROS_HOME` nor
  `ROS_LOG_DIR`, so the ros2 CLI under `--user 1000` writes logs under `HOME=/`.
* **Tasks:** (1) `docker/Dockerfile.offline`: FROM the loaded release image, COPY `resense/ native/
  configs/ ros2_ws/src`, `pip3 install --no-deps .`, colcon build, the import check (g++ is in the
  image). (2) `ENV ROS_HOME=/tmp/.ros ROS_LOG_DIR=/tmp/.ros/log` in `docker/Dockerfile`. (3)
  `release.yml`: after the archive reload, build `Dockerfile.offline` with `--network none`. (4)
  README: the CI-measured build time and the one-line offline rebuild (via E1).
* **Done when:** `docker load -i resense-image-<ver>.tar.gz && docker build --network none -f
  docker/Dockerfile.offline -t resense:offline .` then `docker run --rm --network none resense:offline
  python3 -c 'import resense, resense._native as n; print(resense.__version__, n.status())'` prints
  the version and "native"; `docker run --rm --net=host --user 1000:1000 -v <bags>:/data:ro resense
  ros2 bag play /data/roundT_doubleT --read-ahead-queue-size 10` runs without `-e HOME`; the release
  workflow is green with the new step.

### Speed and launch

#### S1 · Freshness-first start-up catch-up and a memory bound: the literal `ros2 bag play <bag>` gives current results
**Progress 16.10:** original-bag Docker acceptance **FAIL**, including verified Linux-volume
follow-up; [P1 results](evidence/p1_start_2026-10-15/README.md). Runtime candidate withdrawn;
the tasks/thresholds below remain unmet goals, not selected node defaults.
**Criteria** 8.3, 8.6 · **Owner** P1 (agent writes code, tests, Docker A/B; the captain approves
the policy reversal) · **Mode** A · **Size** M · **Points** ~+2 (8.3 +1 to +1.5, 8.6 +0.5 to +1)
· **Depends on** nothing to implement (the node is not sealed); a later tag requires new passing acceptance
* **Evidence** (judge Docker chain, `out/raw.tar.xz` `docker/`): literal player 360° 146/201 frames
  processed, 0 fresh, age p50 7.33 s / max 10.51 s, RSS 3,357 MB; README flags 35/201 fresh, age max
  1.2 s; roundT_doubleT literal 47 FAULT results in the first ~5 s. The team's own A/B with
  `catchup_startup_step` 0.2 ([`evidence/node_startup_2026-09-29/`](evidence/node_startup_2026-09-29/README.md))
  cut the first-3 s median e2e from 312–325 to 38–105 ms; [`MAIN_SYNC_2026-09-28.md`](MAIN_SYNC_2026-09-28.md)
  kept 0 because STOP counts were 185–189 instead of 190.
* **Cause** (`ros2_ws/src/resense_ros/resense_ros/detector_node.py`): `input_queue_depth` 40,
  `catchup_startup_max_lag` 20 s, `catchup_startup_step` 0.0 (repeated in `launch/detector.launch.py`);
  `prune()` keeps every frame as a chain link for up to 20 s of lag; `take_waiting()` moves DDS
  messages into the Python list `self.pending`; non-catchup invalid freshness becomes health error →
  FAULT. At 360° on 4 vCPU throughput (~11–12 fps) barely beats 10 Hz, so the backlog never drains.
* **Tasks:** (1) default `catchup_startup_step` 0.2 s and `catchup_startup_max_lag` 2–3 s; widen the
  step adaptively when processing time × step / period ≥ 0.8 (≤ 0.3 s, so the 1 s hole reset never
  fires). (2) `max_pending_frames` (12) enforced in `prune()` and `take_waiting()`;
  `input_queue_depth` 12–16 in the node and launch. (3) Rewrite the `tests/test_node.py` cases that
  encode the every-frame policy; add a burst test (10 s backlog at 10× real time, 90 ms work per
  frame: pending ≤ 12, a result ≤ 0.5 s old within 3 s of the burst's end, no reset after the first
  frame). (4) Copy the judge's `docker/` chain scripts into a new evidence folder; run the 4
  conditions ×3 on an idle 4-vCPU machine. (5) Update the node docstring, ARCHITECTURE, DECISIONS
  (this reverses MAIN_SYNC; captain signs off), the README jury block (via E1).
* **Done when:** `pytest -q tests/test_node.py` passes incl. the burst test; median of 3 runs:
  README flags fresh ≥ 180/201, age max ≤ 0.6 s, STOP results ≥ 185, first STOP ≤ 1.2 s after the
  first result; literal player ≥ 80 % fresh, age p50 ≤ 0.5 s, container memory ≤ 1,200 MB, first
  STOP at 55–57 m; roundT_doubleT literal FAULT results ≤ 10, README flags fresh ≥ 242/252; CI green.

#### S2 · 360° per-frame cost: native single-pass decode, then a per-stage profile
**Criteria** 8.3 · **Owner** P3 (`native/`) with P1 (`fastcloud.py`, node) · **Mode** A · **Size** M
· **Points** +0.5 to +1 (the other half of the −2) · **Depends on** 1.1.0; best measured after S1;
ships in the 1.2.0 bundle (`native/` and `resense/` are sealed)
* **Evidence:** judge offline 360° decode+detect p50 78–86 / p95 106–119 ms, 18–34 of 200 frames
  over 100 ms; decode p50 30.5–33.3 ms (35–40 %); 120° stays real-time (p95 72–76 ms). Ride: 422
  frames over 100 ms, 387 of them in frames 5000–7000 (detect p50 129.6 ms in 5700–6000; possibly
  contention in the judge's streaming; unproven).
* **Cause:** `fastcloud.py` decode touches all 921,600 slots (a block copy, three passes, three
  masks, gathers); decode and detect run serially in the subscription callback of a
  single-threaded executor; `resense/health.py` runs `arctan2` over the whole cloud.
* **Tasks:** (a) `rs_decode_xyzir` in `native/resense_native.cpp`: one pass over the 26-byte layout
  with the same float32 order and thresholds, called from `fastcloud.decode` via `resense/_native.py`
  with the numpy fallback kept. (b) Profile 1.1.0 per stage (`python -m resense.cli bench`) on
  doubleT_obstacle and ride splits 111–117; decide whether the ride window is real. (c) Only if
  health's `arctan2` costs > 2 ms: reuse round 3's per-frame azimuth cache. (d) Only if 360° p95 is
  still > 100 ms: decode the next frame on a worker thread (node only).
* **Done when:** `scripts/check_fast_input.py` on doubleT_obstacle and roundT_doubleT in the image
  exits 0 (byte-identical) with 360° decode median ≤ 8 ms; two `judge_runner.py` runs on
  doubleT_obstacle on an idle 4 vCPU: p95 ≤ 95 ms, ≤ 5/201 frames over 100 ms, decisions identical;
  gate exit 0 with identical decision rows; the ride-window profile committed with a verdict.

#### S3 · Cap the orientation-search cost while the configured mount has not passed
**Criteria** 8.3, 8.4 · **Owner** P3 · **Mode** A · **Size** S · **Points** 0 on the judged data;
protects ~1 if the control data uses another mount or starts without a rail pair · **Depends on**
1.1.0; the 1.2.0 bundle
* **Evidence:** `MountCalibrator._search_orientation` over 7 candidates took 662 ms on one
  doubleT_obstacle frame (346k points; 847 ms rotated 90°) and 239–365 ms on roundT_doubleT, against
  detect p50 32–47 ms; it never triggers on the organizer recordings. The LiDAR position "is not
  fixed" (answers.md).
* **Cause:** `resense/calibration.py` runs `_search_orientation` on every frame while the configured
  mapping fails (no rail pair at 2–45 m, or a forward/rear ratio < 1.5), for up to `max_frames` 400
  periods; each candidate transforms the full cloud and masks all points.
* **Tasks:** subsample once to ≤ 60k points before the candidate loop (scale the `fwd ≥ 200` test or
  pass the counts); optionally search every 3rd frame; a unit test that every call gets ≤ 60k
  points on a 350k-point frame; keep the rotated-mount calibration tests passing within the same
  frame count; a counter proving the search never runs on gate data.
* **Done when:** `pytest -q tests/test_calibration.py` passes; median of 5 runs of the search on the
  cached doubleT_obstacle frame 50 rotated 90° ≤ 60 ms on an idle 4 vCPU; gate exit 0 with
  identical rows.

#### S5 · Available-hardware bench of the selected node including the literal player
**Captain update 17.10:** an 8-core VPS is not required now. Measurements on available hardware,
including 2–4 cores, are accepted with the actual resources and results recorded. More cores
are a possible later comparison, not a prerequisite or an inferred benchmark result.
The captain handles GitHub quota/billing; release waits until CI is fixed. Source-checkout
measurements can proceed now and remain labelled as such until release identity is verified.

**Criteria** 8.3 · **Owner** P2, or the available machine operator (an agent writes the summary;
P1 quotes it) · **Mode** H · **Size** S · **Points** ~+0.5 through confidence · **Depends on** S1, S2,
the final image
* **Evidence:** the judge timed on 4 vCPU only (8.3 confidence "medium"); the stand is an
  i7-9700E with 8 cores; the team VM of 28.09 (4C/8T) gave 360° node mean 52.9 / p95 62.8 ms against
  the judge's 88/111 ms; `scripts/bench_8core.sh` (CAPTAIN §3 item 9) was never run.
* **Tasks:** on an idle available machine run `scripts/bench_8core.sh` (historical filename; no
  minimum core-count check) with the selected
  image plus the 4 Docker chain conditions of S1; record `lscpu`, disk read speed (360° playback
  needs ~225 MB/s) and numpy in the image; commit `docs/evidence/bench_<date>/`; quote the numbers
  with the hardware named in README and ARCHITECTURE (via D1).
* **Done when:** `RESENSE_DATA=<bags> RESENSE_CACHE=<cache> scripts/bench_8core.sh` exits 0;
  `summary.json` has the 360° node p95 and the four chain summaries (target: README flags p95 ≤ 80
  ms, fresh ≥ 195/201), each explicitly PASS/FAIL; `facts.txt` records actual CPU topology,
  affinity/quota and memory. The core count alone neither blocks nor establishes acceptance.

### Decision outputs

#### C1 · CAUTION policy: one shared decision function, CAUTION only where it carries information
**Progress 16.10:** shared v1 selected; **runtime v2 rejected**. Offline v2 **FAIL**: 30.46%
CAUTION versus ≤25%, 19 lost labelled frame alerts ([screen](evidence/caution_policy_2026-10-15/EVIDENCE.md)).
The proposed column suppression below is not shipping semantics: H1 is dropped and inherited
column misses remain open. New accepted semantics/measurements are required before enabling v2.
**Criteria** 8.1 · **Owner** P1 (node lane; P2 for the display) · **Mode** H+A · **Size** M ·
**Points** +1 (judge −2: "CAUTION on 35–67 % of empty frames carries little information") ·
**Depends on** an accepted column policy (not supplied by the selected 1.1.0 scope); K1 for the axis uncertainty σ(D) (start at 80 m); ships
with the next tag; no reseal (the policy module lives outside the sealed directories)
* **Evidence** (recounted from the judge's outputs, 6 obstacle-free recordings): CAUTION on 5,872 of
  13,558 frames (43.3 %); 1,096 (8.1 %) carry a `column` advisory. Offline re-score of the saved
  outputs: without column CAUTION 39.4 %; range demotions only when compact 33.6 %; margin
  advisories only within 80 m 26.9 %, within 60 m 21.8 %. Set O non-STOP CAUTION frames on labelled
  objects 75 → 62 at 80 m. The node adds catch-up CAUTION (roundT_doubleT README-flags run 9/252).
* **Cause:** `resense/detector.py` sets `warning` for any confirmed advisory and makes every
  confirmed track with zone ≠ gauge an advisory whatever its reason; the node's `decision()` turns
  any warning or health warn into CAUTION; a catch-up lag > 0 makes freshness "catchup" → warn →
  CAUTION with the ranges zeroed. The rule is copied in `scripts/score_clear_distance.py`,
  `scripts/hero_view.py`, `scripts/synthetic_sensitivity.py`,
  `scripts/analyze_cross_ring_measurement.py` and `webapp/backend/resense_web/decision.py`.
* **Tasks:** (1) the captain fixes the semantics: CAUTION = an unexplained object next to or
  entering the envelope, within the range where the envelope edge is resolvable. (2) Implement
  `decision(res, policy)` once in `ros2_ws/src/resense_ros/resense_ros/decision_policy.py` (no
  rclpy); the node, a new `scripts/rescore_decisions.py`, the scripts above and the webapp import it;
  policy parameters in the launch PARAMS, not the sealed `detector.yaml` (T1 moves it into
  `resense/` later). (3) Proposed policy v2: no CAUTION for `column` only after a separately
  accepted column fix (not supplied by this 1.1.0 scope), or non-compact range
  demotions; margin advisories only within D_c (80 m to start); keep health warn and doubt. (4) The
  original one-period catch-up freshness proposal was rejected with S1; selected runtime retains
  published freshness. (5) `caution_reason` in the status JSON
  (`[contract]` in the PR title, CAPTAIN §6); P2 shows it in RViz and the web view.
* **Done when:** `python scripts/rescore_decisions.py --policy v2` on the 1.1.0 judge-runner
  outputs (five empty bags + ride) gives CAUTION ≤ 25 %; set O CAUTION-or-STOP frames on in-gauge
  objects and range_test B/C CAUTION+STOP while visible are no fewer than v1; roundT_doubleT
  catch-up CAUTION 9 → 0; `tests/test_node.py` and the CI docker job green.

#### C2 · `clear_distance` consistent with the advisory output; publish the overclaim scorer first
**Progress 17.10: revised conservative profile ACCEPTED.** The captain explicitly approved
“Use conservative ranges and record the measured loss.” Shared node/offline reporting and the
scorer are implemented on `work/n5-labels-c2-acceptance`. Select
`clear_range_policy:=conservative range_sensor_model:=pandar128`; legacy remains the launch
default until release integration. Revised acceptance retains at least **65%** of each empty-bag
median (measured worst retention **65.3%**) and gives **GO 4 / CAUTION 0** under the existing
0.5 m measured-envelope score. Independent review and local checks pass.
**Original 90% retention acceptance remains FAIL.** The reconstructed historical intended-gauge
score still has GO 40 / CAUTION 11; these are not claimed fixed. The exact 148/694 control
reconstruction, both populations, residuals and scoped validation are published in
[C2 evidence](evidence/c2_acceptance_2026-10-17/README.md). Release/DDS acceptance is deferred.

**Criteria** 8.1 · **Owner** P3 (P1 for node exposure and docs) · **Mode** H+A · **Size** S ·
**Points** +0.5 (judge −1) · **Depends on** C1 (predicate); round 3's honest monitored range (§2) —
build on its cap
* **Evidence:** judge: `clear_distance` reports the path clear beyond a visible in-gauge object in
  148 of 694 set O frames (90 GO); the scoring script is not in the repo. A researcher recount
  (≥ 1 point in the rail envelope and clear > x + 1 m) gives 52/598 (26 GO, 24 CAUTION, 2 STOP),
  47 of them probably the intended-outside objects; e.g. frame 526 is CAUTION at 13.7 m with clear
  201 m.
* **Cause:** the clear cap counts only clusters with ≥ 1 strict voxel (`detector.py` clear cap;
  `clear_cap_min_gauge` 1, `clear_cap_margin` −1, columns skipped); `health.py` takes min(monitored,
  obstacle, cap), so the margin advisory that raises CAUTION never shortens `clear_distance`. The
  earlier "every return caps" rule was rejected (+15 to 50 pp uncertain frames).
* **Tasks:** (1) commit `scripts/score_overclaim.py` with an explicit definition; reproduce 148/694
  on the 13.10 outputs or document the difference. (2) Cap `clear_distance` at the nearest advisory
  that raises CAUTION (C1's predicate). (3) Add `monitored_small`: the range where
  `expected_points(d, 0.3, 0.3) ≥ min_points_far`. (4) Re-score.
* **Done when:** with `score_clear_distance.py` and the new scorer on set O: overclaims with CAUTION
  0, GO overclaims on in-gauge objects ≤ 5; median clear on the five empty bags within −10 % of
  1.1.0 (the captain sets the limit); gate decision rows unchanged, exit 0; safety review.
  **Captain-approved revision 17.10:** replace the −10% range budget with the measured conservative
  outcome, guarded by a **−35%** limit per bag (`conservative_2026_10_17`). The GO/CAUTION
  criterion uses the existing `score_clear_distance.py` measured-envelope population; preserve
  the separately reconstructed intended-gauge results. The accepted explicit Pandar profile
  requires the qualified three-return prior. Canonical-data acceptance exits 0; archived
  decision/detection parity and actual-node unit integration are checked. A new released-image
  Docker/DDS gate is not claimed and remains part of the deferred release work.

### Evaluation tooling (P4 lane)

#### X1 · Range attribution harness: which rule or tracker hold costs each late frame
**Criteria** 8.2, 8.1 (enabler for K1, R1, R2, R3) · **Owner** P4 lane (P1 assigns an agent; P3
validates) · **Mode** A · **Size** S · **Points** none directly; decides which of K1/R1–R3 pay ·
**Depends on** nothing (sealed now, 1.1.0 after the reseal)
* **Evidence:** the published range JSONs (`out/raw.tar.xz`) hold only frame, distance, decision
  and nearest per row; no run records tracker state. Recount of S_person_100 (260 visible frames): 83
  STOP; 78 frames with a gauge candidate without a reason but no STOP; 59 with no candidate; 14
  column; 25 elevated / floating / wall_face.
* **Cause:** `_corridor_cluster` (`resense/clustering.py`) returns None without saying which check
  dropped the blob (oversize, thin / min_points / weak, `_is_infrastructure` incl. the hardware rule);
  tracker holds leave no trace (`column_held`, the approach block, `explained_run` / ego veto, doubt,
  the `_qualifies` conditions in `resense/tracking.py`).
* **Tasks:** (1) `scripts/range_attrib.py`, an observation-only wrapper of `range_test.main()` like
  `debug_blobs.py`: per frame, the first failing check of each blob overlapping the object (else its
  zone and reason), the low and straddle clusters, and the matched track's state (id, hits,
  hit_fraction, confidence, zone_hist, column_held, approach_block, far_evidence, clean_run, doubt,
  fresh_blocked). Round 3's hook scripts (`evidence/silent_misses_2026-10-14/scripts/`) are a start.
  (2) Run on `707ea9c` and on 1.1.0: A_cube03, A_lowbox_rail, A_cube05, C_cube05, D_cube05,
  S_person_100/150, S_cube05_100, B_person, the 5 cm cable E6; set O frames 300–340 (small_center)
  and 760–790 (thin_hanging) via `probe.py`. (3) Commit a cause → frames table per distance bin in
  `docs/evidence/range_attribution_<date>/`.
* **Done when:** with hooks on, the sealed run reproduces the judge's summaries exactly (A_cube05
  `--obj 0.5,0.5,0.5 --start 150 --d0 230 --end 340`: first STOP 135.06, held 83.37, 66 STOP frames;
  S_person_100 `--start 360 --d0 100 --end 620`: 82 STOP frames); every visible non-STOP frame gets
  exactly one cause, 0 "unknown".

#### X3 · Robustness battery as a standing acceptance check next to the gate
**Progress 16.10:** reusable CLI and **40/40-case v1.0.0 baseline** delivered, 29,765 frames;
requested judge figures reproduced exactly ([P4](evidence/p4_start_2026-10-15/README.md)).
This is baseline MEASURED, not selected-candidate PASS. New-seal baseline remains future work.
**Criteria** 8.4, 8.7 · **Owner** P4 lane (P1 runs it with an agent) · **Mode** A · **Size** S ·
**Points** 8.4 +0.25, 8.7 +0.25 · **Depends on** node-decoded caches of the bags and set O
(`cache_decoded.py`)
* **Evidence** (judge probes): squareT_platform false-STOP episodes base 3, pitch +2 4, pitch −2 7,
  roll +2 7, 5 Hz 9, 30 % dropout 14, dedup 3 (STOP frames 11 → 20); doubleT_obstacle STOP frames
  base 193, pitch +2 192, 5 Hz 95/101, 30 % dropout 154, 50 % 126, dedup 189 (5 episodes);
  roundT_squareT 0 under every variant. `scripts/robustness_check.py` covers only 5 Hz and a 3°
  re-mount on the gate cache.
* **Cause:** the gate has no perturbation rows and DETECTOR_FREEZE gates on nominal input only; no
  candidate was ever rejected for brittleness.
* **Tasks:** `scripts/robustness_battery.py` (or extend `robustness_check.py`): the judge's `probe.py`
  variants (pitch ±2, roll +2, 5 Hz, 30 % dropout seeds 1–3, dedup) on squareT_platform,
  doubleT_obstacle, roundT_squareT and set O with a JSON summary; record the 1.1.0 baseline; add a
  DETECTOR_FREEZE rule (no variant worse by more than 1 episode or 2 STOP frames on the obstacle);
  a slide table for 8.4 (via PT1). It is also G3's perturbation part.
* **Done when:** `python scripts/robustness_battery.py --out docs/evidence/robustness_<date>.json`
  reproduces the judge's v1.0 numbers within ±1 on `707ea9c` (squareT 3/4/7/7/9/14 episodes;
  doubleT_obstacle 193/192/95/154) in ≤ 30 min on 4 vCPU with `-j 2`.

#### G3 · Pre-registered held-out test battery: spec now, one run on the final seal
**Progress 16.10:** specification registered; **no held-out detector run/result**, no credit yet.
**Criteria** 8.7, 8.4 · **Owner** P4 lane (P1 runs it; a fresh-context agent that did no tuning;
P3 reviews the misses) · **Mode** A · **Size** M · **Points** 8.7 up to +1 ("no held-out data"),
8.4 +0.5; one honest held-out line for the pitch · **Depends on** spec: nothing; run: the final seal
* **Evidence:** judge: "All tuning used the development data; no held-out real set". Candidate gains
  are measured on the judge's ray-casts, which rounds 1–3 then tuned on (backgrounds A/B/C/S, 27
  probes, the dark-band what-if) — they are in-sample now. Set O was meant as a holdout but became
  development data.
* **Tasks:** before any 1.2.0 tuning, commit `docs/evidence/heldout_<date>/spec.json`: a fixed
  seed; 3–4 new ride windows not used as A/B/C/D/S (curvature, station, switch; train motion from
  `icp_odometry.py`); organizer-style objects (30 × 30 × 10 cm on the bed and on a rail, a 2 × 2 m box,
  a 5 cm hanging cable, a plank across the rails) and new shapes (lying person 1.8 × 0.5 × 0.3, a
  0.15 m pole 2.5 m tall at ±0.8 m, a trolley 1.5 × 1 × 1); random lateral within ±0.9 m, start at
  230 m, approach and crossing. On the frozen final seal a fresh agent runs `range_test.py` and
  `probe.py` once and reports first STOP, held-90 % distance per class and every miss. Nobody tunes
  on it; a later change relabels it as development data.
* **Done when:** `git log -- docs/evidence/heldout_<date>/spec.json` shows a commit older than
  `results.json`; `results.md` has ≥ 4 backgrounds × 6 objects with first-STOP and held distances
  and the misses; the run log shows `detector_freeze.py verify` PASS.

#### J1 · Re-judge the shipped seal with the judge's tools; one table against 13.10
**Criteria** evidence for 8.1–8.8 (8.2 confidence, 8.5 claims, 8.8 honest numbers) · **Owner** P4
(a fresh-context agent runs and scores; P1 reads `delta.md`; P2 turns the table into the deck chart) ·
**Mode** A · **Size** M · **Points** protects the 8.2 credit, ~+0.5 8.5, ~+0.5 8.8 · **Depends on**
E1; second run after the 1.2.0 reseal; X3; CPU (ride on the team VM)
* **Evidence:** the judge credited only what it reproduced. The same v1.0.0 detector differs between
  the team's cache gate and the node path: five empty bags 12 episodes / 39 frames (gate) vs 4 / 13
  (judge); set O big_edge_inside first STOP 18.3 vs 28.2 m, small_on_rail 42.7 vs 48.0 m; ride 30 vs
  32 episodes. The deck and README take their numbers from the int16 cache gate
  (`scripts/build_deck.py` `GATE_SOURCE`), not from the node path the jury runs.
* **Tasks:** copy `docs/evidence/judgement_2026-10-13/scripts/` to `docs/evidence/rejudge_<date>/scripts`
  (never write into the 13.10 folder); `judge_runner.py` on the 7 organizer bags and
  `stream_new_data.py` for the ride (team VM, ~14 GB peak disk); `score_objects.py`,
  `summarize_empty.py`; the range matrix and extra runs; X3's perturbation rows and S1's 4 Docker
  chain conditions on the release image; a fresh agent scores against the 13.10 rubric
  (`scores.json` schema) and writes `delta.md`; once on v1.1.0, once on the final seal ~21.10.
  After the defence: `--input raw --bags <dir>` in `regression_gate.py` reusing
  `judge_runner.NodeReplica`.
* **Done when:** a dry run on `707ea9c` reproduces `out/doubleT_obstacle.csv` (193 STOP from frame
  8) and `out/empty_summary.json` (4 episodes / 13 frames); for the release: 8 per-recording CSVs,
  31 range summaries, the perturbation table, 4 Docker summaries, `scores.json`, `delta.md`;
  `detector_freeze.py verify` PASS in the run log.

#### X2 · False-STOP ledger with pass-by ground truth and a fast window replay
**Criteria** 8.1, 8.4, 8.7 (enabler for F1, F2, K2) · **Owner** P4 lane (an agent; P2 snapshots;
a human confirms classes) · **Mode** H+A · **Size** M · **Points** ~+0.25 on 8.7; makes F2 and K2
reachable · **Depends on** nothing (run on 1.0 outputs now; re-run on the final seal)
* **Evidence:** 36 episodes / 173 STOP frames in 13,558 empty frames (~91/h). Ride 32 / 160:
  onsets 16 at ≥ 100 m, 10 at 40–100 m, 6 below 40 m (7 by minimum distance); squareT 3 (147.6 /
  82.9 / 139.9 m); roundT_pressureGate 1 (54.5 m). The ride's mount goes pending → identity in every
  record, so windows can run with calibration off. Every earlier attempt was judged by aggregate
  counts on full ride replays (~20 min CPU; [`EXPERIMENTS.md`](EXPERIMENTS.md) "what was tried").
* **Cause:** the ride has no labels, so the false-alarm mechanisms (axis misfit, height-reference
  error, phantom returns, real structure) were never separated.
* **Tasks:** `scripts/false_stop_ledger.py`: one row per episode (onset, distance, lateral, size,
  kind, reason, curvature, rail_lock, ego, mount, health) from judge or gate outputs; pass-by:
  integrate ego until the train is 10–25 m from the onset's world position, re-fit the track there and
  classify (side structure |dy| > 1.4, overhead h > 3.0, bed or rail fitting h < 0.15, nothing =
  phantom, in-envelope structure); window replay with 150 frames of pre-roll, calibration off, a
  fresh detector; P2 renders one BEV + side snapshot per episode; a human confirms the ambiguous
  classes (< 1 h).
* **Done when:** `python scripts/false_stop_ledger.py --runs <outputs> --windows <cache>` reproduces
  ≥ 34 of the 36 episodes in window replay (onset within 2 frames, distance within 2 m) at least 2×
  faster than full replays; every episode has a pass-by class; committed as
  `docs/evidence/false_stops_<date>/ledger.json`.

### Detector: range and false alarms (the 1.2.0 bundle and after)

#### K1 · Standing train: far axis jitter → STOP flicker at 100–150 m, perturbation-sensitive platform false STOPs
**Criteria** 8.2, 8.4, 8.1 · **Owner** P3 (agent-executed; P1 merges and reseals) · **Mode** A ·
**Size** M · **Points** 8.2 +0.5 to +1 (judge −1 "standing train"), 8.4 +0.5, 8.1 +0.25; gives C1
its σ(D) · **Depends on** 1.1.0; X1 first; X3 for the perturbation acceptance
* **Evidence** (judge's standing-train runs, squareT_platform frames 360–620): the placed object's
  lateral varies 0.095 m, while the live axis at X = 100 m has SD 0.30 m (offset median 0.58 m), at
  150 m SD 0.67 m, at 60 m SD 0.08 m; the empty-run axis at 100 m has SD 0.094 m, so the object
  roughly triples the jitter (likely by occluding far wall bins; unconfirmed). Person-size box STOP
  82/260 at 100 m, 90/259 at 150 m; 0.5 m cube 94/260 at 100 m, 0/243 at 150 m; at 60 m 255/260.
  Empty squareT: axis at 83 m SD 0.25–0.47 m, CAUTION 102–132 of 150 frames, the 3 base false STOPs
  at 147.6 / 82.9 / 139.9 m, 3 → 4–14 episodes under perturbations (X3).
* **Cause:** yaw and curvature are re-fitted from the walls every frame and smoothed per time, not
  per distance (`resense/track.py`: `kw` = periods, `a_w = walls_smoothing ** kw`, `walls_smoothing`
  0.6 per period): at standstill the EMA follows wall-fit noise with τ ≈ 0.2 s; the rate limit allows
  1e-4 1/m curvature per period (0.5 m at 100 m per frame); `detector.py` sets the speed estimate
  only after `_fit_track`; the strict edge at 100 m is 1.05 − 0.15 = 0.90 m, so the body straddles it.
  Secondary (X1 weighs them): `column_hold`, the far-evidence approach block (needs ≥ 2 m/s), track
  re-creation after `max_misses` 3.
* **Tasks:** (1) X1 on the standing runs: share of frames lost to the axis offset vs tracker holds.
  (2) Distance-based smoothing: weight = `walls_smoothing ** max(k_min, travelled / 1.5 m)` with the
  previous frame's speed (k_min ≈ 0.05; unknown speed keeps today's behaviour); hold the median of the
  fits during a stop (never one fit for more than 60 s); scale the rate limits per distance. (3) Only
  if X1 shows tracker holds dominate: `column_hold` ignores hits whose strict voxels are the track's
  own body; a stationarity test replaces `_approaching` at proven standstill (< 0.5 m/s for ≥ 2 s);
  keep a missed track 1 s while standing. (4) Re-run the standing runs, X3 and the gate.
* **Done when:** standing person-size box at 100 m ≥ 200/260 STOP, at 150 m ≥ 150/259; 0.5 m cube
  at 100 m ≥ 150/260; at 60 m still ≥ 255; `probe.py` on squareT_platform ≤ 1 false-STOP episode
  (now 3); X3 variants ≤ 3 episodes each on squareT, 0 on roundT_squareT; an object appearing at
  100 m on the standing background STOPs within 0.5 s; doubleT_obstacle 193; gate exit 0; safety
  review.

#### R1 · 0.3 m objects confirmed only from ~45 m
**Criteria** 8.2, 8.1 · **Owner** P3 (agent-executed; P1 gate and reseal) · **Mode** A · **Size** M
· **Points** realistically +0.5 (~+10 m for the 0.3 m class; the voxel ceiling caps it) ·
**Depends on** 1.1.0 (expect rebase conflicts in `clustering.py`); X1 before task (d); one
candidate together with R2
* **Evidence:** A_cube03 first STOP 44.86 m / held 49.32 m, 30–60 m 11/21, 60–100 m 0/27, visible
  from 228 m; the 0.3 × 0.3 × 0.15 box on the rail head is identical; B 41.2 m, C 41.6 m; set O
  small_on_rail first STOP 42.7 m / held 46.2 m (gate). The organizers' minimum object is
  30 × 30 × 10 cm.
* **Cause:** (1) the corridor "hardware" rule (`_is_infrastructure` in `resense/clustering.py`;
  `hardware_max_top` 0.35, `hardware_max_width` 0.4, `hardware_max_height` 0.3) drops every corridor
  cluster that small, with no lateral condition, after the weak test, so it also removes weak far
  evidence; `tests/test_modules.py` asserts that a 0.3 × 0.3 × 0.2 box on the axis at 20 m is dropped.
  (2) The low stage ends at `lowobj.range_max` 60 m and needs `low_confirm_hits` 5. (3) Straddling
  never joins the two parts: `straddle_min_width` 0.35 is wider than the cube. Ceiling: the clustering
  scale grows as (1 + d/40), so beyond ~50–60 m a 0.3 m face cannot pass a 5-voxel bar per frame.
* **Tasks:** pre-register each variant and measure it separately, cheap config variants first via
  `--set`: (a) `tracking.low_confirm_hits` 5 → 3 for low clusters that reach `min_top`; (b)
  `straddle_min_width` 0.35 → 0.25 only for clusters ≤ 0.6 m long; (c) `lowobj.range_max` 60 → 75 (the
  bed is observed to ~90 m); (d) after X1: the hardware rule only within 0.3 m of a rail line (|dy|
  0.5–1.1 m) or for clusters longer than 0.6 m. Rewrite the `test_modules.py` case to use a sample on
  the rail line; add a test that a 0.3 m cube on the axis at 40 m is a gauge cluster.
* **Done when:** A_cube03 (`--obj 0.3,0.3,0.3 --start 150 --d0 230 --end 340` on
  roundT_squareT_pressureGate_squareT) first STOP ≥ 55 m and held ≥ 52 m; the rail-head box held
  ≥ 50 m; B/C cube03 no worse; gate exit 0 with ride ≤ 27 events / 30 episodes, five bags ≤ 8/12, set O
  small_on_rail first STOP > 42.7 m, small_outside_near 0 false STOP; safety review.

#### R2 · Sparse far objects: the point bar leaves an 80–100 m hole
**Criteria** 8.2, 8.1 · **Owner** P3 (agent-executed) · **Mode** A · **Size** M · **Points**
realistically +0.5 to +1 (variants (a) and (b) take hours) · **Depends on** 1.1.0; X1 (separates the
hardware share); one candidate together with R1
* **Evidence:** A_cube05 first STOP 135.06 m but held only from 83.37 m (60–100 m 12/27, 100–150 m
  15/38); C_cube05 75.4 / 82.8 m; D_cube05 104.8 m, never held; standing 0.5 m cube at 150 m 0/243.
  Set O small_center (a 0.3 m cube floating at 1.6–2.0 m): `clear_distance` equals the object's
  distance in frames 319–336 (85.2 → 57.5 m) yet the decision stays GO until frame 337 (55.8 m) — a
  candidate, never confirmed. Set F box0.5 detected 2/6, at 64.4 m.
* **Cause:** `min_points` is 5 below `cluster.far_range` 100 m and `min_points_far` 3 beyond it, so a
  3–4-voxel object is a candidate at 100–150 m, lost at 60–100 m and back nearer; the weak path
  (`weak_min_points` 4) admits ≥ 4 voxels only from 60 m and only as evidence for an approaching
  track; beyond the height reference only clusters ≥ `far_min_height` 0.6 m count (a 0.5 m cube gets
  `beyond_height_ref`); accumulation is off in the node without a speed. Not the doubt model (set O
  with it off stays 411 → 411).
* **Tasks:** pre-registered config variants, each through the gate with `--set`, in order: (a)
  `cluster.weak_min_points` 4 → 3; (b) `cluster.far_range` 100 → 60; (c) a bar that never rises with
  range: `min_pts(d) = clip(round(k · sensor.expected_points(d, 0.5, 0.5)), 3, 5)` (`resense/sensor.py`;
  a small change where `min_points` is chosen); (d) `far_min_height` 0.6 → 0.45 only where
  `track.floor_verified`. Keep the first variant that passes; unit test that the bar never rises with
  range.
* **Done when:** A_cube05 held ≥ 120 m and the 80–100 m frames ≥ 12/14; C_cube05 and D_cube05 no
  worse; gate exit 0 with ride ≤ 27/30, five bags ≤ 8/12, set O small_center first STOP ≥ 65 m (now
  55.8), big_outside false STOP ≤ 6, set F box0.5 not worse than 2/6; safety review.

#### R3 · Thin cables: hanging 5 cm object STOP only from 30 m, standing 5 cm cable from 60 m
**Criteria** 8.1, 8.2 · **Owner** P3 (agent-executed) · **Mode** A · **Size** M · **Points** ~+0.5;
closes an explicit organizer requirement ("broken hanging cables must be detected") the jury may ask
about · **Depends on** X1; 1.1.0
* **Evidence:** set O thin_hanging visible from 199.7 m, first STOP 30.1 m, held 31.8 m (30–60 m
  1/13, 60–100 m 0/7); frames 785–788 GO while `clear_distance` follows the object (36.7 → 31.8 m),
  STOP from 789 with kind `hanging`. The judge's 5 cm standing cable (0.05 × 0.05 × 2.6 m, base 0.2 m):
  first STOP 59.8 m, held 43.4 m, 60–100 m 0/10, 13 returns at 100 m; at 60–130 m a gauge candidate
  without a reason in 13 GO frames, no candidate in 36.
* **Cause** (partly verified): the hanging stage stops at `hanging_max_distance` 60 m and needs the
  rail pair; for the standing cable a candidate exists at 60–130 m but no track confirms it —
  unattributed between hit fraction / confirm time, association of a 5 cm object, and the doubt model
  (`doubt_near` 25 m, `doubt_body_range` 40 m).
* **Tasks:** X1 on the cable run and set O frames 760–790; fix the dominant cause (e.g. exempt thin
  vertical gauge clusters ≥ 2 m tall inside the strict envelope from the doubt delay, relax
  association for tracks ≤ 0.1 m wide, or `hanging_max_distance` 60 → 80 if the ring spacing supports a
  0.3 m dip there); add a 5 cm cable probe to X3 / G3. Check the interaction with the experimental free-top
  column test (it exempts only clusters ≥ 0.25 m wide).
* **Done when:** the cable probe (`run_range_extra.sh` line E6) first STOP ≥ 80 m, held ≥ 60 m; set O
  thin_hanging first STOP ≥ 45 m; gate exit 0 with ride ≤ 27/30, five bags ≤ 8/12, set O background 0;
  safety review.

#### F1 · Near-field low-object false STOPs at the rail-head plane (5 of 6 ride episodes below 40 m)
**Criteria** 8.1, 8.4 · **Owner** P3 (agent-executed) · **Mode** A · **Size** M · **Points** 8.1
+0.5 to +1 (part of the −4; the judge stresses the emergency-brake range); risk ~−0.5 on 8.2 small
objects if the margin is too tight · **Depends on** 1.1.0; X2 windows optional
* **Evidence:** low-kind episodes on the ride: frame 2838 at 3.1 m (1.19 × 0.20 m), 4152 16.2 →
  13.6 m, 5714 36.3 → 32.0 m, 5901 28.8 m (rail lock 0.05, ego 2.1 m/s), 7362 39.4 → 31.7 m
  (centre); roundT_pressureGate frame 139 at 54.5 m. The judge's 7th "below 40 m" episode is frame
  2670 (onset 87.4 m, a 0.99 × 0.63 × 0.36 m cluster at lateral 1.02 reaching 26.6 m), not low-kind.
  `lowobj.min_top` 0.08 took the ride to 25 episodes / 22 events (EXPERIMENTS "lowobj.min_top 0,08";
  sealed 30/27) but loses the organizers' 10 cm box on a rail, whose ray-cast top is only 0.055–0.075 m
  above the plane.
* **Cause:** the low stage keeps a cluster whose top reaches `min_top` 0.0 (`min_point_top` 0.03)
  above the model's rail-head plane; beyond `rails_range` / `template_range` 30 m that plane is
  extrapolated, so centre-bed fixtures read 0.03–0.08 m above it; rail-side fittings are compared with
  their own rail's line only within `rail_start_within` 4 m and only when the line is ≥
  `rail_start_min_ref` 0.06 above the model (`resense/lowobj.py`, `mark_rail_line`); frame 5901: no
  low-object cap when the rail lock is lost (`gauge.no_rail_range` 40 m applies beyond 40 m).
* **Tasks:** (a) a local reference: the rail-head line from both rail bands at X ± 5 m (generalise
  `mark_rail_line`); require top ≥ local line + margin — first measure how far the ray-cast box rises
  above its own rail line, keep ≥ 1.5 cm headroom, then sweep the margin 0.02 / 0.03 / 0.04; (b) the
  same-rail-line test out to `lowobj.range_max` without the `rail_start_min_ref` condition (margin
  0.03–0.05); (c) without a rail pair (`track.rail_slabs == 0`) a low STOP only within 15 m, otherwise
  advisory.
* **Done when:** `judge_runner.py` on the 5 empty bags and the ride (or X2 windows): low-kind
  false-STOP episodes 6 → ≤ 1; the rail-head box first STOP ≥ 42 m (judge 44.9); set O small_on_rail
  via `judge_runner.py` first STOP 48.0 ± 3 m; the repo's 10/25/45/50 m low-box test green;
  doubleT_obstacle 193; gate exit 0; safety review.

#### F2 · Far-onset false STOPs at ≥ 100 m (half of all episodes), after the X2 audit
**Criteria** 8.1 (8.2 at risk) · **Owner** P3 · **Mode** A · **Size** L · **Points** 8.1 +0.5 to +1;
8.2 risk −0.5 to −1 if range is lost · **Depends on** X2; the final seal; after 23.10 unless O1 says
updates count
* **Evidence:** 18 of 36 episodes start at ≥ 100 m (16 on the ride, 83 of its 160 frames; 2 on
  squareT at 147.6 and 139.9 m): compact clusters of 3–19 voxels, 0.5–2 m tall, 13 of 18 central
  (|lat| ≤ 0.6); the ride's start-up episode (frames 10–36) at 138–145 m. Every earlier filter cost
  8.2 range (`far_min_height` 0.8–1.0, far axis both sides, fresh STOP evidence, `explained_run` with
  range reasons; EXPERIMENTS "what was tried").
* **Cause:** both references are extrapolated far out — height from the linearly extrapolated bed,
  lateral from one global quadratic trusted to the last wall bin + 15 m (+50 m when straight); a far
  cluster only has to meet `far_min_height` 0.6 / length ≤ 3 / bottom ≤ 1.0 and `confirm_hits` 3 with
  a 0.6 zone fraction. Which mechanism dominates is unknown: X2 decides.
* **Tasks:** classify the 18 with X2; branch on the dominant class (side structure: a far onset must
  stay in the gauge under the median of the last 5 axes; overhead: far height from the side-wall base,
  `verify_floor_extrapolation` in `track.py`; compact central: document as a residual,
  indistinguishable from 8.2 targets); screen every candidate with range_test A/C person and 1 m cube
  before the gate.
* **Done when:** ride far episodes 16 → ≤ 8; A person first STOP ≥ 210 m, A 1 m cube ≥ 145 m; set O
  big_center 98.2 m and big_above 111.4 m within 2 m; gate exit 0; safety review.

#### K2 · Curve and double-track axis — read the round-3 evidence first
**Criteria** 8.2, 8.4, 8.1 · **Owner** P3 (agents for the offline fit study and the gate; P1
reseals) · **Mode** A · **Size** L · **Points** 8.2 −3 (curves / double track) and 8.4 −2 (range
collapse): realistically +1 to +2 in total; 8.1 +0.25 to +0.5 (mid-range edge false STOPs) ·
**Depends on** round 3's curve-entry axis result (§2); 1.1.0; X1; X2 for the ride episodes; after
23.10 unless round 3 shipped the axis fix or O1 allows
* **Evidence:** C (roundT_pressureGate_roundT) after the session's cut: person 82.8 / 91.6 m, 1 m cube
  85.7 / 94.6, 0.5 m cube 75.4 / 82.8, person +0.7 m 68.1 / 75.4; GO remains at 118–150 m; the far
  axis lags 1.0–2.4 m at 100 m in frames 57–117. B (roundT_doubleT): person 51.8 / 57.1 m, 28/119
  STOP, 60–100 m 0/23 all CAUTION; `axis_valid` is 60 m in 31 of 36 frames 131–166. Ride mid-range
  edge episodes on curves: frames 6867 (47.8 m, 1.03 × 0.49 × 1.27 m), 7859 (47.6 m, 5.5 m long),
  7868 (41.4 m, 6.0 m long), 3753 (64 m). Capping `axis_valid` instead of only the monitored range
  cost the C person 55 → 43 STOP frames in round 3 and was not taken.
* **Cause** (round 3's investigation): the two walls are averaged by fit quality 1/(rms² + 1e-4), so
  the smooth inner wall carries 3–10× the weight but is hidden by the curve beyond 56–96 m; a
  quadratic held to the rails' tangent cannot follow a curvature that grows along a transition curve;
  the EMA lags only ~1.5 frames and the curvature rate limit never binds (≤ 9e-5 per frame). Double
  track: `axis_valid` is capped at `axis_disagree_range` 60 m when the wall curvatures differ by more
  than 6.7e-4, and everything beyond becomes `beyond_axis` (CAUTION).
* **Tasks:** (0) read round 3's final evidence; if its axis fix shipped, re-measure C, B and the ride
  and close or shrink this card. (1) Otherwise, offline on recorded wall observations: score the
  wall-vs-axis error per X bin for (i) the outer wall alone beyond the inner wall's reach, (ii) a
  piecewise or clothoid curvature term fitted where the walls agree, (iii) for double track, the side
  whose offset from the rail axis at 6–30 m is the single-track gap (~2.2–2.3 m). (2) Integrate the
  best behind flags (default off) with round 3's wall-drift test as the trust test. (3) Pre-register on
  B, C, D, the ride crossover frames 4720–4729 and the four ride episodes above.
* **Done when:** offline wall-vs-axis error at 80–120 m on C ≤ 0.5 m (now 1.0–2.4); C person
  (`--obj 0.5,0.5,1.75 --start 0 --d0 230` on roundT_pressureGate_roundT) first STOP ≥ 110 m, held
  ≥ 100 m; B person (`--start 50` on roundT_doubleT) ≥ 90 m and 60–100 m ≥ 80 %; A person still 218 /
  222 m; the ride's 4 edge episodes ≤ 1 and the crossover posts not STOP; gate exit 0 (ride ≤ 27/30);
  safety review.

#### S4 · Dual-return duplicates: the track model counts raw points
**Criteria** 8.4, 8.3 (8.1 CAUTION side effect) · **Owner** P3 (P1 for the decode; the captain and an
independent reviewer decide go / no-go) · **Mode** H+A · **Size** L · **Points** 8.4 up to +1 (dedup
is named in the judge's −2 sensitivity), 8.3 +0.5 if dedup at decode lands · **Depends on** 1.1.0;
X3; S2 for the decode part; coordinate with K1 (both move the axis); after 23.10 unless O1 allows
* **Evidence** (judge probes): squareT_platform with dedup CAUTION 446 → 99 frames, STOP 11 → 20
  (episodes 3 → 3), points p50 161,358 → 83,777; doubleT_obstacle STOP 193 → 189 split into 5
  episodes, CAUTION 0 → 3; roundT_squareT CAUTION 191 → 200. The organizers' control data is "Last and
  Strongest" dual return. [`SENSOR.md`](SENSOR.md) "копии не меняют ни одного решения" is refuted.
* **Cause:** clustering counts voxels and is immune, but the track model counts raw points per bin
  (`bin_percentile` min_points, `walls_min_points` 3, `floor_min_points`, `floor_verify_min_points`;
  health visibility k = 20), so `axis_valid`, the height reference and the `beyond_*` advisories
  follow the driver's return mode; `fastcloud.py` keeps every finite return of both echoes.
* **Tasks:** bisect with `probe.py --dedup` on squareT applying dedup only inside the track-model fits;
  if the change follows, count distinct returns per bin with thresholds re-derived from
  `sensor.expected_points` (not re-tuned); optionally an O(n) partner-slot dedup in S2's decode kernel
  behind `sensor.dedup_returns` (default off) with the same rule in the cache path; X3 matrix + full
  gate + safety review + reseal; the captain records go / no-go in DECISIONS.
* **Done when:** X3 battery: squareT false-STOP episodes ≤ base + 1 under dedup, 5 Hz, 30 % dropout
  and ±2° tilt; CAUTION with dedup within ±10 pp of base; doubleT_obstacle ≥ 190 STOP frames as one
  episode under dedup and 5 Hz; gate exit 0 without `--allow` on STOP / recall / first-STOP rows.

### Generalization and technical quality

#### G1 · Rule provenance: ablate every rule justified by a named recording
**Criteria** 8.4, 8.7 · **Owner** P3 (an agent runs the ablations on the team VM; P1 merges) ·
**Mode** A · **Size** M · **Points** 8.4 up to +1 (part of the −3), 8.7 up to +0.5 · **Depends on**
the final seal; CPU (~17 full gates); feeds T1 and the Q&A; after 23.10 unless O1 allows
* **Evidence:** `configs/default.yaml` has 333 leaf parameters (more after 1.1.0) and 30 lines cite a
  recording (`grep -cE 'doubleT_|roundT_|squareT_|set O|\bride\b|frame 111|new_data' configs/default.yaml`).
  Enabled examples: `floor_shadow_range` 30 (doubleT_platform), `wall_keep_gauge_voxels` 10 (set O #6),
  `floating_long_min_length` 3.0 (the ride), `column_hold`, `near_escalate_*`, `stop_keep_*`,
  `explained_run`, `ego_veto_min_speed`. Judge 8.4 −3, 8.7 −2.
* **Cause:** each rule was accepted when the gate improved on the recordings it was tuned on; none
  was checked against recordings it was not tuned on.
* **Tasks:** list the ~17 enabled recording-cited rules and their off values; one full gate per rule
  off on the final seal; a table (change on the source, on the other recordings, on set O/F, the
  safety effect); classify each as general, single-source patch, or harmful elsewhere; P3 decides;
  removals go through T1's reseal and the YAML comments point at the table.
* **Done when:** `docs/evidence/rule_ablation_<date>/` holds one
  `python scripts/regression_gate.py --cache <cache> --baseline <final baseline> --set <key>=<off> --out .../<key>.json`
  per rule plus `table.md` classifying every rule; after T1 the grep above gives ≤ 5.

#### G2 · Doubt model: cross-fit on the current detector, keep only if it earns its place
**Criteria** 8.4 · **Owner** P3 (agent) · **Mode** A · **Size** M · **Points** ~+0.5 (one of three
reasons for the −3) · **Depends on** the final seal; the ride cache (8 pieces); G3 positives optional;
feeds T1; after 23.10 unless O1 allows
* **Evidence:** `resense/models/track_opinion_report.json`: 205 negative rows (doubleT_platform,
  ride pieces 0–7, squareT_platform), 2,646 synthetic positives, held-out AUC 0.9745, `lat_std`
  importance 0.459, trained on the 27.09 detector (two rule generations old). The cross-fit on that
  detector gave ride events 43 off / 37 cross-fitted (EXPERIMENTS). Judge 8.4: "a learned model
  trained on the ride's own tracks".
* **Tasks:** four leave-two-pieces-out folds with `scripts/track_opinion.py collect/train --exclude
  new_data:K,...`; `python scripts/opinion_crossfit.py --fold 0,1:A.json:t --fold 2,3:B.json:t --fold
  4,5:C.json:t --fold 6,7:D.json:t --baseline-model off --out docs/evidence/opinion_crossfit_<date>/crossfit.json`;
  report off / shipped / cross-fitted ride events and episodes plus the delay on set O, set F and G3
  positives; keep the model (retrained) if the cross-fitted gain is ≥ ~3 events and no held-out
  positive is delayed, otherwise `doubt_extra_hits` 0 in T1; record the decision in DECISIONS.
* **Done when:** `crossfit.json` committed with three rows and the decision row in DECISIONS; if kept,
  the deck and README quote the cross-fitted rate labelled "вне выборки".

#### T1 · Next seal: remove dead switches, code-only parameters into the YAML, decision function into `resense/`
**Criteria** 8.5, 8.4 · **Owner** P3 (agent code; P1 YAML structure, reseal, `sync_params`) ·
**Mode** A · **Size** M · **Points** 8.5 +0.5 to +1 (part of the −2 complexity), 8.4 ~+0.25 ·
**Depends on** the final seal; C1; G1 and G2 outcomes; after 23.10 by default
* **Evidence:** 22 disabled experimental switches with about 52 YAML leaves (`lowobj.near_*` 11,
  `gauge.axis_union_*` 4, `cluster.retro_*` 4, …); `resense/farrails.py` (242 lines) serves only
  `rails_far_rings`; 4 `configs/experimental_*.yaml`; live code-only parameters in
  `resense/config.py` (`explained_window`, `ego_veto_*` incl. `min_distance` 25 m that the safety review
  relies on, `hold_misses`); `Track.history` grows on every hit but only its max is read. Judge 8.5 −2.
* **Cause:** experiments were merged switched off rather than removed; parameters added on 29.09 went
  into dataclass defaults only, despite "one parameter file" (CAPTAIN §7).
* **Tasks** (branch from the final seal): delete the disabled branches, their parameters, tests and
  the 4 experimental configs (keep the external-speed accumulation path as an opt-in); add the live
  code-only parameters to `default.yaml` and the ROS copy (`scripts/sync_params.sh`); move C1's
  decision policy into `resense/` and import it everywhere; replace `Track.history` with a running
  max; fold in G1 / G2. Steps 1–4 must leave every decision unchanged; then safety review and reseal.
* **Done when:** gate exit 0 with 0 changed frames for steps 1–4 (frame diff as in
  `evidence/silent_misses_2026-10-14/gate_frames_vs_sealed.txt`); `detector_freeze.py verify` passes;
  YAML leaves ≤ 295 and code-only fields 0;
  `grep -rnwE 'rails_far_rings|axis_union|weak_min_rings|shell_min_top|start_clean|zone_min_votes|local_support_enabled|fresh_stop_evidence' resense configs`
  finds nothing; `pytest -q` passes.

#### D1 · Fix ~28 stale or contradictory statements in 13 docs; SCORECARD and the ownership map current
**Criteria** 8.5 (claims), 8.8 (credibility) · **Owner** P2 (an agent edits; the docs are P1's lane, P1
approves the PR) · **Mode** A · **Size** S ·
**Points** ~+0.5 on 8.5; stops jurors catching stale claims in the Q&A · **Depends on** nothing for
the v1.0.0 facts; second pass after the 1.1.0 and final seals and J1
* **Evidence:** (1) CAPTAIN and EVALUATION command the gate baseline `…_competitor_rules.json`; the
  current one is `…_shell_off` (DETECTOR_FREEZE, `detector_freeze.py`). (2) v1.0.0 is on `5d6e9b5`,
  but CAPTAIN, PLAN, REQUIREMENTS_MAP, ARCHITECTURE, PRESENTATION, SCORECARD and README say there is no
  tag or name `70bc265`. (3) `evidence/judgement_2026-09-29/` holds only scripts, though CAPTAIN cites
  it. (4) Five different totals (SCORECARD 61 and 65, 69 / 66 / 67.5 elsewhere), 13.10 in none.
  (5) SENSOR "копии не меняют ни одного решения" is refuted. (6) Set O small cubes appear as 43/56,
  35–56, 48–56 and 30–56 m in different docs. (7) The person-transplant claim refers to an older
  detector. (8) CAPTAIN §8 still gives PRESENTATION, `build_deck.py` and the video to P2, though §1 and
  PLAN give the pitch to P1 since 29.09.
* **Tasks:** edit P1-lane docs only: fix (1)–(3), (5), (8) as facts; make 13.10 = 66/100 the SCORECARD
  headline with older totals in a dated history table and update the CAPTAIN §2 table from it; label
  (6) with its pipeline (gate cache vs node path; final values from J1) and (7) "older detector";
  leave decision-log rows alone; second pass after 1.1.0 and after the final seal with J1's numbers.
* **Done when:** `grep -rnE '0 tags|No tag or release exists|Пока релиза нет|пока нет тега|0 тегов, 0 релизов' README.md docs/*.md gitbook`
  matches only dated history rows; `competitor_rules.json` in no command of CAPTAIN / EVALUATION /
  VM_GUIDE; the SENSOR sentence is gone; the first 20 lines of SCORECARD name 13.10 66/100.

**Progress 16.10:** P2 pass 1 integrated; fact/source audit and
checks: [`evidence/p2_2026-10-15/`](evidence/p2_2026-10-15/README.md). Shared docs consolidated
for selected scope after P1/P2 conflicts; final numerical pass still follows released seals
and J1. Queue state: [`web/P2_STATUS.md`](../web/P2_STATUS.md).

#### D2 · Archive the 28.09 experiment layer: process notes, personal-path tests, orphan scripts
**Criteria** 8.5, 8.7 · **Owner** P2 (an agent; docs are P1's lane and tests / scripts P4's, so P1
approves) · **Mode** A · **Size** S · **Points** ~+0.5 on 8.5, ~+0.25 on 8.7 · **Depends on**
after the session's and D1's doc commits (conflicts in `docs/evidence/README.md`, CHANGELOG)
* **Evidence:** `docs/` has 37 top-level `.md` files, 20 of them dated process notes (12
  `*_2026-09-28*`, 8 `EXPERIMENT_*`). Personal paths: `git grep -nE 'D:/Datasets|C:/Users' -- tests
  scripts resense` (7 hits: `tests/test_evidence_coherence.py` used by 6 realdata tests,
  `tests/test_fresh_support_analysis.py`, `tests/test_far_structure.py` docstring,
  `scripts/analyze_local_body_support.py`, `scripts/analyze_residual_events.py`). Judge top-10 #10.
* **Tasks:** `git mv` the 20 notes to `docs/archive/2026-09-28/` with an index README (hypothesis,
  verdict, evidence link) and fix inbound links; tests read their paths from env vars and keep the
  realdata marker, or go together with unshipped experiments' scripts; orphan analysis scripts to
  `scripts/archive/`; one line in [`README.md`](README.md) (this index).
* **Done when:** `ls docs/*.md | wc -l` ~17; `git grep -nE 'D:/Datasets|C:/Users' -- tests scripts resense`
  finds nothing; the markdown link check prints 0; `pytest -q` passes with removed tests named in the PR.

### Pitch (23.10)

#### PT1 · Pitch content for the shipped seal: lighter deck, honest range by track shape, node-path numbers
**Criteria** 8.8 (8.4 / 8.7 credibility in the Q&A) · **Owner** P1 (P2: range chart, slide visuals,
video cards; an agent: text cuts, numbers, Q&A drafts) · **Mode** H+A · **Size** M · **Points** up to
+1 of 5 · **Depends on** O1 (format; whether 1.1.0+ may be shown); J1 (numbers); G3 (held-out line);
D1 (same claims)
* **Evidence:** `docs/presentation/ReSense_LCT2026.pptx`: 16 slides, 1,917 words, max 239; slides over
  80 words: 2 (159), 4 (168), 5 (163), 6 (99), 7 (108), 11 (239), 12 (131), 13 (198), 14 (81), 15 (139),
  16 (130). The headline "человек 151 м" comes from set F, while the judge measured 218 m straight but
  52 / 74 m on curves and 41–45 m for a 0.3 m cube; "81–82 мс p95 360°" was not reproduced (106–119 ms
  on 4 vCPU); the speech says "2,1 на километр" (cache gate) where the node-path ride rate is ~2.5/km.
  Judge 8.8 −1 for dense slides and favourable headlines.
* **Cause:** `scripts/build_deck.py` takes its numbers from the cache gate and fixed 28.09
  measurements; detail that belongs in the notes sits on the slides.
* **Tasks:** after the final seal update the gate block with `--check-gate` against the final baseline
  and switch the published numbers to J1's node-path table; re-render the overview-video cards
  (`scripts/make_overview_video.py`, checked by `web/demo` tests); cut every slide to ≤ 80 words with
  the detail in the notes; replace the single "151 м" with a first-STOP chart (straight / curve /
  double track / platform × person, 1 m, 0.3 m) from J1 (P2 renders it); name the hardware for 81–82
  ms and add the 4-vCPU node figure (or S5's); speech with node-path numbers, one held-out line (G3)
  and, if O1 allows, one sentence on the independent check; Q&A on poles, curves, false alarms per hour
  (~91/h, ~2.5/km), the default `ros2 bag play`, hanging cables, who did what; drop the stale "пока нет
  тега" and the transplant claim. The captain orders the edits in P2's lane or gets P2's OK.
* **Done when:** `python scripts/build_deck.py --check-gate <final baseline json>` prints no differing
  row; `pytest -q web/demo` passes; slide text total ≤ 1,100 words and max ≤ 90 per slide; the range
  slide shows ≥ 3 track geometries; P1 signs off the PDF in `web/P2_STATUS.md`.

**Progress 15.10:** P2 task 2 (slide cuts) delivered: named PPTX/PDF, detail in notes and enforced
≤80 words per slide / ≤1,100 total. This is preparation, not closure of PT1: the range-by-geometry
chart and final numbers still require J1/O1; P1's PDF sign-off is pending (same evidence as D1).

#### PT2 · Live demo on the shipped image and two timed rehearsals with a fallback
**Criteria** 8.8 · **Owner** P1 (P2: second device with RViz / Foxglove, fallback clip; P3 + P4 as
mock jury) · **Mode** H · **Size** M · **Points** a failed demo or an overrun can cost 1–2 of 5 ·
**Depends on** PT1; O1 (format, live demo); E1 (release image); if v1.2.0 slips, rehearse on v1.1.0
and swap the day before
* **Evidence:** PRESENTATION "Две репетиции — не проводились"; `web/P2_STATUS.md` "Rehearsals |
  none held yet"; the fallback clip `docs/video/docker_chain_rviz.mp4` is the 23.09 archive; the demo
  needs `--read-ahead-queue-size 10` until S1 ships; node start to "listening" 3.1–4.2 s, first STOP
  1.0 s after the first result.
* **Tasks:** load the release archive on the captain's laptop and pre-cache doubleT_obstacle;
  optionally P2 re-records the 69 s fallback clip on the shipped image (`scripts/play_bag.sh` +
  RViz); rehearsal 1 by 19.10 (full run with a stopwatch, overrun per slide, RViz screen share);
  rehearsal 2 by 22.10 on the final image (full run, a forced switch to the fallback in ≤ 30 s, a
  10-question Q&A drill answered only with J1 / PRESENTATION numbers); log both in `P2_STATUS.md`
  (date, commit, image ID, time, demo result).
* **Done when:** two dated entries in `web/P2_STATUS.md` "Rehearsals": total ≤ 5:00 (or O1's length),
  STOP at ~56 m within 30 s of `ros2 bag play`, fallback switch ≤ 30 s in rehearsal 2; the checklist
  in PRESENTATION is fully ticked.

## 7. Inputs of 16.10: the competitor survey and the experts' message

Two documents were added on 16.10; neither changes a card above, they attach evidence and add work.

* **[`COMPETITOR_SURVEY_2026-10.md`](COMPETITOR_SURVEY_2026-10.md)** (34 other teams' repositories, read-only): the
  filtered shortlist, to test offline before any detector change (the seal rules in §1 apply). Where each idea goes:

| survey idea | card | what to do with it |
|---|---|---|
| 1 context tests on the compact far target (opacity, front-lift, attachment, depth edge) | F2, F1 | compute per episode on the X2 ledger first; CAUTION or delayed start only |
| 2 per-return structure peeling before the shape tests | H2, F2 | hypothesis for the judge's silent GO on curves (the merge with an edge blob), next to the evidence bar of H2 |
| 3 graded trust beyond the axis range instead of the hard `beyond_axis` cut | K2, K1 | the range lever; re-fit on anchored placements; largest false-alarm risk, so last |
| 4 inner-wall sight-line model on curves | K2 task (1) | matches K2's cause ("the inner wall is hidden by the curve beyond 56–96 m"); about 100 lines |
| 5 along-track continuation, collinear clusters, persistent low lines | F1, F2 | per-return evidence for CAUTION or `explained_run`; keep the collision-volume exception |
| 6 pooled carried-along test for short tracks | F2 | extension of `ego_veto`; replay on the ride's residual events |
| 7 switch / turnout branch hypotheses | X2, F2 | classify the ride and switch episodes first: how many are turnouts |
| 8 frame-context features for the doubt model | G2 | only after 1 works |
| evaluation items (label-free axis error, rays-hit next to detected, mirror replay, ambiguous-trial marking, leave-one-recording-out, false-alarm-per-hour bound) | X1, X2, X3, G3, K2 | see the survey's section 4 |

* **[`FINALS_BRIEF_2026-10-16.md`](FINALS_BRIEF_2026-10-16.md)** (the experts' criteria, new data, launch requests):
  the experts name the gauge's range and stability as criteria of their own, and ask for dust, a second lidar and
  an interactive launch. New cards, same format: **N1** the gauge as a stable, honest box in RViz (P2 with P1, no
  seal), **N2** second lidar: axis directions, channels, fields (P3 + P4), **N3** dust / suspension (P4 + P3),
  **N4** interactive launch: pause, slow, switch bags, graphics (P1, no seal). Suggested order: N4 and N1, then N2's
  battery, then N3 when the organizers' dust sample arrives.
* **[`evidence/axis_profile_2026-10-16/`](evidence/axis_profile_2026-10-16/README.md)** with
  `scripts/axis_error_profile.py`: the axis error, per-frame jitter and point counts by range from the organizers'
  synthetic objects (label-only, reproducible). Input for K1 / K2 and for N1's acceptance numbers.


## 8. Update of 17.10: release state, the extended dataset and the second lidar

Proposed by P4 on 17.10 from the material below; P1 owns this file and the schedule. No card above changes owner.

### 8a. What changed since §2

| item | state on 17.10 | evidence |
|---|---|---|
| `main` | Live remote checked at `3b7d7aa7cbbf238c21f84330497697da131b7cb9`; PR #35 (P2) and #36 (P4/new data) merged; sealed 1.1.0 source verifies | [execution record](evidence/n5_c2_execution_2026-10-17/README.md) |
| branch archive | Frozen seed `e39a011` is now reachable from `main`; the missing-history prerequisite is resolved. This check does not establish that every archive restore test has been repeated | [branch archive](evidence/integration_2026-10-16/branch_archive/README.md) |
| E1 | **no `v1.1.0` release yet**; latest CI job did not start because of billing/spending limits. Captain handles quota/billing; release is deferred until CI is fixed | [job annotation](https://github.com/pmixay/ReSense/actions/runs/39072282773/job/117512188031) |
| X3, X1, J1 prep | done on 1.1.0 (§3 rows); P4 work is merged through PR #36 | [P4 report](evidence/p4_eval_1.1.0_2026-10-16/README.md) |
| for P2 | case register / numeric export (proposed format, P2 to confirm), confirmed limitations and caption corrections | [export](evidence/p4_eval_1.1.0_2026-10-16/export/FORMAT.md), [limitations](evidence/p4_eval_1.1.0_2026-10-16/LIMITATIONS.md) |

### 8b. The extended dataset of 16.10 (measured)

Organizers' files: [intake note](organizers/extended_dataset_2026-10-16.md); analysis:
[extended data](evidence/extended_data_2026-10-17/README.md) and [Falcon Prime](sensor/falcon_prime/README.md).
The sealed 1.1.0 was run on it **for observation only**; if anyone tunes on it, it is development data (not G3).

* **`new_synth_data`**: three Pandar128 bags (platform 386, switch 736, tunnels 545 frames), same topic / fields /
  axes as the six originals. Objects are inserted **in place** (no appended block), so Set O's
  `label_fake_objects.py` does not label them. Intensity 1 alone is not ground truth. Team annotation and
  explicit uncertainty now replace the missing-label blocker (N5 below). Platform: a box at the rail (STOP from 87 m), a box
  outside (CAUTION), a **person-shaped object STOP only from 44 m** although visible from 201 m (CAUTION from ~166 m;
  `monitored_range` capped at 45 m at the platform). Switch / tunnels: ≥ 5 and ≥ 3 objects; false STOP on background
  8 frames (switch) and 3 + 1 frames (tunnels). **No dust or suspension in this delivery.**
* **`falcon_test`** (second lidar, real, standing train in a dark tunnel, 444 s): topic `/iv_points`, `frame_id`
  `seyond`, **ROS axes** (x forward, y left, z up), no `ring`, single return, ~95 k points per frame, header stamp =
  sensor uptime. The default launch works: 1 `FAULT` frame, orientation adopted at frame 1, mount 1.77 m / −2.4°.
  **But CAUTION on 65–99 % of frames** (two static gauge-edge warnings at 105.6 / 115 m) and short false STOPs at
  115 m; a walking person (97–127 m) gets STOP from 123 m. Only 187 of 444 s were read (disk); the rest is unseen.

### 8c. Cards: N2 and N3 revised, N5 and N6 new (format of §6)

#### N2 · Second lidar (revised 17.10: measured, launch works; the jury-visible problem is CAUTION)
**Owner** P1 (launch, docs) + P4 (measurement) + P3 (detector, only after measurement) · **Size** M
* **Tasks:** (1) P1: the Falcon line in the jury README / gitbook (`/iv_points`, `freshness_mode:=replay`, explicit
  `sensor_forward:=+x sensor_left:=+y sensor_up:=+z` or the default with auto-calibration), and the two-bag switch
  Pandar → Falcon in one node (N4); (2) P4: read the unseen 257 s of `falcon_test` in streamed windows; the orientation
  battery incl. the manual's native x-up frame (which the 8-candidate search cannot find); a Falcon proxy from our
  Pandar data (±60°, single return, Falcon grid) through the full gate; (3) P3, measurement first: what the two static
  warnings at 105.6 / 115 m are (real edge structure, or the 0.77 m lateral mount offset / 1.77 m height / −2.4° pitch);
  ring-free and single-return effects. Sealed changes only from those measurements.
* **Done when:** the README shows the Falcon command; the whole recording is characterised; the CAUTION and false-STOP
  cause on the Falcon is attributed (X1-style); a decision on a fix or an honest limitation for the pitch.

#### N3 · Dust / suspension (revised 17.10: the organizers' data contains none)
**Owner** P4 + P3 · **Size** M · **Depends on** O1-style question to the organizers
* **Tasks:** (1) P1 asks whether dust data is still to come; (2) P4 builds the generator and measures as in
  [FINALS_BRIEF](FINALS_BRIEF_2026-10-16.md) N3, so the answer exists if the hidden set has dust.

#### N5 · Labels and scoring for the new synthetic bags
**Owner** P4 · **Size** S–M · **Depends on** nothing
**Progress 17.10: DONE for team annotation and bounded development scoring.** All 1,667 frames,
12 tracks and 1,684 supported object/frame rows are recorded. Independent review found an
additional tunnel box and corrected a near-pass tracker attachment before freezing labels.
The two archived detector versions score identically. Uncertain gauge placement and unsupported
intervals remain explicit; this completion does not imply exact organizer truth or fixed detector misses.
* **Captain direction 17.10:** annotate the data ourselves; missing organizer labels do not block N5.
  Intensity 1 is only a candidate feature. Use exact Set O differences for platform frames 0–314,
  reviewed raw geometry and temporal continuity elsewhere, and explicitly retain sparse support,
  boundary/unknown gauge membership and incomplete negative knowledge.
* **Deliverable:** all **1,667 frame keys**, reviewed object records, first matched STOP / held distance
  per object, and per-bag false-STOP bounds on 1.1.0 and the recorded control. The scoring code
  rejects missing frames and incompatible coordinates; unknown labels are not negatives. Feeds
  criteria 1 and 4–5. This remains **development** data, not G3 or a release score.
  See [team labels and independent scoring](evidence/n5_labels_2026-10-17/README.md).

#### N6 · Late STOP on the synthetic person at the platform (criterion 1)
**Owner** P3 · **Size** M · **Depends on** N5, X1-style attribution
* **Evidence:** visible from 201 m, CAUTION from ~166 m, STOP only at 44 m, `monitored_range` capped at 45 m at the
  platform (the honest-range cap of 1.1.0). **Tasks:** attribute the frames (X1 harness) before any change; then K1 / K2.

### 8d. Order up to 23.10 (replaces §4 from 17.10)

* **17.10 captain update:** history preservation and P2/P4 merges are complete. The captain handles GitHub
  billing/quota; release (E1) waits for repaired CI. N5 proceeds by team annotation with explicit uncertainty,
  without waiting for organizer ground truth. C2 implementation and acceptance evidence proceed on the remote
  work branch. Dust and Falcon questions remain separate N2/N3 work; no organizer contact was made by this task.
  P4: N5 scoring; Falcon remaining windows.
  P2: confirm the export format; N1 gauge display can start (no seal).
* **18.10:** P4: J1 on the release (~3–4 h after E1; runbook ready). P1: N4 + the Falcon launch line (N2 task 1).
  P3: X1-style attribution of the Falcon warnings (N2 task 3) and the platform person (N6), then the 1.2.0 bundle
  as in §4 (R2 / R1 → K1 → F1 …) with the new bags as **development** checks.
* **19–20.10:** as §4: bundle items measured one by one; noon 20.10 cut-off; P4 independent safety review of
  `det/1.2.0`, including the new synthetic bags and the Falcon recording in its checks.
* **21.10:** P4: J1 run 2 on the final seal; G3 by a fresh agent (unchanged; the new data is not G3). P2: deck numbers
  from J1 and N5 (marked development data).
* **22.10:** rehearsal 2 (Falcon bag included in the demo only if N2's CAUTION issue is understood).
