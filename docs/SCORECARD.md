# Criteria judgement (spec §8) — 24.09, commit `d58567e`

**How this was judged.** One reviewer with no stake in the work judged the repository at commit
`d58567e` (branch `claude/festive-turing-8y6no1`; the code is identical to `main` at `4cd32d6`,
only documentation and one JSON file differ) against the organizers' technical specification
§5, §7.2 and §8 ([`organizers/technical_specification_case05.txt`](organizers/technical_specification_case05.txt)),
the Q&A session ([`organizers/QA_session.md`](organizers/QA_session.md), with the Russian
transcript) and the written answers of 23.09 ([`organizers/answers.md`](organizers/answers.md)).
The weights of the criteria are not published. The reviewer read the README, ARCHITECTURE,
ALGORITHM, EXPERIMENTS (with the raw file `experiments_2026-09-24_remeasure.json`), EVALUATION,
SUBMISSION, the code in `resense/` and `ros2_ws/`, the scripts, the tests, the CI workflow, the
Dockerfile and the stored Docker evidence, and treated every claim as unproven until checked.
Run by the reviewer on 24.09:

- the test suite (198 passed in 45 s, no skips with `RESENSE_REQUIRE_SYNTHETIC=1`), `ruff check .` (clean) and `scripts/sync_params.sh --check` (in sync);
- `scripts/eval_real.py` over all 13 759 real frames: the per-recording summary is identical to the team's record, field by field;
- a recount of STOP episodes, events first confirmed beyond 100 m, the `CAUTION` share and the labelled person and object hits from those per-frame outputs;
- the same full run with the opt-in near-bed path (`lowobj.near_enabled: true`), which the team had never measured on real data;
- set F spot checks (synthetic objects ray-cast into the moving ride) and the farthest return in 40 sampled frames per recording.

Not run: Docker (another agent held it). For the container chain the reviewer relied on GitHub
Actions run 92 on `main` (all 5 jobs green; the Docker job logs were read) and on
[`evidence/docker_2026-09-23/`](evidence/docker_2026-09-23/). The full review, with every
finding and its evidence: [`reviews/2026-09-24_review.md`](reviews/2026-09-24_review.md).

## Scores

Each criterion is scored on a 10-point scale.

| § | criterion | score (/ max) | one-line reason |
|---|---|---|---|
| 8.1 | **Works** (the main criterion) | 6 / 10 | The one real obstacle scene is solved (person 58 of 61 frames, object on the rail 124 of 126), but the obstacle-free ride has a false STOP episode every ~31 s and nothing on the bed between the rails is ever reported |
| 8.2 | **Range** | 6 / 10 | A person is held in every 10 m band from 115 m and first confirmed at 148 m, but only on synthetic objects with detector-derived placement; 30 cm objects on a rail head from 42–49 m; the sensor returns nothing beyond 210 m |
| 8.3 | **Speed** | 6 / 10 | 35–64 ms mean per frame on one core offline and 10 fps at 120° through ROS; 7–10 fps at 360° on 4 vCPU, 1–6 s lost at the start of a played bag, i7 stand not measured |
| 8.4 | **Generalisation** | 6.5 / 10 | Map-free tunnel model rebuilt every frame and mount calibration from the data; about 15 infrastructure rules tuned and scored on the same seven recordings, one real obstacle scene |
| 8.5 | **Technical quality** | 8 / 10 | Pure-Python library and a thin node, 198 tests, CI 5 of 5 including ROS in Docker, real-data results reproducible frame for frame; about 4 600 lines of docs with some stale statements |
| 8.6 | **Ease of launch** | 8 / 10 | `docker build → docker run → ros2 bag play → /resense/decision` with no arguments and either topic pair; the start-up hole and a `CAUTION`-heavy decision stream are what the jury will see |
| 8.7 | **Team approach** | 8.5 / 10 | Ten methods compared with the rejected ones kept, ablations, a leakage check, a leave-one-subset-out check, every number marked real or synthetic |
| 8.8 | **Pitch** (lower weight) | 6.5 / 10 | Template deck with a strong main shot; outdated numbers on five slides, placeholders on slides 2–4, all four videos silent |
| — | **indicative total** | **6.9 / 10** | weighted mean: 8.1 counted twice, 8.2–8.7 once, 8.8 at half weight (58.25 / 8.5) |

The total is indicative only: the organizers publish no weights, and the hidden control data
decide 8.1, 8.2 and 8.4.

## What each score rests on and what holds it down

"Real" means the organizers' recordings; "synthetic" means objects ray-cast into real frames
(set F: into consecutive frames of the moving 20-minute ride), placed with the detector's own
per-frame axis and bed ("legacy" placement).

### 8.1 Works — 6 / 10

Rests on (real, reproduced by the reviewer with `scripts/eval_real.py`):

- `doubleT_obstacle`: the crossing person is reported in 58 of the 61 frames in which it is inside the 2.1 × 3.0 m envelope, first at frame 11 (0.3 s after entering it), distance error ≤ 0.23 m; the organizers' object lying across the rail in 124 of the 126 frames after the person leaves it (127 of 185 by its own detection); no false alarm on this recording.
- Five obstacle-free recordings (2 287 frames, 229 s): 107 alarm frames, 20 events, 27 STOP episodes.
- The 20-minute, 13 km ride (11 271 frames, no obstacles by the organizers' written answer): 204 alarm frames (1.8 %), 47 events (3.6 per km), 39 STOP episodes.
- Starting processing 0–40 frames late, as a played bag does: 14–20 events on the five recordings (team record, `start_offsets.py`, not re-run).
- Synthetic (set F round 3): a person on straight track 6 of 6, in R ≈ 350 m curves 6 of 7, at station stops 6 of 6; a 3 cm hanging cable 6 of 6.

Held down by:

- **False stops.** 39 STOP episodes in 20 minutes of the ride is one every ~31 s. 25 of the 27 episodes on the five recordings come from `squareT_platform_squareT_switch` (88 s, the platform-end structure).
- **Nothing lying on the bed between the rails is reported, by policy.** Set F round 3: a 30 × 30 × 10 cm box 0 of 6, a 30 cm cube 1 of 6 (at 9 m), a dog-sized 0.6 × 0.3 × 0.45 m box 1 of 6 (at 50 m). The envelope floor at 0.12 m above the rail head is the team's own assumption. The organizers said "anything in the train envelope of at least 30 × 30 × 10 cm" and "someone may throw a dog", and their own synthetic-obstacle tool is part of the hidden check. The question is not among the open questions to the organizers.
- **The opt-in fix does not work.** With `lowobj.near_enabled: true` the reviewer measured 145 events (1 035 alarm frames) on the five recordings and 667 events on the ride (3 730 alarm frames, 33 % of the ride, 247 STOP episodes), against 20 and 47 with the defaults. On the same bed set it finds the dog-sized box in 5 of 6 approaches, but only from ~20 m. The 30 × 30 × 10 cm box stays at 0 of 6, and 69–75 false detections appear per set, against 0–6 with the defaults.
- `CAUTION` covers 27–68 % of the frames of the obstacle-free recordings and 41 % of the ride (reproduced).
- One real obstacle scene, standing still at 55–57 m; every other positive is synthetic.

### 8.2 Range — 6 / 10

Rests on (synthetic, set F round 3 on the current code, team record):

- A person on straight track, no speed input: first confirmed at 148 m (median of 6, range 110–169 m). Held in ≥ 90 % of the frames from 149 m (median) and in every 10 m band from 115 m (per approach 20–160 m). The reviewer's re-run (the person alone, so the lateral draws differ) gave a median first confirmation of 147 m (110–158 m), held from 151 m.
- With a train speed (5-frame accumulation): a person first confirmed at 167 m.
- A 1 m crate first at 111 m, held in every band from 105 m. A trolley first at 144 m, but held in every band only from 70 m.
- A 3 cm hanging cable first at 95 m, held only from 53 m, and in 4 of 6 approaches only.
- In R ≈ 350 m curves: 58–86 m, which is the sightline. The organizers accept the visible limit there.
- Real: the farthest return in any sampled frame is 209.5 m (reviewer, 40 frames per recording), so 300 m is out of this sensor's reach.

Held down by:

- The organizers' own size criterion (30 × 30 × 10 cm) is found only on a rail head, from 42 m (the box) and 49 m (the cube), and never on the bed.
- Every long-range number is synthetic, with a placement derived from the detector's own far-field model. EVALUATION.md §3 itself says this can flatter the curve and edge sets, and the independent placement mode has never been run.
- The only real obstacle is at 55–57 m.
- The organizers rate below 100 m "poorly". A person is in the "good" band (100–200 m); small objects are not.

### 8.3 Speed — 6 / 10

Rests on:

- Offline, one core with single-threaded BLAS: 42–64 ms mean, p95 53–78 ms per frame on every recording (team, 23.09, [`evidence/timing_2026-09-23/`](evidence/timing_2026-09-23/)). The reviewer's full run on 24.09, with two jobs in parallel on 4 vCPU, gave 34.6–53.0 ms mean and p95 44.6–69.3 ms.
- Through ROS in Docker (team evidence, 23.09): the 120° recording at 10 fps, p95 76 ms. The node container used ~100 % of one core and 186 MB (14 samples). No GPU is used.
- The node skips frames instead of lagging (keep-last 1) and reports its dropped-frame count.

Held down by:

- **At 360° through ROS on 4 vCPU: 7–10 fps.** Latency p95 was 99–151 ms per 2 s window in the stored `ct_real_node.log`, and the stored dry run dropped 86 of 201 frames. The whole 360° cloud is processed, including the half behind the train.
- **The start of a played bag is lost.** The stored logs show 4.5 s (120°) and 4.9 s (360°) of the first seconds unprocessed with the shipped UDP profile, and 6.0 s before it. Every hole longer than 1 s resets the scene. A fix is in progress elsewhere.
- The 0.5 s confirmation adds 11 m at 80 km/h for an object that appears inside the envelope.
- The i7-9700E test stand has never been measured.

### 8.4 Generalisation — 6.5 / 10

Rests on:

- No map: the bed, rails, axis and curvature are re-estimated from every frame. This is the environment-model approach the specification asks for.
- The mount is found from the data (real frames re-mounted by known rotations: tilt residual 0.0–0.5°, orientation found for every upright or inverted mount).
- Either topic / frame pair is taken, and the node switches between recordings.
- A leave-one-subset-out check over 13 subsets: v0.6.2 has fewer events than v0.6.1 in 12 of them and more in none.
- The 20-minute ride was never seen before v0.5 was tuned: v0.5 alarmed on 3.2 % of its frames against 4.2 % on the recordings it was tuned on.

Held down by:

- About 15 infrastructure rules and every threshold since v0.6 were tuned on the same seven recordings they are scored on.
- The false alarms concentrate by scene type: 15 of the 20 events on the five recordings come from one station recording. The organizers' check includes full rides through other tunnels.
- One real obstacle scene. The long-range positives use detector-derived placement.
- The final tilt calibration needs 20 s, so a short control bag with a 0.75–2.5° tilt is never corrected.

### 8.5 Technical quality — 8 / 10

Rests on:

- `resense/` is a ROS-free library with one method per stage (`resense/detector.py`); the node is thin and has guards (watchdog, `FAULT` / `NO_INPUT` / `STALE`, a reset after 5 errors); one parameter file, checked by CI.
- 198 tests pass (reviewer's run), and the node logic runs against ROS stand-ins in `tests/test_node.py`. ruff is clean.
- CI run 92 on `main`: pytest, web, lint, params-in-sync and Docker all green. The Docker job ran the 198 tests inside the image, played two synthetic bags (both topic pairs) through one node, and ran the node and a uid-1000 player in separate containers.
- Every real-data headline number was reproduced frame for frame by the reviewer, and raw summaries are committed.
- The limitations are documented (ALGORITHM.md §6).

Held down by:

- 4 612 lines in README.md and `docs/*.md` at `d58567e` (EXPERIMENTS.md alone 1 266, with three "no new measurement" sprint preambles ahead of its §0). A reader has to work to find the current state.
- Stale statements remain in EVALUATION.md, EXPERIMENTS.md §3b and CAPTAIN.md, and the documented start-up loss is too low (review, "Doc claims").
- Two experimental opt-in paths ship in the detector unmeasured on real data. The reviewer's measurement shows one of them (`near_enabled`) is unusable as it stands.
- Pure Python, and the base image is not pinned by digest.

### 8.6 Ease of launch — 8 / 10

Rests on:

- The jury path heads the README (lines 22–40) and is the organizers' own chain: `docker build`, `docker run … resense` (the default command is the node), `ros2 bag play <bag>` from any console, `ros2 topic echo /resense/decision`.
- No argument is needed for either topic / frame pair.
- The image runs Fast DDS over UDP only, so a player run by a normal user reaches a root node. CI proves this with a uid-1000 player in its own container.
- All dependencies are installed by the Dockerfile, with pinned pip versions.
- The "What to look at" table names the one topic to read.
- There are headless, RViz and Foxglove paths, and an acceptance script (`dry_run.sh`).

Held down by:

- The first 1–6 s of a played bag are not processed (the decision is `FAULT` until the first frame).
- `CAUTION` is the most common state on an empty tunnel.
- CI's "organizers' way" plays the bag from the project's own image, so both sides carry the UDP-only profile. A host console with stock Fast DDS or another RMW is not covered by CI or by stored evidence.
- The image build needs the network: the team has decided the stand has internet.

### 8.7 Team approach — 8.5 / 10

Rests on:

- EXPERIMENTS.md §7 compares ten methods with verdicts, including the rejected ones: a bed-anomaly stage with 1 482 ride events, a rail-level stage with 734, a LiDAR-only speed estimate that raised false alarms.
- §8 keeps a learned second opinion out of the product after finding that intensity leaked the injector.
- False alarms are counted by cause; there are ablations per lever group, threshold margins and false alarms by start frame; each version is compared with the one before on all 13 759 frames.
- The trade-offs are stated with their cost: 0.5 s confirmation, no far alarm without rails, the bed policy.

Held down by:

- The story is spread over thousands of lines of version history.
- The main policy trade-off (the bed) was never put to the organizers.
- All long-range positives are synthetic.

### 8.8 Pitch — 6.5 / 10

Rests on:

- 15 slides in the organizers' template (slides 7–11 kept as required).
- The arc is problem → data → algorithm → main shot (STOP at 55.8 m from the cab) → demo → results → range → reliability → hard cases → next steps.
- A Docker/RViz chain video exists.

Held down by:

- Outdated numbers in the deck and in PRESENTATION.md: a distance error of 0.35 m (now ≤ 0.23 m), "held from 135 m" (149 m), 152 tests (198), small objects "42–44 m" (42–49 m), "confirmation 0.3 s" (0.5 s).
- The `<…>` placeholders on slides 2–4. The captain is working on them.
- The four videos are 20–69 s long and have no audio track.
- Nothing beyond 100 m is shown visually.

## Deliverables (spec §5 and §7.2)

| item | status | evidence |
|---|---|---|
| README: project description | present | README.md lines 1–20 |
| README: how to build the image | present | README.md:25, "ROS 2 / Docker" |
| README: how to run | present | README.md:22–40 (jury path), "ROS 2 / Docker", "Demo without a display" |
| README: how a bag is processed | present | README.md "How a bag is processed" (the node subscribes; `ros2 bag play` from any console) |
| README: parameters and configuration | present | README.md "Parameters worth knowing", ALGORITHM.md §5, `configs/default.yaml` |
| architecture | present | ARCHITECTURE.md (diagram, data flow, formats, real-time budget) |
| algorithm (problem, data, processing, decision, parameters, limitations) | present | ALGORITHM.md §1–§6 |
| experiments: range | weak | synthetic only, detector-derived placement (EXPERIMENTS.md §2d); one real obstacle at 55–57 m |
| experiments: latency, FPS | present, weak on the stand | EXPERIMENTS.md §3, §3b; i7-9700E not measured |
| experiments: false alarms, hard cases, evolution | present | EXPERIMENTS.md §0, §1b, §1d, §4, §7; reproduced by the reviewer |
| video | weak | four silent clips of 20–69 s in `docs/video/`, including the Docker chain with RViz |
| Docker container, runs without manual dependency installation | present | `docker/Dockerfile`; CI run 92 builds it and runs the chain; the build needs the network |
| source code | present | `resense/`, `ros2_ws/`, `scripts/` |
| demonstration on the control bag | weak | the chain works in CI (synthetic bags) and on rebuilt real bags (23.09 evidence); the first 1–6 s of a played bag are lost; no release tag exists yet |

## What would raise each score most (by expected gain per hour)

| # | action | criteria | owner (guess) | effort |
|---|---|---|---|---|
| 1 | Ask the organizers one question: does a 30 × 30 × 10 cm object lying on the bed between the rails, below the rail head, count as inside the envelope, and where is the envelope floor? The answer decides whether the largest detection gap matters for their synthetic check. | 8.1, 8.4 | P1 | 15 min |
| 2 | Correct the outdated numbers on the slides and in PRESENTATION.md (list in the review, section 6). | 8.8 | P2 (captain on slides 2–4) | 1 h |
| 3 | Add a CI step that plays the bag with stock Fast DDS (`FASTRTPS_DEFAULT_PROFILES_FILE` unset in the player container), as a host console would. | 8.6, 8.5 | P1 | 1 h |
| 4 | Finish the DDS start-up fix (in progress), then state the measured loss in README.md and SUBMISSION.md. The stored logs show 4.5–4.9 s, not 2–4 s. | 8.3, 8.6, 8.1 | P1 | **done after this review** (v0.6.4, 24.09, EXPERIMENTS.md §3b): the cause was the player's preload, not DDS; the node now works through the burst, first STOP on `doubleT_obstacle` 4.0 → 1.6 s of recording time, no scene reset; not re-scored |
| 5 | Make the docs readable for a jury. Move the three sprint preambles of EXPERIMENTS.md below §0, add a one-screen current-results summary at the top, and fix the stale lines in EVALUATION.md, EXPERIMENTS.md §3b and CAPTAIN.md. | 8.5, 8.7 | P1 | 1–2 h |
| 6 | Make one narrated 2–3 minute video: the Docker chain, the main shot, one synthetic long-range approach. | 8.8, §7.2 video | P2 | 2–3 h |
| 7 | Run set F on straight track with independent placement (an axis surveyed from the near rails), so that the range numbers do not rest on the detector's own far model. | 8.2 | P4 | 2–3 h |
| 8 | At 360°, drop the points behind the train once the mount orientation is known, and skip the marker and corridor-cloud publishing when the node is behind. Check with `output_fingerprint.py` and re-time. | 8.3 | P3 / P1 | half a day |
| 9 | Station and platform-end false alarms: 25 of the 27 STOP episodes on the five recordings, and the station pieces of the ride. Needs a station-aware corridor or a longer confirmation where the rails are lost, then a full re-run. | 8.1, 8.4 | P3 | 1–2 days |
| 10 | If the organizers say that bed objects count: build a discriminator for the near-bed path (it now raises 667 ride events), for example an object that stands above the local template in consecutive frames and approaches at the train speed. Re-measure on all data and on set F. | 8.1, 8.2 | P3 / P4 | 2–3 days, uncertain |

**P4 follow-ups after this review (24.09, not re-scored).**

* Item 7 (done, synthetic): set F was re-run in pairs, the detector's far axis against a
  placement anchored on the near rails ([`P4_AUDIT.md`](P4_AUDIT.md)).
  * On the straight set of round 3, a person is first confirmed at a median 154 m anchored
    against 150 m legacy (5 approaches), so the ~148 m figure does not rest on the detector's
    own far model.
  * On seven curve and edge scenes, neither mode matched anything beyond 100 m.
  * A surveyed reference still does not exist.
* The organizers' own synthetic-obstacle recording (`cloud_with_fake_obj`) is now labelled
  exactly and graded per object ([`P4_AUDIT.md`](P4_AUDIT.md) "Organizer synthetic-obstacle
  recording"). It is the first positive set made by the tool that is part of the hidden check.
* For item 1: none of its ten test objects lies on the bed between the rails.

Optional, low priority by the team's decisions: a saved Docker image (the stand has internet)
and a decision-log slide (the pitch stays focused).
