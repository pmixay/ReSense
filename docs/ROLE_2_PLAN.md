# Role 2 — execution plan through the 23 October defence

> **Purpose:** finish P2's interface, documentation, visual evidence and demo support against
> the organizer requirements and the team's accepted work. **Owner:** P2 · **Language:** EN
> **Registered:** 2026-10-16 · **Branch:** `role-2`
> **Base:** `b0c9c17cde65a59ddf93fb2799bc94a8a6a31bd1` (`integration/2026-10-15-16`).
> **Status:** implementation in review; [execution receipt](evidence/p2_execution_2026-10-16/README.md)
> tracks completed preparation and pending acceptance. Release, measurements and approvals remain pending.

16.10 execution update: P4's verified export and raw archive have been received;
[draft charts/deck](presentation/draft_2026-10-16/README.md) are prepared.
All 47 webapp browser tests pass. Final release J1 and external acceptance remain open.

## 1. Goal and starting point

Deliver **100% of the applicable P2 acceptance checks**, make the jury's view of the system
accurate and easy to use, and maximize the score the team's measured solution can justify.
The last independent assessment is **66/100 on v1.0.0, 13 October**. The 100-point weights
are internal; the organizers publish eight criteria, not numeric weights. P2 completion
does not itself establish a new system score. J1 and the organizers' decision O1 determine
what improvements can be credited.

Read this alongside [BACKLOG](BACKLOG.md) §5 and cards D1/C1/PT1/PT2/S5/D2,
[CAPTAIN](CAPTAIN.md) §8, the [integration ledger](evidence/integration_2026-10-16/README.md),
and the [review/source register](evidence/p2_plan_2026-10-16/README.md).
The dated integration acceptance takes precedence over older proposed implementations.

### Accepted state to build on

| Area | Actual state on the fetched snapshot | Consequence for P2 |
|---|---|---|
| Delivery | Published `v1.0.0` → `5d6e9b5`; package **1.1.0 sealed but unreleased**; H6/E1 pending | Separate release identity from checkout version everywhere |
| H5 | 36-file seal digest `db3f588df59184ad703436996f72bd94a91eca91dfcfe4a02655fcdd4397d751`; local default-manifest verification PASS | Use this source for consumer development; media claiming a release waits for its actual archive |
| H1 | Free-top withdrawn (`column_free_max_top=0`); inherited High tall-object miss remains open | Do not advertise the historical 157-frame pole gain; selected A-axis probe is **82/177** |
| H2 / axis cap | Selected C-person probe **82.77 m / 55 STOP frames**; monitored-range cap accepted | Identify this as a specific synthetic probe; the cap does not fix the curve axis or prove better recall |
| Runtime | Shared **v1**; `decision_policy` and `caution_reason` present; runtime v2 rejected | C1 display can start now; implement accepted semantics |
| S1 | Failed candidate removed; queue 40, startup step 0, startup lag 20 s retained | Keep supported player flags; no claim that literal playback freshness was fixed |
| E2 | Offline rebuild locally passed on an E2-compatible image; new tagged workflow pending | Instructions must name the compatible image; do not promise this capability in the old archive |
| P2 preparation | D1 pass 1 and slide cuts integrated; 16 slides, recorded audit 963 words/max 80 | Reuse them; final charts, media and P1 sign-off remain open |
| P4 | v1.0 X3 baseline complete; G3 spec only; new X3/X1/J1-prep protocol at `058a451` | Consume P4's forthcoming results; release J1 still waits for E1; G3 is not available for UI experiments |
| O1 / PT2 | Organizer message prepared, not dispatched; no recorded rehearsals | Five minutes is a planning assumption; P1 supplies allowed version/format and leads rehearsals |

## 2. Requirement and scoring coverage

Every acceptance row below must have an artifact and a dated check. Targets are work-completion
conditions, not self-awarded points. [SCORECARD](SCORECARD.md) remains the score source.

| Criterion / current score | P2 contribution | Acceptance / dependency for the remaining score |
|---|---|---|
| **8.1 Detection — 15/25** | C1 reasons, faithful STOP/FAULT/freshness presentation, visible misses/false alarms | Display matches producer decisions in all registered consumer cases; P1 C1/C2 and P3 detector fixes, measured by P4, determine detection gains |
| **8.2 Range — 9/15** | PT1 chart by geometry and object, first and sustained STOP, visible misses | All J1 rows represented without favourable-case selection; at least 3 geometries on-slide; P3 X1-driven work owns range improvement |
| **8.3 Speed — 7/10** | S5, clearly labelled processing time versus result age and UI replay speed | Final-image benchmark with hardware, raw runs, p95/freshness/memory; P1/P3 own S1/S2/S3 fixes |
| **8.4 Generalization — 8/15** | X3 perturbation chart and accurately qualified G3 summary | P4 confirms results and denominators; preregistered synthetic placements on known backgrounds are not unseen real tunnels |
| **8.5 Technical quality — 7/10** | D1, backward-compatible consumer code, tests, reproducible visual artifacts; D2 later | No unsupported current claims, broken changed links, consumer regressions or undocumented format changes; P3/P4 retain code-complexity work |
| **8.6 Launch — 8/10** | Clear offline jury instructions, second-device check, optional-viewer dependency disclosure | P1 E1 archive/checksum verification plus literal execution of documented commands; website availability does not substitute for the offline ROS chain |
| **8.7 Team approach — 8/10** | Compact evidence trail explaining rejected H1/S1/C1-v2/R1/R2 attempts | Hypothesis → measurement → accepted/rejected outcome, with sources; G3 execution and data claims stay P4-owned |
| **8.8 Pitch — 4/5** | Readable deck, honest charts, matched video, timed fallback and rehearsal support | P1 signs off PDF/speech; two logged rehearsals within O1's duration (5:00 until confirmed), fallback ≤30 s |

The original backlog estimates roughly **+0.5 for D1**, **up to +1 for PT1** and
**~+0.5 confidence for S5**, with D2 gains later. These estimates overlap other work and
are not guaranteed/additive. Near-100 system quality also requires closing the remaining
8.1/8.2/8.4 failures and runtime limits; polishing the UI cannot close those deductions.

### Organizer constraints applied to every task

* ТЗ §3/§4/§7.2: Ubuntu 22.04 / ROS 2 Humble / Docker; show **container → bag → cloud →
  obstacle → distance**. Runtime is offline; prepare all assets/dependencies before disconnecting.
* ТЗ §5: the README must cover build, run, bag processing and parameters; architecture,
  algorithm, experiments and a short video must remain directly reachable.
* Q&A and answers §8–§9: the **2.1 × 3.0 m** envelope is referenced to the rails; the
  implementation's 0.12 m floor is a configuration choice. A 30 × 30 × 10 cm bed object
  below the envelope is a negative control; a hanging cable entering it is required.
  Platform people outside the envelope are not obstacles. Synthetic placements may drift.
* Two organizer topic/frame pairs and consecutive bags are supported. No required odometry,
  external API or GPU. The demo must distinguish a standing real-person recording from a
  moving recording containing synthetic objects.
* ТЗ §8.2 and Q&A: show range/reliability trade-offs and sightline limits. The observed
  ~210 m return limit concerns the recorded real data; ideal synthetic returns beyond it
  are not a measured real-sensor range. Braking control is outside this case.
* Online defence **23 October**. The 29 September submission cutoff still applies unless
  P1 records a new organizer answer. Preserve template slides **7–11** in design/structure;
  custom content uses the allowed layouts. Five-minute timing awaits O1.

## 3. Team interfaces and ownership

| Provider / owner | Input P2 needs | P2 return / handoff |
|---|---|---|
| **P1** | O1 reply; final accepted source/tag/archive/image digest; complete CI receipt; approved runtime contract; demo device and speaking schedule | Consumer PR and payload examples, updated runbook/docs, PDF/media, S5 report, rehearsal log; P1 approves shared docs and pitch and merges |
| **P3** | Accepted detector-change summary and limitations; validation of X1 interpretations and geometric chart labels | No speculative fix claims; screenshots of failures linked to case/frame; detector requests go through P3/P1 freeze procedure |
| **P4** | J1 table/`delta.md`/score, X3 comparison, eventual G3 results; raw artifact access and exact matching definitions | Deterministic charts and captions for P4 numeric review; no re-scoring or tuning by the renderer |
| **P2** | Existing dashboard, label tool, RViz/Foxglove layouts, deck/video tooling | C1 consumers, D1 passes, PT1 visuals, PT2 fallback/second device, S5; D2/X2 snapshots after defence |

Direct P2 paths: `web/`, `ros2_ws/src/resense_ros/rviz/`, `docs/images/`, `docs/img/`.
Deck/video work uses `scripts/build_deck.py`, `scripts/make_overview_video.py`,
`docs/presentation/`, `docs/video/` with P1 content approval. D1 edits P1-owned docs as
assigned in BACKLOG. Coordinate `webapp/` changes with P1 (its documented owner), and
backend field propagation with its maintainer. RViz text is generated in P1's
`detector_node.py`; changing only the `.rviz` layout cannot add reasons.

Publish focused commits on `role-2`, with `[contract]` on any PR changing a wire contract.
Add optional fields compatibly; record the source SHA of each handoff. Reconcile incoming
integration commits before implementation and again before final media generation. P1's
H6/E1 and P4's active evaluation remain independent workstreams.

## 4. Ordered work packages

### P2-01 · D1 checkpoint reconciliation and evidence intake — first, 16–17 October

**Budget:** 3 h. **Inputs:** fetched integration and participant handoffs; no new evaluation needed.

1. Refresh `web/P2_STATUS.md`, relevant GitBook output/launch pages and maintained docs to
   distinguish released 1.0.0, sealed-unreleased 1.1.0, pending release evaluation and rejected
   experiments. Preserve dated evidence as history.
2. Fix the remaining concrete review gaps: C1 marked absent despite its producer; old package
   versions in CAPTAIN; stale branch/review states; `docs/README.md` demo ownership; overview
   duration described as both 2:50 and 3:00 (measure the actual file with `ffprobe`).
3. Trace each current headline to its result file, measured commit, pipeline, data type,
   denominator and machine. Hand P4 the residual dual-return wording in DATASET; coordinate
   EXPERIMENTS changes with P3/P4. Maintain one numeric source rather than another results table.
4. Prepare the P4 chart-input agreement in §5 and the P1 marker-text request in P2-02.

**Done:** changed maintained docs agree with selected scope; D1's stale-claim searches and
relative-link check are reviewed; no current text credits withdrawn H1, S1 or C1-v2; P1/P4
handoffs explicitly list any owner-blocked correction. This pass may complete before E1/J1.

### P2-02 · C1 display and faithful decision presentation — 16–18 October

**Budget:** 6 h plus 2 h coordinated webapp/marker work. **Inputs:** accepted v1 source and
[C1 contract](evidence/caution_policy_2026-10-15/CONTRACT.md), interpreted with the later
[runtime selection](evidence/integration_2026-10-16/runtime_selection.md).

**Implementation sequence:**

1. Capture producer examples for GO, CAUTION (object/health/both), STOP, held STOP and FAULT
   from accepted node fixtures. Use the shared Python policy as the oracle for fallback
   conformance, not a new frontend interpretation of detection.
2. Extend `web/assets/result-format.js` and dashboard `web/index.html`: validate optional
   reason arrays, render plain-text Russian explanations, preserve unknown codes generically,
   and show absent legacy reasons as unavailable. Keep the published decision and existing
   freshness/latch guards. The label tool must continue opening legacy results.
3. With P1, extend `webapp/frontend/src/api/types.ts`, ROS input validation, Live/Player/RunDetail
   presentation and corresponding tests. Trace `worker.py` → stored results → HTTP/WS → UI:
   offline-generated rows may require backend metadata propagation. Preserve imported historical
   decisions; do not silently rescore a saved run to obtain reasons.
4. Replace misleading unqualified GO wording (`СВОБОДНО` in `src/lib/decisions.ts`) with
   **«Препятствие не обнаружено»**, or a compact `GO` with that explanation visibly adjacent.
   `clear_distance` is **estimated monitored range**, not guaranteed free path. Keep layout
   readable at 1280×720 and 1920×1080 desktop screen-share sizes.
5. P1 updates the RViz status marker using the already evaluated policy reasons; P2 checks
   the view and Foxglove layout. No new ROS plugin should be needed. Foxglove LAST-value
   behaviour must be explained; disconnection is not current GO.

**Reason labels:** `advisory_object` → «Предупреждение об объекте»;
`health_warning` → «Снижена достоверность данных». The other documented codes (`doubt`,
`margin_object`, `compact_range_object`, `incomplete_advisory`) get descriptive labels for
stored/forward-compatible data, without offering runtime v2. Unknown strings remain text,
never HTML; no warning is suppressed to make the display calmer.

**Required acceptance matrix:**

| Case | Required behaviour |
|---|---|
| v1 CAUTION with one/multiple reasons | Same CAUTION as node; all distinct reasons readable; health details remain available |
| Legacy payload with no new fields | Same published decision; «причина не передана» when applicable; no crash |
| Unknown reason code | Generic readable text, no HTML execution or decision change |
| Malformed optional field / invalid decision or flags | Explicit invalid/unavailable data under the existing boundary policy; never a fresh GO or silent loss of held STOP |
| STOP / FAULT / GO after CAUTION | Previous CAUTION explanation cleared; zero stale reason carryover |
| Held STOP, watchdog, processing error | STOP retention and last-distance label preserved; missing boxes are not “no obstacle” |
| Stream silent >0.5 s, disconnect, stale source despite frequent receipt | No current-green indication; expose freshness failure and historical/held values correctly |
| Pause, seek, reconnect, new bag/topic/frame | Recording state clearly labelled; old connection callbacks/reasons cannot replace the new source |
| Offline JSONL / HTTP / simulated WS / real ROS | Equal meaning for equal valid payloads; simulation visibly labelled and never used as detector latency evidence |

**Done:** matrix passes on both web clients; RViz reason display demonstrated after P1's
producer patch; label-tool compatibility, frontend types/build and affected backend/browser
tests pass; no decision/range/STOP-latch change introduced by presentation code. Record exact
versions and screenshots in a new P2 evidence directory.

### P2-03 · PT1 source-driven charts and final deck — preparation now, numbers after J1

**Budget:** 4 h. **Inputs:** P4 X3/J1, O1 version decision; G3 only after its final execution.

1. Prepare a renderer/import path for §5's source table. Reuse `build_deck.py`; keep the
   historical cache `GATE` check but add a distinct node-path source check for final headline
   numbers. Update artifact tests to verify the declared source rather than whichever filename
   happens to sort latest. Chart values and video cards come from the same accepted input.
2. Replace the single favourable range headline with a geometry × object chart: straight,
   curve, double-track, platform where measured; person-size box, 1 m cube, 0.3 m cube;
   first STOP and sustained/held-90% distance. At least three geometries visible, full table
   in notes/appendix. Display “not measured” and misses explicitly. Keep real person, organizer
   synthetic objects and ideal ray-casts clearly distinguished.
3. Add compact false-STOP episodes/time/km and fresh/processed/total counts; separate detection
   latency, publication/source age and multi-frame confirmation delay. Show X3 failures as well
   as passes and explain G3's actual scope. Keep the open tall-object limitation visible.
4. Preserve team names/photos and required template layouts. Keep **≤80 words per slide and
   ≤1,100 total**, including chart labels; this uses PT1's stricter task target rather than its
   looser 90-word acceptance line. Move technical detail to notes. P1 owns speech/Q&A changes.
5. Rebuild PPTX/PDF and visually inspect every page for clipping, tiny units, layout changes and
   illegible screen-share charts. P4 checks every chart row; P1 signs the final PDF.

**Done:** numeric parity with accepted J1/X3 sources, gate check and word audit pass; at least
three geometries; PDF visual review and P1 approval logged. J1 missing means preparation only,
or an explicitly v1.0.0 historical deck under the fallback decision in §6.

### P2-04 · PT2 release-matched fallback, offline demo and second device — 18–22 October

**Budget:** 3 h media/device preparation plus two team rehearsals. **Inputs:** P1-selected
permitted released image, checksum, approved demo route and hardware.

* Load the exact verified archive and record tag/source/image ID, seal, bag hash and commands.
  Follow the supported `--net=host`, DDS buffer and bounded player-queue instructions. Warm-up
  or pre-reading the bag for a demo is disclosed and kept separate from a cold-start benchmark.
* Record a short new fallback showing launch, FAULT before input, bag playback, cloud/envelope,
  STOP and distance, and loss-of-input behaviour. A moving Set O insert is labelled synthetic;
  `doubleT_obstacle` is a standing real scene. Add Russian captions and a source/version card.
  Keep archival clips labelled with their original date/version.
* Update overview cards/subtitles/voice consistently with the chosen evidence; measure final
  duration, inspect legibility and caption timing, verify local MP4 playback without internet.
* Rehearse screen sharing on the captain's laptop and a second device. Use RViz as the primary
  jury chain; Foxglove/rosbridge are optional viewer dependencies prepared in advance. The
  web prototype stays explicitly outside the runtime image unless P1 changes packaging.
* P1 leads rehearsals by **19 October** and **22 October**. P2 operates the second display,
  measures the forced fallback switch, and records version/time/demo outcome. P3/P4 supply
  the mock jury; cover poles, curves, small objects/cables, false alarms, freshness, data reuse,
  range definitions, offline launch, release eligibility and team contribution.

**Done:** two actual dated logs, talk within confirmed time (otherwise ≤5:00), STOP near
56 m within 30 s of playback, forced fallback ≤30 s in rehearsal 2, and local media available
on both devices. Historical instructions or a prerecorded video alone do not close rehearsal.

### P2-05 · S5 benchmark on available hardware — run by 21 October

**Budget:** 2 h plus machine time. **Inputs:** available idle host, raw bags/caches,
selected source/image, P1/P4-agreed protocol. Local i5-8250U is **4 cores / 8 threads**.
**Captain decision 17.10:** no 8-core VPS prerequisite; 2–4-core measurements are acceptable
with the actual hardware and measured result named. Source runs can proceed while the captain
resolves GitHub billing/quota; release remains deferred until CI is fixed.

1. Register machine/image/input identities and conditions before measuring. Record topology,
   affinity/quotas, RAM, disk sequential-read throughput, DDS/player settings, native backend,
   Python/NumPy and background load. The approximate 360° playback demand is 225 MB/s.
2. Load the verified final image. `bench_8core.sh` otherwise builds/reuses `resense:latest`;
   deliberately alias the inspected release image and use **`SKIP_BUILD=1`**, recording the
   full image ID before/after. Host offline timings require the matching source checkout.
3. Run the existing kit, then separately the **four Docker conditions × three repetitions**:
   360°/120° × literal/README player, using the selected shipping runtime. The kit's console
   smoke checks are not this matrix and do not establish freshness acceptance.
4. Retain every run and completeness verdict. Report processing p50/p95/max, FPS, fresh vs
   processed vs input frames, source age, first STOP lag, STOP frames, drops/skips, CPU/RSS.
   Explain cold/warm conditions and machine differences; do not extrapolate to i7-9700E.

**Done:** kit exit 0, complete four-condition summaries and raw evidence, actual hardware record;
S5 targets **README 360° p95 ≤80 ms, fresh ≥195/201** explicitly PASS/FAIL. Also report S1
thresholds from BACKLOG without relaxing them. S1/S2 may remain unshipped: benchmark the final
selected runtime anyway and retain any failures. P1/P3 own corrective runtime work.

### P2-06 · D1 final pass and P2 acceptance handoff — 21–22 October

**Budget:** 3 h. **Inputs:** final release identity, P4's accepted results, S5 and media.

* Reconcile README, GitBook, REQUIREMENTS_MAP, PRESENTATION, SCORECARD references, P2_STATUS,
  demo runbook, deck notes, video captions and image descriptions to one version/evidence set.
  Scores change only when P4 supplies the new independent judgement.
* Execute documented viewing commands, check public repository/release/PDF/video/GitBook links
  logged out, and verify the offline copy. Record deployed web source identity separately.
* Run relevant checks in §7 and publish a concise acceptance table with PASS/FAIL/BLOCKED,
  tested SHA, commands, artifacts, owners and residual limits. P1 receives the PR and final
  media manifest before the second rehearsal. Any version change invalidates affected checks
  and requires refreshed media/numeric acceptance.

**Done:** all applicable P2 checks have receipts; open external dependencies remain named;
P1 has approved the final pitch materials and two rehearsal entries exist. P2 must not mark
overall completion while a required device, release, result table or sign-off is missing.

### P2-07 · After 23 October: D2 and X2 support

Follow the existing backlog order: coordinate D2 archival moves with P1/P4, preserve inbound
links, executable evidence and immutable hashes, replace personal-path assumptions through
the owners, then run affected tests. The new archived-lint integrity checks mean a bulk move
cannot be judged by Markdown file count alone. For X2, render BEV/side snapshots against P4's
episode ledger and human-confirmed classes. P3 owns F2/K2/S4/G1/G2/T1 improvements; P2 updates
their explanatory materials after accepted measurements. These tasks do not displace demo
readiness before the defence.

## 5. Evidence handoff contract

Agree the actual export with P4 before implementing it; this is the required information,
not a claim that a new API already exists. Reuse existing JSONs wherever possible.

**Every numeric row:** criterion/task, measured full SHA + seal digest, release/image when
applicable, protocol/scorer identity, recording/case, real/organizer-synthetic/team-synthetic,
in-sample/held-out scope, geometry/object dimensions, units, numerator/denominator, source
file + JSON key or CSV row, PASS/FAIL and limitations. Range rows carry first STOP,
held-90% definition/value and visible/matched counts; absent results are null with a reason.
Timing rows identify the machine and clock being timed.

**Preservation:** provide retrievable raw files or a durable archive plus checksum/restore
instructions. P4's new protocol says large raw files may remain only in an ephemeral
container: request export before it is retired. A hash index alone identifies evidence but
cannot reproduce a plot or validate its rows. Mark unavailable raw evidence explicitly.

**P2 output package:** source-table identity/hash, renderer invocation, generated chart/media
hashes, caption/source map, visual review, test receipt and P1/P4 review status under a fresh
dated `docs/evidence/p2_<task>_<date>/` directory. Keep full recording names: **B is
roundT_doubleT; C is roundT_pressureGate_roundT**. Separate 1 cm gate metrics from node-decoded
metrics, events from episodes, label rows from frames, and nominal gates from robustness runs.

## 6. Schedule, dependencies and fallback decisions

| Date (MSK) | P2 milestone | Required external event / action |
|---|---|---|
| 16–17 Oct | P2-01; C1 fixtures/UI start; chart scaffold; reserve S5 host | P1 confirms marker/webapp handoff, sends O1; P4 continues X3 → X1 → J1 prep |
| 18 Oct | C1 consumer acceptance, draft charts, media preparation | P1 H6/E1 when resumed; P4 release J1 after E1/X3; rejected detector work is not a dependency |
| 19 Oct | First permitted-version demo/fallback and rehearsal | P1 leads, P3/P4 mock jury; provisional charts clearly dated if J1 is unfinished |
| 20 Oct noon | Confirm final detector/release choice from P1 | Original bundle cutoff; only accepted/resealed/released changes enter final claims |
| 21 Oct | S5, final chart/media numbers, D1 pass 2 | P4 final J1 and separately assigned G3; P1 final PDF/speech approval |
| 22 Oct | Final device/offline/link check and second rehearsal | Forced fallback, timed Q&A, final release/media identities locked |
| 23 Oct | P2 display/fallback support during defence | P1 presents; all claims use the approved version and sources |

Estimated P2 effort **~26 hours (23 planned + 3 integration contingency), plus rehearsals/machine
time**, with dependency waiting outside the estimate. Protect C1 fidelity, final numeric accuracy and the demo before optional
visual expansion. Notify the named owner on the day a dependency slips and record the revised
date in P2_STATUS; a calendar date never changes a pending task to DONE.

* **O1 absent or v1.0.0-only:** use v1.0.0 for scored claims/demo; retain later work as clearly
  labelled development material only where P1 confirms it is allowed. Use 13.10 evidence for
  honest historical charts; final J1-on-new-release remains blocked.
* **No new release by rehearsal:** rehearse the permitted published image and record that exact
  version; swap only after E1 verification and repeat affected checks.
* **J1/X3 late:** final visual work can use explicitly dated v1.0.0 evidence; no inferred new
  score or invented range values. **G3 late:** say “registered, not executed”; no held-out gain.
* **No ≥8-core machine:** proceed on available hardware, including 2–4 cores, under the captain's
  17.10 decision. Keep source runs distinct from final-image runs and report the actual topology,
  affinity/quota and PASS/FAIL. Do not multiply timings by a core-count ratio.
* **P1 marker change late:** web C1 can finish; RViz subtask remains open and uses the existing
  decision display. **Live connection fails:** measured local fallback within 30 s.

## 7. Verification and completion rule

Run commands from the repo root in an environment with the documented dependencies; use
`python3` on this host. For execution, install root, ROS Python and backend packages as in CI,
plus Open3D, Playwright/Chromium and frontend dependencies. Required browser checks must not
silently skip. Capture environment, command, exit code and tested SHA.

```bash
python3 scripts/detector_freeze.py verify
bash scripts/sync_params.sh --check
python3 scripts/release_meta.py version
RESENSE_REQUIRE_WEB=1 python3 -m pytest -q -rs web/demo tests/test_overview_video.py
npm --prefix webapp/frontend test
npm --prefix webapp/frontend run build
python3 -m pytest -q -rs webapp/backend/tests
python3 -m pytest -q -rs webapp/e2e
python3 scripts/build_deck.py --audit docs/presentation/ReSense_LCT2026.pptx
python3 scripts/build_deck.py --check-gate docs/evidence/results/regression_baseline_2026-09-29_shell_off.json
git diff --check
```

Use the baseline declared by the final release if P1 registers a successor. `--check-gate`
alone does not check J1 headlines: P2-03 adds source-parity verification. Run the backend/e2e
commands when those paths are affected; marker/contract changes also need P1's node/policy
tests and `scripts/p2_viewer_test.sh` on the selected image. After each focused change passes,
complete the full applicable P2 suite once on the assembled candidate; P1 owns full merge CI.

Manual checks: every PDF page, source/chart parity, readable captions, actual video duration,
second device, offline assets, actual ROS/Foxglove payload, disconnect/held STOP, logged-out
links and two timed rehearsals. Tests cover behavioural boundaries and actual regressions,
not the wording of this plan.

**Completion:** all P2-01…06 acceptance conditions fulfilled with evidence, P1 content approval
and P4 numeric review. Report task completion separately from the system's independently
measured score. The next executable item is **P2-01**, followed immediately by **P2-02**;
chart preparation and hardware booking can proceed while release evaluation is pending.
