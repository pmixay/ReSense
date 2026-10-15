# Backlog: remaining criteria work

> **Purpose:** what is left to gain on the eight criteria of ТЗ §8 after the independent judgement of
> 13.10 (66/100): one card per work item with its evidence, cause, tasks, acceptance check, owner
> role, mode and size; the order up to the defence on 23.10 and the load per role. What the agent
> session of 13–15.10 finishes itself is listed separately (§2) and is not in the cards.
> **Audience:** P1 (to distribute the work), team · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-10-15: every cause and line reference against the sealed `707ea9c`
> (v1.0.0 detector) by four read-only researchers and one critic; numbers recounted from the judge's
> per-frame outputs (`docs/evidence/judgement_2026-10-13/out/`, `raw.tar.xz`). Line numbers in
> `resense/` shift after the 1.1.0 reseal (§2): search for the named function.
> **Status:** current; §2a hands the session's unfinished work over (15.10)

## 1. How to use it

* **Roles** (the repo names roles, not people; [`PLAN.md`](PLAN.md) §roles, ownership map
  [`CAPTAIN.md`](CAPTAIN.md) §8): **P1** captain (ROS node, Docker, CI except pytest, release,
  docs, the detector seal, the pitch since 29.09) · **P2** frontend / visualization (`web/`, RViz,
  deck visuals, video) · **P3** CV engineer (`resense/` detector modules, `native/`, config values)
  · **P4** data / evaluation (datasets, metrics, eval scripts, regression gate, labels, tests;
  standing duties dropped 25.09, so P4-lane items run as agents under P1). Assign a person to each
  role before handing out cards.
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

## 2. Done in this session (not in the cards)

| what | judge problem | state on 15.10 |
|---|---|---|
| Column free-top test: a tall narrow object whose top is seen free is no longer demoted as `column` (pole 0.3 × 0.3 × 2.8 m on the axis 82 → 157 STOP frames, 0.7 m off the axis 0 → 128); a single "free" frame cannot release a real column's hold (`tracking.column_free_min_spares` 2) | #1 critical | integrated on branch `final/silent-misses`, gate PASS frame-identical to the seal |
| Structure-surface cut of oversize clusters on curves (person-size box on C first STOP 73.9 → 82.8 m; wall equipment 1.0–1.1 m proud of the wall stays quiet at `structure_cut_tol` 1.3 m) | #2 high | same branch; the GO band at 118–150 m on C is axis lag → card K2 |
| Round 3: honest monitored range where a wall crosses the corridor at curve entry (`track.axis_wall_drift`: `clear_distance` capped; C probes "GO with range past the object" 26 → 10) | #2, part of #4 | branch `r3/axis`, gated (every decision unchanged), **not reviewed, not integrated** |
| Round 3: curve-entry axis fix (walls weighted by how far each is seen) | #4 | branch `r3/axis-B-trial`: C axis error at 100 m 1.39 → 0.42–0.56 m, but three versions **failed the gate** (ride +6 / +9 / +7 events) → card K2 starts here |
| Round 3: free-top test robust to a non-returning band above the top, ring-table check, per-frame azimuth cache, objects taller than the 3.0 m cut | #1 hardening | branch `r3/column`, **WIP commit, not gated**: dark-band what-if on ride piece 1 sealed 14 / 1.1.0 candidate 30 / WIP 23 STOP frames |
| Round 3: physical evidence bar for structure-cut parts | #2 hardening | not started |
| Version 1.1.0 inside the reseal, new seal | — | **handed over 15.10, not done** (§2a) |

### 2a. Handoff of the session's unfinished work (15.10)

The session stopped on the captain's request; the rest goes to the team's agents, in this order.
All branches are on `origin`. The session's test harness (wall-anchored probes, the
dropout / pitch / dark-band batteries, axis hooks, wall observations on C) is in
`docs/evidence/silent_misses_2026-10-14/harness/` on `final/silent-misses` (README there).

| step | branch | what to do | done when |
|---|---|---|---|
| H1 | `r3/column` (WIP `42108ac`, on top of `final/silent-misses` `a188a2d`) | finish the measurements (S/B batteries, the dark-band what-if on ride pieces 1 and 3, pole / post probes), write the evidence README, full gate; ship only if the dark band improves at no cost; otherwise drop the branch | gate exit 0 on the committed code; pole on the axis still 157 STOP frames (A); battery identical to sealed |
| H2 | new from `final/silent-misses` | structure-cut evidence bar: a cut part must span ≥ 2 azimuth columns / enough rings (or a cut-part-only track needs more hits); keep the C gains (person first STOP 82.8 m, 55 STOP frames) | the wall-anchored battery gives no STOP the seal does not (mast 1.2 m proud is now 0 → 2); C under 30 % dropout and 5 Hz has no gauge cut part at or above the bar; gate exit 0 |
| H3 | `final/silent-misses` | integrate `r3/axis` (`a9347a8`, `972edd2`) and H1 / H2 if they passed; full gate on the committed code; diff every gate frame against the seal | gate exit 0, frame diff explained |
| H4 | `final/silent-misses` | **independent** safety review (DETECTOR_FREEZE step 3) and correctness review of `707ea9c..HEAD`: the 14.10 review fixes (`14f83dd`) and `r3/axis` were never reviewed independently | no confirmed medium-or-worse finding left |
| H5 | `final/silent-misses` | bump 1.0.0 → 1.1.0 in `pyproject.toml`, `resense/__init__.py`, `ros2_ws/src/resense_ros/package.xml`, `ros2_ws/src/resense_ros/setup.py` **before** the final gate (they are sealed files); final gate; `python scripts/detector_freeze.py create --manifest docs/evidence/detector_freeze_<date>.json --baseline docs/evidence/results/regression_baseline_2026-09-29_shell_off.json --evidence <committed gate JSON>`; `DEFAULT_MANIFEST` in `scripts/detector_freeze.py`; DETECTOR_FREEZE "Что опечатано", CHANGELOG release section, README "пакет 1.1.0" | `detector_freeze.py verify` PASS; `pytest -q`; `python scripts/release_meta.py version` prints 1.1.0 |
| H6 | → `main` | merge, then card E1 (tag `v1.1.0` by a human, release verification); update §2 of this file with the final numbers and shrink K2 if the axis changed | release workflow green |

## 3. Starting point and summary

Judgement of 13.10 on v1.0.0: 8.1 **15**/25 · 8.2 **9**/15 · 8.3 **7**/10 · 8.4 **8**/15 · 8.5 **7**/10 ·
8.6 **8**/10 · 8.7 **8**/10 · 8.8 **4**/5 = **66**/100. Points still lost: 8.1 −10, 8.4 −7, 8.2 −6,
8.3 −3, 8.5 −3, 8.6 −2, 8.7 −2, 8.8 −1.

**Before you start:** the upload closed 29.09 and the expertise of 30.09–14.10 ran on v1.0.0.
Whether anything after v1.0.0 can still count is the organizers' answer (card O1, today). The
"when" column assumes it can; if not, see §4 "if O1 says v1.0.0 only".

| id | item | criteria | owner | mode | size | points | when |
|---|---|---|---|---|---|---|---|
| O1 | Ask the organizers: pitch format, whether v1.1.x may be shown or re-run, results before 23.10 | 8.8 (gates 8.1–8.6) | P1 | H | S | decides ~3–6 | 15.10 |
| E1 | Ship 1.1.0: PR to `main`, tag `v1.1.0`, verify the release, fix the jury block; repeat as v1.2.0 | 8.6 (enabler) | P1 | H+A | S | +0.25 | 16–17.10, 20.10 |
| S1 | Freshness-first start-up catch-up and a memory bound: the literal `ros2 bag play <bag>` gives current results | 8.3, 8.6 | P1 | A | M | ~+2 | 15–17.10 |
| E2 | Offline rebuild from the release archive; non-root player without `-e HOME` | 8.6 | P1 | A | S | +0.5 | 15–17.10 |
| C1 | CAUTION policy: one shared decision function, CAUTION only where it carries information | 8.1 | P1 | H+A | M | +1 | 15–18.10 |
| C2 | `clear_distance` consistent with the advisory output; publish the overclaim scorer | 8.1 | P3 | H+A | S | +0.5 | 17–19.10 |
| X1 | Range attribution harness: which rule or tracker hold costs each late frame | 8.2 (enabler) | P4 lane | A | S | enabler | 16–17.10 |
| X3 | Robustness battery as a standing acceptance check next to the gate | 8.4, 8.7 | P4 lane | A | S | +0.5 | 15–17.10 |
| G3 | Pre-registered held-out test battery: spec now, one run on the final seal | 8.7, 8.4 | P4 lane | A | M | up to +1.5 | spec 15.10, run 21.10 |
| J1 | Re-judge the shipped seal with the judge's tools; one table against 13.10 | evidence for all | P1 | A | M | protects 8.2, +0.5 8.5, +0.5 8.8 | 16.10, 21.10 |
| K1 | Standing train: far axis jitter → STOP flicker at 100–150 m and perturbation-sensitive platform false STOPs | 8.2, 8.4, 8.1 | P3 | A | M | +1 to +1.75 | 17–19.10 |
| R1 | 0.3 m objects confirmed only from ~45 m (hardware rule, low stage ends at 60 m) | 8.2, 8.1 | P3 | A | M | ~+0.5 | 17–19.10 |
| R2 | Sparse far objects: the point bar leaves an 80–100 m hole (0.5 m cube, set O small_center) | 8.2, 8.1 | P3 | A | M | +0.5 to +1 | 17–19.10 |
| R3 | Thin cables: hanging 5 cm object STOP only from 30 m, standing 5 cm cable from 60 m | 8.1, 8.2 | P3 | A | M | ~+0.5 | 18–19.10 |
| F1 | Near-field low-object false STOPs at the rail-head plane (5 of 6 ride episodes below 40 m) | 8.1, 8.4 | P3 | A | M | +0.5 to +1 | 17–19.10 |
| S2 | 360° per-frame cost: native single-pass decode, per-stage profile | 8.3 | P3 + P1 | A | M | +0.5 to +1 | 17–19.10 |
| S3 | Cap the orientation-search cost while the configured mount has not passed | 8.3, 8.4 | P3 | A | S | protects ~1 | 17–18.10 |
| S5 | 8-core stand-in bench of the final node incl. the literal player | 8.3 | P1 | H | S | ~+0.5 | 21.10 |
| D1 | Fix ~28 stale or contradictory statements in 13 docs; SCORECARD and ownership map current | 8.5, 8.8 | P1 | A | S | ~+0.5 | 15.10, 21.10 |
| PT1 | Pitch content for the shipped seal: lighter deck, honest range by track shape, node-path numbers | 8.8 | P1 | H+A | M | up to +1 | 18–21.10 |
| PT2 | Live demo on the shipped image and two timed rehearsals with a fallback | 8.8 | P1 | H | M | protects 1–2 | 19.10, 22.10 |
| X2 | False-STOP ledger with pass-by ground truth and a fast window replay | 8.1, 8.7 (enabler) | P4 lane | H+A | M | +0.25 | after 23.10 |
| F2 | Far-onset false STOPs at ≥ 100 m (half of all episodes), after the X2 audit | 8.1 | P3 | A | L | +0.5 to +1 | after 23.10 |
| K2 | Curve and double-track axis (curve-entry lag, 60 m cap when walls disagree) — read the round-3 evidence first | 8.2, 8.4, 8.1 | P3 | A | L | +1 to +2.5 | after 23.10 unless round 3 (B) shipped |
| S4 | Dual-return duplicates: the track model counts raw points, so decisions follow the driver's return mode | 8.4, 8.3 | P3 | H+A | L | up to +1.5 | after 23.10 |
| G1 | Rule provenance: ablate every rule justified by a named recording | 8.4, 8.7 | P3 | A | M | up to +1.5 | after 23.10 |
| G2 | Doubt model: cross-fit on the current detector, keep only if it earns its place | 8.4 | P3 | A | M | ~+0.5 | after 23.10 |
| T1 | Next seal: remove dead switches, code-only parameters into the YAML, decision function into `resense/` | 8.5, 8.4 | P3 | A | M | +0.75 to +1.25 | after 23.10 |
| D2 | Archive the 28.09 experiment layer: 20 process notes, personal-path tests, orphan scripts | 8.5, 8.7 | P1 | A | S | ~+0.75 | after D1 |

## 4. Order up to the defence (23.10)

The bottleneck is CPU for ride replays and full gates: run them on the team VM. Detector items go
into **one bundle** (`det/1.2.0` from the 1.1.0 seal) with one combined gate, one safety review
and one reseal; items that miss the cut-off do not ship.

* **15.10 (D0):** O1 first (its answer is the branch point). Agents start what needs no seal and
  little CPU: S1, E2, C1 (rescore on saved outputs + the policy module), D1 pass 1, the G3 spec
  (must be committed before any new tuning, or it is not held-out), X3.
* **16–17.10:** once the session's 1.1.0 lands: E1 (PR, CI green, tag `v1.1.0`, release verified);
  J1 run 1 on v1.1.0 (its range table feeds the deck early); X1 on 1.1.0 and on `707ea9c`. Open
  `det/1.2.0`, cheapest first: R2 and R1 config variants through `--set` (hours) → F1 → S3 → K1
  (after X1) → R3 (after X1) → C2 (after C1) → S2.
* **18–19.10:** measure each bundle item on its own; only passing items join `det/1.2.0`. P1
  restructures the deck (PT1); rehearsal 1 (PT2) on v1.1.0 by 19.10.
* **20.10, noon cut-off:** combined gate on `det/1.2.0`, independent safety review, reseal with the
  version bump, tag `v1.2.0`, release. S1, C1 and E2 ship in the same tag (a tag needs a version
  bump in sealed files anyway).
* **21.10:** J1 run 2 on the final seal, G3 run once by a fresh agent, D1 pass 2, final numbers in
  the deck and video cards, S5 if an 8-core machine is available.
* **22.10:** rehearsal 2 on the final image with the fallback and Q&A drills.
* **After 23.10** (or earlier only if O1 says updates count and CPU allows): K2 unless round 3 (B)
  shipped, X2 then F2, S4, G1 and G2 then T1, D2, J1's raw-path gate mode.
* **If O1 says v1.0.0 only:** keep O1, E1, J1, D1, PT1, PT2 and S1/E2/C1 (they improve the live
  demo and the Q&A); shrink the detector bundle to the evidence the Q&A needs (K1, R1/R2
  measurements); everything else moves after the defence.

## 5. Load per role

| role | items before 23.10 | load | notes |
|---|---|---|---|
| **P1** | O1, E1 (twice), S1, E2, C1, J1 (twice), D1, PT1, PT2, S5; orchestrates the P4-lane agent items X1, X3, G3 | human ~4 of the 8 days: O1 0.5 h, two tags with verification ~3 h, the C1 semantics decision 1 h, two reseal sign-offs with the safety-review read ~3 h (CAPTAIN §3 item 8, the human read of the 29.09 review, is still open), J1 reading 2 h, deck and speech 1.5 days, rehearsals 1.5 days | overloaded: delegate S5 and the deck visuals; keep the tags, reseals and the pitch |
| **P2** | PT1 (range chart from J1, slide trims in `scripts/build_deck.py`, video cards via `scripts/make_overview_video.py`), PT2 (fallback clip, second demo device), C1 (`caution_reason` in RViz and the web view; `scripts/hero_view.py`), X2 snapshots (after 23.10) | ~2–3 days | D1 must fix the CAPTAIN §8 map so the deck / video lane matches the pitch owner |
| **P3** | the 1.2.0 bundle: K1, R1, R2, R3, F1, C2, S2, S3 (~8–10 agent-days; fits 16–20.10 with 3–4 agents in parallel if CPU allows; if short: K1 > R2/R1 variants > F1 > S3 > C2 > R3 > S2); after 23.10: K2, F2, S4, G1, G2, T1 | human: validate X1's attribution, read the safety reviews, classify G1's rules | since the freeze detector changes are agent-executed and captain-merged; confirm whether the P3 person is available, else an independent agent reviews and P1 decides |
| **P4** | X1, X3, G3 (spec now, run on the final seal), J1 runs; X2 after 23.10 | agents under P1 | the person, if available: confirm X2's ambiguous classes (< 1 h), review the G3 spec, mock jury in rehearsal 2 |

Rough gain if the pre-defence items land and count (judge's estimates): 8.1 +2 to +3, 8.2 +1 to +2,
8.3 +1.5 to +2.5, 8.4 +0.5 to +1, 8.5 +1, 8.6 +1 to +1.5, 8.7 +1, 8.8 +1.

## 6. Cards

### Organizers and release

#### O1 · Ask the organizers: pitch format, whether v1.1.x may be shown or re-run, results before 23.10
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
on 8.6 directly · **Depends on** the session's 1.1.0 reseal (§2); O1; S1 and E2 for the doc part
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
**Criteria** 8.3, 8.6 · **Owner** P1 (agent writes code, tests, Docker A/B; the captain approves
the policy reversal) · **Mode** A · **Size** M · **Points** ~+2 (8.3 +1 to +1.5, 8.6 +0.5 to +1)
· **Depends on** nothing to implement (the node is not sealed); reaches the jury with the next tag
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

#### S5 · 8-core stand-in bench of the final node incl. the literal player
**Criteria** 8.3 · **Owner** P1 (a teammate with an 8-core machine runs it; an agent writes the
summary) · **Mode** H · **Size** S · **Points** ~+0.5 through confidence · **Depends on** S1, S2,
the final image
* **Evidence:** the judge timed on 4 vCPU only (8.3 confidence "medium"); the stand is an
  i7-9700E with 8 cores; the team VM of 28.09 (4C/8T) gave 360° node mean 52.9 / p95 62.8 ms against
  the judge's 88/111 ms; `scripts/bench_8core.sh` (CAPTAIN §3 item 9) was never run.
* **Tasks:** on an idle machine with ≥ 8 physical cores run `scripts/bench_8core.sh` with the final
  image plus the 4 Docker chain conditions of S1; record `lscpu`, disk read speed (360° playback
  needs ~225 MB/s) and numpy in the image; commit `docs/evidence/bench_<date>/`; quote the numbers
  with the hardware named in README and ARCHITECTURE (via D1).
* **Done when:** `RESENSE_DATA=<bags> RESENSE_CACHE=<cache> scripts/bench_8core.sh` exits 0;
  `summary.json` has the 360° node p95 and the four chain summaries (target: README flags p95 ≤ 80
  ms, fresh ≥ 195/201); `facts.txt` shows `nproc` ≥ 8.

### Decision outputs

#### C1 · CAUTION policy: one shared decision function, CAUTION only where it carries information
**Criteria** 8.1 · **Owner** P1 (node lane; P2 for the display) · **Mode** H+A · **Size** M ·
**Points** +1 (judge −2: "CAUTION on 35–67 % of empty frames carries little information") ·
**Depends on** 1.1.0 (column semantics); K1 for the axis uncertainty σ(D) (start at 80 m); ships
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
  `resense/` later). (3) Policy v2: no CAUTION for `column` (after 1.1.0) or non-compact range
  demotions; margin advisories only within D_c (80 m to start); keep health warn and doubt. (4) A
  catch-up lag up to one input period counts as current. (5) `caution_reason` in the status JSON
  (`[contract]` in the PR title, CAPTAIN §6); P2 shows it in RViz and the web view.
* **Done when:** `python scripts/rescore_decisions.py --policy v2` on the 1.1.0 judge-runner
  outputs (five empty bags + ride) gives CAUTION ≤ 25 %; set O CAUTION-or-STOP frames on in-gauge
  objects and range_test B/C CAUTION+STOP while visible are no fewer than v1; roundT_doubleT
  catch-up CAUTION 9 → 0; `tests/test_node.py` and the CI docker job green.

#### C2 · `clear_distance` consistent with the advisory output; publish the overclaim scorer first
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
**Criteria** 8.7, 8.4 · **Owner** P4 lane (P1 runs it; a fresh-context agent that did no tuning;
P3 reviews the misses) · **Mode** A · **Size** M · **Points** 8.7 up to +1 ("no held-out data"),
8.4 +0.5; one honest held-out line for the pitch · **Depends on** spec: nothing; run: the final seal
* **Evidence:** judge: "All tuning used the development data; no held-out real set". The 1.1.0 gains
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
**Criteria** evidence for 8.1–8.8 (8.2 confidence, 8.5 claims, 8.8 honest numbers) · **Owner** P1
orchestrates (a fresh-context agent runs and scores; P2 turns the table into the deck chart) ·
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
  0.3 m dip there); add a 5 cm cable probe to X3 / G3. Check the interaction with the 1.1.0 free-top
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
**Criteria** 8.5 (claims), 8.8 (credibility) · **Owner** P1 (agent) · **Mode** A · **Size** S ·
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

#### D2 · Archive the 28.09 experiment layer: process notes, personal-path tests, orphan scripts
**Criteria** 8.5, 8.7 · **Owner** P1 (docs; tests and scripts are the P4 lane, run by the captain
since 25.09) · **Mode** A · **Size** S · **Points** ~+0.5 on 8.5, ~+0.25 on 8.7 · **Depends on**
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
