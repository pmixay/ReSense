# Criteria judgement (spec §8) — v0.6.3, 23.09

**How this was judged.** Two reviewers with no stake in the work each read the whole repository
against the organizers' criteria: the technical specification §8
([`organizers/technical_specification_case05.txt`](organizers/technical_specification_case05.txt)),
the Q&A session and the written answers of 23.09 ([`organizers/answers.md`](organizers/answers.md)).
Reviewer A judged the results (8.1–8.4) and reviewer B the engineering, the launch, the method
and the pitch (8.5–8.8 and the §7.2 deliverables). Both were told to distrust the team's claims.
Reviewer A re-ran the evaluations on the frame cache. Reviewer B built the image and ran the
organizers' procedure on rebuilt real bags: the node container, then `ros2 bag play` as a normal
user from another container. Their reports: [`reviews/`](reviews/).

This is the third round:

1. The first judged v0.6.1.
2. The second judged v0.6.2 in the morning of 23.09.
3. This one judged commit `fcbb3f8` in the afternoon.

The team then checked every finding. Each verified finding was fixed or is listed under "What is
left". The fixes went out as v0.6.3 (commit `c1c2b6a` and before it). The scores below are the
reviewers' own for `fcbb3f8`. The last column is the team's estimate after the fixes; no one has
re-reviewed those numbers.

## Scores

| § | criterion | v0.6.1 (1st round) | v0.6.2 (2nd) | **`fcbb3f8` (3rd, the reviewers)** | after the v0.6.3 fixes (team's estimate, not re-reviewed) |
|---|---|---|---|---|---|
| 8.1 | **Works** (the main criterion) | 5 | 6 | **6** | 6.5: STOP no longer flickers; the object on the rail 124 / 126; a person lying across the track kept |
| 8.2 | **Range** | 6 | 6 | **6** | 6: the numbers are now stated conservatively; the range itself did not change |
| 8.3 | **Speed** | 7 | 7 | **6** | 6.5: timing re-measured and the calibration made cheaper; 360° is still at the frame period on 4 vCPU; the i7 stand is not measured |
| 8.4 | **Generalisation** | 6 | 6 | **6** | 6: the start-frame dependence and the threshold margins are now measured; the tuning still shares the data |
| 8.5 | **Technical quality** | 7.5 | 8 | **7.5** | 8: CI green again; the acceptance scripts work as documented; stale docs fixed |
| 8.6 | **Ease of launch** | 6.5 | 7 | **8** | 8.5: a jury quick path heads the README; the dry-run checks pass as documented |
| 8.7 | **Team approach** | 9 | 9 | **8** | 8.5: false alarms reported for late starts, as the jury will run; margins measured |
| 8.8 | **Pitch** (lower weight) | 5 | 7 | **7** | 7: the Docker/RViz chain is on the demo slide; the videos are still silent |

The weights are not published. Counting 8.1 twice and 8.8 at half weight gives an indicative total
of **6.7 / 10** for `fcbb3f8` (6.4 for v0.6.1).

### What the scores rest on

**8.1: 6.** Reviewer A reproduced these from the per-frame outputs:

- the real crossing person in 58 of its 61 envelope frames, first STOP 0.3 s after it enters, distance error ≤ 0.23 m;
- the organizers' object on the rail, 121 of 185 frames by its own detection (v0.6.3: 127, and 124 of the 126 after the person leaves);
- 20 false events on the five empty recordings and 47 on the 13 km ride (3.6 per km).

What holds it down:

- **Nothing on the bed between the rails is reported, by policy.** A 0.5 m box or a dog-sized box is found in 1 of 6 approaches (set F). The organizers named "animals thrown on the track".
- **False stops remain:** 39 STOP episodes on the 20-minute ride with v0.6.3, one every ~30 s on average. The largest cause is corridor-edge structures, 18 of the 47 events.
- **A 3 cm hanging cable is found late:** first at 95 m, held only from ~50 m.

**8.2: 6.**

- A person on straight track is held in every 10 m band from 115 m inward. That is the median of 6 approaches; per approach it ranges from 20 to 160 m.
- A person is first confirmed at 148 m; with the train speed, at 167 m.
- Small objects on a rail head are found from 42–47 m.
- In R ≈ 350 m curves the range is 58–86 m, the sightline.
- 300 m is impossible: no return lies beyond 210 m.
- 14 of the 47 ride events start beyond 100 m, which is what the far-field rule costs.

**8.3: 6.**

- CPU only, one core, 186 MB.
- Detector: 42–64 ms mean, p95 53–78 ms on every recording (re-measured for v0.6.3).
- At 360° through ROS on 4 vCPU the node runs at the frame period and skips frames: 7–10 fps.
- The i7-9700E stand is not measured.

**8.4: 6.**

- No map: the model of the tunnel is rebuilt every frame and the mount is found from the data.
- The one real out-of-sample result: v0.5 alarmed on 3.2 % of the ride's frames against 4.2 % on the bags it was tuned on.
- About 15 hand-tuned infrastructure rules, and no held-out data with obstacles.

**8.5: 7.5.**

- A pure-Python library, a thin ROS node and one parameter file checked by CI.
- 150 tests at the reviewed commit (152 at the v0.6.3 base; 166 on the P4 audit branch), and ruff is clean.
- Guards: watchdog, `FAULT` / `NO_INPUT` / `STALE`, a reset after errors.
- Input switching was verified by the reviewer with both topic / frame pairs.
- Held down: CI was red at `fcbb3f8` (a stale web test), and false alarms depended on the start frame.

**8.6: 8.** Reviewer B ran the organizers' chain as written:

- the node on the image's default command;
- `ros2 bag play` as uid 1000 from another container, with the image's DDS profile and with stock Fast DDS;
- `STOP` at 55.8–56.5 m.

Held down:

- the first 2–4 s of every played bag are lost;
- the team's acceptance scripts failed as written;
- the jury path started at line 170 of the README;
- no prebuilt image.

**8.7: 8.**

- Ten methods compared, with the rejected ones kept.
- A learned second opinion was dropped after a leakage check.
- False alarms are counted by cause, with a leave-one-out check, and every number is marked real or synthetic.
- Held down: the evaluation always started at frame 0, all long-range positives are synthetic, and ~3 700 lines of docs.

**8.8: 7.**

- 15 slides in the organizers' template; slides 7–11 match the template. The team has four members, so the fifth card of template slide 9 is removed.
- The arc is clear and the main shot is strong.
- Held down: the four videos are silent, nothing beyond 100 m is shown visually, and some slides are dense.

## What the reviewers found (`fcbb3f8`) and what was done

Every finding below was re-checked by the team before acting on it.

| # | finding | checked | action |
|---|---|---|---|
| A3 | The mount calibration measured every frame until it froze. That cost 10–15 ms per frame for the first ~20 s of every recording, which is a whole short control bag. | confirmed by timing | **fixed (v0.6.3):** frames between two spaced observations are no longer measured, and a tilt is applied from 0.75° (1.5× the p90 noise). Decision and distance are identical on all 13 759 frames, and the re-mount check (EXPERIMENTS §6) gives the same residuals. |
| A2 | The README quoted the v0.6 timing (42–58 ms). The current code was 25–33 % slower. | confirmed | **re-measured:** 42–64 ms mean, p95 53–78 ms (EXPERIMENTS §3). |
| A10 | The decision flickered: a confirmed obstacle missed in one frame gave `GO` for that frame. | confirmed | **fixed (v0.6.3, `hold_misses` = 1):** STOP episodes 88 → 66 on the obstacle-free data, events unchanged, alarm frames 245 → 311, the object 118 → 124 of 126 (EXPERIMENTS §0). |
| B4 | False alarms depend on the frame processing starts from. Through ROS the first 2–4 s are lost. | confirmed offline | **measured:** `scripts/start_offsets.py` gives 14–20 events on the five bags for starts 0–40; frame 0 is the worst case in total. The object is found from every start, the person ~1 s later. The cause, a trackside device at ~50 m confirmed from some starts, is not fixed: a stricter hit fraction for low tracks only partly helped and was not kept (item 10 below). |
| — | (the team, from reviewer A's lying-person run) The low-object width cap (1.6 m) rejected a person lying across the track. | confirmed | **fixed:** the cap is 2.2 m (the envelope's width), identical on every real frame; a lying person 2 → 6 of 6 approaches on a shallow bed (EXPERIMENTS §2d). |
| B2 / B3 | `dry_run.sh` defaults (`--max-dropped 0`) could not pass: the start-up hole counts as dropped frames. The README said `--delay 3` prevents the loss. | confirmed | **fixed:** drops are counted after `--settle-s` 5 s. The 120° recording now passes with 0 steady drops; the 360° one still fails on 4 vCPU, for CPU. The `--delay` claim is corrected. |
| B9 | `console_test.sh` defaults fail on a clear recording played first. | confirmed | **fixed:** `--obstacle-in`, with the usage for the real recordings in the script. |
| B1 | CI red at `fcbb3f8`: a web test still expected best-effort RViz displays. | confirmed | **fixed** in `fa81206`. The RViz raw-cloud displays read reliable (the recording showed best-effort ones lose the played clouds). |
| B5–B8 | Stale statements: `--ipc=host` "shared memory" (the image runs UDP), SUBMISSION "pending (28.09)", the Dockerfile pointed to a missing README section, the README pointed the jury to an old self-assessment. | confirmed | **fixed** (this file replaced). |
| B10, B11 | `CAUTION` covers 10–64 % of an empty recording's frames and is not explained; `obstacle_detected` is `false` during `FAULT`. | confirmed | **documented** in the README quick path and "What to look at": `CAUTION` is advisory, `/resense/decision` is the go / no-go signal. The semantics are unchanged. Filtering classified infrastructure out of `CAUTION` would remove at most half of it (measured per recording). |
| B12 | The dashboard's live mode is advertised "via rosbridge", but the image has no rosbridge and roslib comes from a CDN. | confirmed | **fixed** wording (web/README, README, ARCHITECTURE, slide 10). Foxglove, whose bridge the image has, is named for an offline stand. |
| B13 | Template slide 9: 5 cards became 4. | checked | **kept:** the team has four members. |
| A1, A8 | The range headline was a median without its spread. "Crate 182 m with speed" hid the loss of steadiness. The cable at 95 m was a first hit only. | confirmed | **fixed:** per-approach spread (20–160 m), the speed trade-off (crate held from 89 instead of 117 m), and the cable held from ~50 m are now in the README. |
| A4 | A set F dropout was blamed on "the near-range bed fit". | confirmed: a 3.4 s hole in `new_data_169` | **fixed** (EXPERIMENTS §2d). |
| A6, A7 | The bed depth ("0.44 m") and the object's height disagree with the stored runs and the labels. | confirmed | **fixed:** bed 0.26–0.34 m below the rail head beside a 0.57–0.60 m trough. Object top 0.13 m after the mount calibration against 0.17 m in the labels, which are measured before it. |
| A9 | "8–10 fps" at 360° through ROS; the dry-run log shows 6.8–8.3. | confirmed | **fixed:** 7–10 fps. |
| A5 | Set F places the objects on the detector's own track axis, so an axis error never moves them out of the corridor. This flatters the curve and edge sets. | confirmed from the code; the size of the effect is not measured | **open** (item 4 below). |
| B (8.8) | The demo slide showed screenshots, not the Docker / RViz chain. | agreed | **fixed:** a frame of `video/docker_chain_rviz.mp4` is on slide 10. |

Re-verified on the final code (v0.6.3, full runs over all 13 759 frames, per-frame outputs
compared):

- the person 58 / 61 from frame 11;
- the object 127 / 185;
- 20 and 47 events;
- the width cap and the calibration change are identical frame for frame to the runs before them;
- 166 tests on the P4 audit branch and 6 dashboard tests pass, ruff is clean, and the parameter files are in sync.

## What is left (by expected gain per hour)

Out of scope at the owner's request: the run on the jury's i7-9700E stand, and sending the three
open questions ([`QUESTIONS.md`](QUESTIONS.md)). The owner merges the branch to `main`.

**Detection (8.1, 8.2, 8.4)**

1. **Station and corridor-edge false alarms.** 15 of the 20 empty-bag events come from
   `squareT_platform_squareT_switch` (the platform-end structure). On the ride, corridor-edge
   structures are the largest cause: 18 of 47 events. The fix is a station-aware corridor (the
   platform edge is found from the geometry) or a longer confirmation where the rails are lost.
   1–2 days with the full re-evaluation. The largest remaining gain on 8.1.
2. **Objects on the bed between the rails** (a dog-sized box: 1 of 6). This needs an opt-in
   near-range rule: ≥ 0.3 m wide and tall, within ~30 m, where the bed template is dense. Measure
   its false-alarm cost on the ride first, because a bump-above-the-bed rule once raised
   1 482 events (EXPERIMENTS §1d). 3–4 h plus a full run. It is a policy decision as much as a
   technical one.
3. **A far height reference anchored on the tunnel vault.** Small objects cannot alarm beyond
   ~100 m, and 14 of the 47 ride events start beyond 100 m. 1–2 days, some risk. Moves 8.2.
4. **Set F with independent placement** (A5): `--placement-mode legacy` remains the default
   for reproducing the historical frame-axis method; `--placement-mode anchored` uses a near
   rail reference, while `--placement-mode independent` takes an externally surveyed axis.
   The paired selected curve/edge run is complete: six usable approaches per kind and one
   recording-gap skip; no visible synthetic person or box was matched in the 100–150 m bin
   in either mode. The near reference uses estimated speed and track registration, so it is
   not surveyed ground truth ([`P4_AUDIT.md`](P4_AUDIT.md)). The organizers' new fake-object
   recording has no injection manifest: P4 can process it, but cannot score true/false events
   independently until the organizer supplies labels.
5. **Start-frame robustness of the low stage.** The trackside device at ~50 m in `roundT_doubleT`
   is confirmed from some start frames: its low and corridor hits are chained into one track.
   Look at the association between the two stages. Half a day.

**Launch and transport (8.3, 8.6)**

6. **The DDS start-up hole** (the first 2–4 s of a played bag): try the Fast DDS
   reliability and heartbeat settings and a deeper reader history. 2 h of research.
7. **A saved image** (`docker save | gzip`) with `docker load` instructions, for a test stand
   without internet at build time. 1 h, hosted outside git.
8. **Tilt calibration for short bags.** The final tilt needs 20 s; a short control bag with a
   1–2.5° tilt is never corrected. Half a day.

**Pitch (8.8)**

9. **A narrated 2–3 minute video:** the Docker chain, the main shot and a synthetic person
   confirmed at ~148 m. Lighter text on slides 5, 13 and 15. 2–3 h.
10. **A one-page decision log** (hypothesis → experiment → result → decision) and a "what failed"
    slide drawn from EXPERIMENTS §7. 1 h.
