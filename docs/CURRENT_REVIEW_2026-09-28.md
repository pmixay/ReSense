# Current project review — 28 September 2026

**Current assessment: 69/100, unchanged after the additional work.**

Reviewed branch: `gpt-score-push-20260928`. Reviewed source:
`20e82297bbf859e7d63bee35044d6c8314f746c5`, including both development commits after the previous
69-point review. The review commit adds documentation and evidence; it does not change the detector.

This is an internal engineering assessment using the existing weights for the organizers'
[eight criteria](organizers/technical_specification_case05.txt). The organizers publish no
numerical weights. Three specialist agent reviews supported the lead review; all had access to
the earlier scores. This is a reassessment with fresh checks, not a blinded judging panel or an
official competition score. The earlier paired **66.5** on `806b6c4` and single-review **69**
on `a2f9122` remain dated records, not scores to average together.

## What the project does

ReSense detects obstacles inside a metro train's clearance envelope from 3D LiDAR. Its Python
library calibrates the sensor mount, estimates rails and tunnel geometry, selects points in the
envelope, finds low and hanging objects, clusters candidates and confirms tracks over time.
Optional C++ kernels accelerate the same calculations. A small learned track model can delay
suspected false alarms within configured limits.

The ROS 2 Humble node receives PointCloud2 and publishes obstacle presence, distance,
GO/CAUTION/STOP/FAULT, monitored range and diagnostics. Docker, a playback wrapper, RViz,
Foxglove and a browser dashboard provide the demonstration path. The repository includes
organizer specifications, recording labels, experiment outputs, regression tooling, tests,
CI, slides and videos. The strongest engineering work is the reproducible evidence and launch
tooling; the largest remaining gaps concern detection performance and unseen scenes.

## Scores

| Criterion | Current / maximum | Why |
|---|---:|---|
| 8.1 Functionality | **16 / 25** | Fresh raw-bag replay confirms the person in 61/61 labeled frames and the rail object in 123/126 frames from frame 75. Three STOP gaps remain. Recounted raw set O results are 414/801 visible inside object-frames; the cached full ride still has 32 false track events. |
| 8.2 Range | **7.5 / 15** | Raw set O first detections range from 18.3 m for the large edge box to 111.4 m for the overhead box. The small edge cube first STOPs at 35 m. Roughly 150 m person results use team synthetic objects, with no new real obstacle validation at that range. |
| 8.3 Speed | **8 / 10** | Native processing, optimized input and ROS playback are measured. Independent recorded 360-degree end-to-end p95 is 102 ms warm / 118 ms cold; a later CI runner achieves 62 ms cold. These are machine-dependent current-result figures; startup and dense ride sections can be slower. |
| 8.4 Generalization | **8 / 15** | Geometry, automatic calibration, rate/mount/start perturbations and multiple recordings provide useful evidence. No untouched real positive recording is available. The learned model's held-out ride figure is 37 events versus 32 in-sample; the new fixture is controlled synthetic data. |
| 8.5 Technical quality | **8 / 10** | Detector/source integrity, synchronized parameters, native fallback, tests and retained per-frame outputs are strong. Interacting rules, raw/cache sensitivity and some overstated evidence summaries keep this below full marks. |
| 8.6 Ease of launch | **8.5 / 10** | Docker defaults, offline load/rebuild checks, playback wrapper and stock DDS integration have evidence. Cold original-bag and remote-viewer checks passed on the earlier working branch. The score branch skips those extended checks; a public release archive and physical second-device rehearsal remain outstanding. |
| 8.7 Team approach | **9 / 10** | Hypotheses, rejected experiments, ablations and strict acceptance rules are recorded. The latest candidate was correctly rejected despite fixing the target example. Most experiments still reuse inspected data. |
| 8.8 Pitch | **4 / 5** | The 16-slide deck and 170-second video exist, match their artifact hashes and disclose synthetic results and limitations. Live rehearsal and private team details still need completion. |
| **Total** | **69 / 100** | **Change from the previous 69-point review: 0.** |

Switches receive the organizers' stated exception; the aggregate ride figures are diagnostic,
not an assumption that every switch alarm will be penalized. Objects wholly below the train
envelope are excluded. The organizers do not offer early access to the target stand, so its
absence is an uncertainty rather than a failed mandatory check.

## What the additional work achieved

**`d73af5a`: synthetic LiDAR fixture.** It adds 24 point clouds, 18 object masks, seeds,
hashes and a generator. All 42 artifact hashes and the generator hash check out. The scenarios
can support regression work, but the repository currently has no automated test or CI consumer
for this fixture. Its existence establishes neither improved detection nor performance on
new real tunnels.

**`20e8229`: raw rail-object continuity experiment.** Increasing `tracking.hold_misses`
from 1 to 2 restores the three missed STOP frames, taking the raw rail object from 123/126
to 126/126. It also increases cached ride alarm frames **130 → 150**, events **32 → 34**,
and false detections for three synthetic object types. Four enforced metrics regress, so the
candidate is rejected and the default remains 1. This is useful diagnostic work; it earns no
additional performance points. The experiment does not yet identify the point-filter or
association stage that loses the evidence.

`git diff a2f9122 HEAD` shows no changes to the detector, native kernels, production settings,
ROS node, Docker/CI or presentation artifacts. The engineering/process categories already
credit the established experiment discipline. Neither new commit justifies another half point.

## Verification and limits

Fresh verification records are kept in
[`evidence/current_review_2026-09-28/`](evidence/current_review_2026-09-28/).

- **Source integrity:** detector seal passes for 31 files; parameter copies match; Ruff passes.
- **Local tests:** 764 tests and six subtests passed in the full run; its only failure was the
  missing local cache frame `new_data_55_0013`. Rebuilding ride splits 55 and 56 from the local
  original DB3 files resolved it: the remaining test passed separately. Thus all 765 tests are
  covered by the full run plus that focused rerun, with no unresolved failures. The original
  failure log is retained; no test or detector code was changed.
- **Raw replay on this PC:** verified the original obstacle DB3 hash
  `05f1d7f7d1bbbc5e9453877416cc9f7367c19e31d35a5291271d863fc89c5ad9`; processed all 201 frames
  using current source and native kernels. Alarm flags, detections, warnings, nearest/clear
  distances and mount outputs equal the prior raw reference on every frame. Track-fit floating
  values differ by at most `1.34e-15`; timing and load-dependent health are not compared.
  The three remaining non-STOP frames are **111, 117 and 197**. Prior ROS captures identify
  these as GO, CAUTION and CAUTION respectively. This local run is offline, not a new ROS run.
- **Recounted retained outputs:** five empty raw recordings total 23 alarm frames / 8 track
  events / 7 STOP episodes. Raw set O gives 414/801 inside object-frames and 7 outside false
  STOP frames using the repository matcher. Its independent matcher counts 9 outside frames.
  The full cached ride remains 11,271 frames / 130 alarm frames / 32 events / 31 STOP episodes.
  Recounting saved output is not replaying those recordings again.
- **Gate accounting correction:** recomputation gives **146 enforced rows**, all unchanged,
  plus 62 unchanged informational rows and 16 changed informational latency rows. Earlier prose
  incorrectly called the JSON's `same: 208` count "208 enforced metrics". The summaries are
  corrected; the recorded gate result remains PASS. The four candidate failures also reproduce.
- **New fixture smoke check:** 302 controlled synthetic frames were processed. One missing
  target-return frame retains STOP; a second consecutive miss releases it. The clear and
  single-frame transient scenarios do not alarm. Repeating the far survey scans confirms both
  box sizes at 50 m, neither at 75 or 100 m. This is a diagnostic run on designed sequences,
  not a new range benchmark or evidence of real-scene transfer.
- **Exact reviewed source CI:** all four jobs passed in
  [run 36453635491](https://github.com/pmixay/ReSense/actions/runs/36453635491).
  The workflow's `FULL` branch list excludes this score branch: original-bag cold replay and
  the separate-container viewer probe are inherited evidence from
  [run 36432860933](https://github.com/pmixay/ReSense/actions/runs/36432860933).
- **Delivery and pitch:** all ten artifact hashes in the P2 manifest match; actual slide text
  and video metadata were inspected. GitHub returned zero published releases when checked
  during this review. The current branch's archive upload step is also excluded by its branch
  list. These checks do not establish a final stand or human rehearsal result.

The raw replay used an i7-8565U laptop, Python 3.10.12, NumPy 1.26.4, SciPy 1.13.1 and
scikit-learn 1.5.2 in an isolated Docker review container with current source installed.
Concurrent checks ran, so its elapsed time is not used to revise the speed score. This review
does not repeat the full detector gate, every ROS playback or all robustness experiments.

## What would justify a higher score

1. Fix the raw rail-object gaps with a targeted change that passes the full false-alarm and
   range gates, then verify it through ROS.
2. Demonstrate earlier, sustained detection for edge/small objects while holding outside-object
   false alarms steady. Evaluate new placements and an untouched real positive recording if one
   becomes available.
3. Reduce ride false alarms with a genuinely held-out check and distinguish switch events from
   platform/open-tunnel events.
4. Retain the final runnable image, run the extended checks for the delivery source, and complete
   the human demonstration. Further documentation alone should not raise detection scores.
