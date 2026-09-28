# P2 criteria completion — 28 September 2026

> **Owner:** P2 · **Base:** `main` at `8f23284`, including the accepted 27.09 detector
> **Working branch:** `testovaya-gpt` (tracks `origin/testovaya-gpt`)
> **Status:** public PPTX/PDF/MP4 rebuilt from the corrected sources on 28.09; local private preview uses the supplied roster and portraits. City, team formation, group photo, on-device demo and human rehearsals remain pending.

The previously reviewed P2 work was on `f6b156b`. Its remote Claude branch has since been
deleted. Current `main` contains a newer detector (`352ca13`, measured at `d572807`), so the
reviewed client fixes were ported onto **current main** and the public PPTX/PDF/video were rebuilt
from the current regression baseline instead of publishing an obsolete deck. Another contributor
removed a draft GitBook/Pages site from the Claude branch during this review; that removal is
preserved. The P2 instructions and freshness limitations are in `web/README.md`.

## Criteria and evidence

| Organizer requirement | P2 work and evidence | What remains |
|---|---|---|
| §4: Docker → supplied bag → raw cloud → detection → distance; preferably live | RViz config and Foxglove layout include both known raw-cloud topics, corridor and boxes; archived full Docker/RViz chain in `docs/video/docker_chain_rviz.mp4`. Foxglove channel and freshness protocol tested; browser's actual bundled roslib tested across subscribe, STOP, expiry, recovery and disconnect. The two-container viewer probe is enabled on this Claude branch. | On the actual demo machine, P1/P2 must import and visually inspect the layout from a **second device** while playing a supplied bag; test link loss/recovery. The archived recording is earlier detector evidence, not a new run of the 27.09 detector. |
| §5, §7.2: short algorithm video and accessible documentation | Public 2:50 H.264 overview and `.srt`, 16-slide PPTX/PDF in the organizers' template, updated interface screenshots, label-tool and replay instructions. The viewer can see data provenance (real bag vs organizer synthetic vs our synthetic). | Captain supplies submission links; optional narration is the speaker's choice. |
| §8.5: robustness, tests, honest documentation | Live valid/current contract, STOP hold, stale overlays, reporting v2, label import and numeric validation, rendering and Foxglove split-advertisement checks. Browser tests cannot silently skip in CI. Detector seal checked separately; this pass does not change detector/config. | ROS runtime and physical rendering on the jury stand require the demo setup. |
| §8.6: easy launch | `web/README.md` gives offline replay, browser validation and live Foxglove procedure. Existing `scripts/play_bag.sh` and Docker CI are owned by P1 and remain the supported jury path. | P1/demo operator checks the final image and supported read-ahead procedure on the actual machine. |
| §8.7–8.8: explain approach, trade-offs and show results in a few minutes | Deck speaker notes, 16-slide public deck, 2:50 overview and narration script distinguish in-sample from cross-fitted estimates, known misses/false events and the 27.09 reference change. Removed claims of arbitrary mount support, ready-made braking integration, unmeasured competing-model AP and unseen external evaluation. | Captain/team provide private names/portraits/city/team history; build the private deck; conduct two timed team rehearsals. Public slides 2–3 show the roles P1–P4 (no `<…>` fields since 28.09 evening). |
| §8.1–8.4: detector quality/range/speed/generalization | P2 visualizes and cites the **current** accepted regression numbers, including 61/61 real person frames, 32 in-sample and 37 cross-fitted ride events, set O edge ranges 35/18 m and the blind spots; since 28.09 evening also the node-path figures (object on the rail STOP in 123 of 126 frames with one GO; latency with its machine). | P3/P4/P1 own new algorithm changes and accepted measurements. Do not silently alter public claims until their gate and evidence change. |

## 28.09 evening: fixes after the fresh re-judgement

Two independent judges re-scored the branch on 28.09 ([`rejudge_2026-09-28.json`](../docs/evidence/results/rejudge_2026-09-28.json)).
Every finding about the deck, the video and `docs/PRESENTATION.md` is fixed in the sources
(`scripts/build_deck.py`, `scripts/make_overview_video.py`, the `.srt`, `docs/PRESENTATION.md`):

* **Speed with its machine.** «18–23 мс на кадр (p95 ≤ 33 мс …)» came from a 27.09 sandbox whose
  CPU was not recorded and did not reproduce on the judges' 4-vCPU Xeon 2.1 GHz (P2 re-ran
  `resense bench` there: 360° mean 31.4 / p95 47.1 ms, 120° 24.6 / 36.8 ms). The slides and the
  video now give the end-to-end p95 through ROS with the machine: 87–118 ms (360°) and 54–64 ms
  (120°) on that Xeon, 60 / 37 ms on the CI runner (CI run 36397511351, read from the job log).
* **Object on the rail.** 125 of 126 was the offline replay of the 1 cm cache; through the node (and
  offline on the original recording) STOP in 123 of 126 frames, GO at frame 111, CAUTION at 117 and
  197 (counted by P2 in the four full node captures of `docs/evidence/node_input_2026-09-28`).
* **Outside box in set O.** «6 ложных STOP» → 9 frames (563–571, 126–142 m) with a STOP detection on
  it, offline and through the node; `scripts/score_fake_objects.py` credits 7 on those runs (two
  detections 2–3 cm beyond its 1 m tolerance), 6 on the gate's cache.
* **The opinion's delay** is at most 10 processed frames per track (`tracking.doubt_extra_hits`):
  ~1 s at 10 Hz, ~2 s at 5 Hz, longer during a catch-up — not «≤ 1 с».
* **Tests** «731» → «750+» (753 passed on the host on 28.09).
* **Team slides** show P1–P4 and what each owns; the build refuses any deck with a `<…>` field.
* `docs/PRESENTATION.md`: one status, the current numbers with their sources, the build; the
  dated rebuild records moved to its archive section.

The committed PPTX, PDF and MP4 were rebuilt from these corrected sources on 28.09 using the
commands in `docs/PRESENTATION.md` «Сборка». Their sizes, SHA-256 hashes and media properties are
recorded in [`demo/evidence/p2_criteria_2026-09-28.json`](demo/evidence/p2_criteria_2026-09-28.json).

## Corrections from the full client audit

* Live `valid: true` is insufficient: require frame snapshot, matching mode/clock, current reason,
  queue/catch-up and age bounds, non-held status and consistent health. Contradictions cannot
  release a held STOP. Both cab and plan views cover stale data; cab range respects the published
  `clear_distance` cap. Replay and live controls cannot cross-write, including a delayed file read.
* Report schema v2 calls consecutive STOP runs **`stop_episodes`** instead of `alarm_events` (the
  evaluator uses the latter for distinct confirmed track IDs). Exclude watchdog/error snapshots
  from frame metrics and count them as `status_snapshots`; do not export an old replay report in
  live mode. The banner/card/log/report derive offline decisions consistently.
* The label tool requires absolute bag frame indices, treats a valid new results file as a new
  recording, serializes file selections, rejects invalid numeric edits and preserves imported
  evaluator metadata/extra fields. Keyboard frame selection and phone-width table scrolling work.
  Draw the strict ±1.05 m envelope separately from the ±1.4 m advisory limit and rotate
  box/plank labels in the top view.
* The Foxglove probe waits for all required channels even if advertised in batches. Stock
  Foxglove indicators say **LAST**: their values do not expire on a disconnected viewer; read the
  connection and `/resense/status` or use the expiring web dashboard. Hero renders use node-equivalent
  STOP/FAULT/CAUTION/GO precedence and refuse a missing requested frame.
* Overview excerpts now clip and rebase SRT/chapter timestamps. The rebuilt public deck retains
  the latest detector's measured numbers and clearly states that braking integration is future
  work and the organizer objects are synthetic on previously used backgrounds. The overview
  identifies earlier v0.6.2/0.6.3 picture clips as archival: current metrics come from the
  27.09 gate, not from replaying the new detector in those pictures.

## Repeatable checks and limits

```bash
RESENSE_REQUIRE_WEB=1 python -m pytest -q -rs web/demo tests/test_overview_video.py
python -m pytest -q -rs tests
python scripts/detector_freeze.py verify
ruff check .
python web/demo/check_status_compatibility.py --out out/p2-review-status-compatibility.json
mkdir -p out
gzip -dc docs/evidence/docker_2026-09-23/obstacle_status.jsonl.gz > out/p2-review-real.jsonl
python web/demo/check_dashboard.py --jsonl out/p2-review-real.jsonl \
  --speed 2 --min-dist 55 --max-dist 57 --screenshot out/p2-review-real.png
```

* Current verification on `testovaya-gpt`, 28.09: **83 P2 checks passed with Chromium and no skips**;
  **753 core tests passed**, one ride-dependent test was deselected because `/data/cache/new_data`
  is absent, and six subtests passed. Ruff 0.15.8, parameter synchronization, video consistency,
  whitespace checks and the 31-file detector integrity seal pass. The detector seal does not replay
  recordings.
* The shared browser validator accepted **4,760/4,760** archived records across **18** gzip files.
  It also accepted **982/982** statuses in **4** supported-playback capture files, including
  original-bag status streams.
  Real replay smoke accepts **103** archived status frames, observes STOP at **56.1 m**. These
  establish UI compatibility with archived data, not detector recall on unseen data.
* Public PPTX/PDF were rebuilt from the organizer's 37-slide template: **16 exported slides**.
  The 2:50 video is **1920×1080, 25 fps**, H.264, silent with burned-in and sidecar subtitles;
  the refreshed dashboard clip is 7.24 s. Exact hashes, sizes and commands are recorded in
  [`demo/evidence/p2_criteria_2026-09-28.json`](demo/evidence/p2_criteria_2026-09-28.json).

The ignored private folder now contains a local draft made with the supplied roster and portraits;
it is not committed. City, team formation and team photo are still missing. The remaining device
import, human rehearsals and physical stand run cannot be marked complete from this checkout:
`/data/for_hackathon` and a second physical viewing device are absent. The existing CI's two-container
protocol check is not a visual Foxglove import. Optional narration was not supplied. The internal independent
scorecard's 72/100 is not an organizer score and is not changed by this presentation work.
