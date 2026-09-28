# Work before a final detector freeze

## Current implementation handoff — 28 September (`a2f9122`)

The current single-review internal estimate is **69/100** on `a2f9122`; the latest paired score
remains 66.5/100 on `806b6c4`. The detector categories did not rise in the single-review update.
The frozen detector still has 123/126 STOP frames on the raw rail-object recording, including a
GO at frame 111 and CAUTION at 117/197; the full ride has 32 alarm events and 31 STOP episodes;
set O has 411/801 visible in-envelope STOP frames. Registered threshold candidates A/B/C made no
scored output change and must not be repeated as a sweep.

The raw `doubleT_obstacle` DB3 is not present in the local data directories. The 1 cm int16 cache
does **not** reproduce the raw dropout: a traced cache replay returns STOP at frames 111, 117 and
197. Therefore its point/stage history cannot validate a fix for the raw recording. Obtain the
original bag or equivalent unquantized frames plus tracker history before changing the continuity
or straddle logic. If that data is unavailable, retain the shipped detector and document the miss.

Next work, in order:

1. Trace raw frames 108–119 and 194–199 through geometry, candidate rejection, association and
   hold state. Test one continuity fix only if the raw trace identifies a bounded cause. Preserve
   all 61/61 person frames and improve the 123/126 rail-object STOP count without harming other
   positives or empty recordings.
2. Trace platform/switch false STOP events in the full ride to exact supporting points and
   detector stages. Change one causally implicated rule at a time; reject any reduction that
   creates a missed positive or weakens monitored coverage.
3. Trace small/edge object geometry and evidence across frames in set O. Do not repeat A/B/C's
   threshold changes; pursue a candidate only when a different causal mechanism is demonstrated.
4. Before accepting any behavior change, compare original-bag node playback, all six recordings,
   set O under both matchers, the full ride, strict regression gate, processing-history stress,
   altered frame rate and mount tilt, clear-distance claims, and latency. Keep before/after outputs
   and reject or document every regression.
5. Rescore only after a candidate passes acceptance. Keep 69/100 unchanged until a reviewer scores
   the accepted exact commit. Without an untouched real-obstacle route, new-scene generalization
   remains uncertain; synthetic holdouts measure sensitivity only.

The two-device Foxglove simulation is complete in CI, but physical second-device import, city/team
formation/group photo and timed human rehearsals remain delivery tasks. Synthetic evaluation cannot
replace new real-obstacle data for the generalization criterion.

**Historical update 27.09:** the [27.09 quality cycle](QUALITY_CYCLE_2026-09-27.md) shipped and sealed a new
reference detector ([`DETECTOR_FREEZE.md`](DETECTOR_FREEZE.md)), revised after an independent
review: ride 45 / 38 → 32 / 31 false events / STOP episodes in-sample (37 events on ride pieces
the opinion never saw), edge cube first STOP 5.2 → 35 m,
GO overclaims 46 → 16, the captured history-dependent clear-run STOP gone. Open next steps (from
its limits section): real positives for the track opinion (its 2× margin is on synthetic
ones); small objects low on the bed between the rails; objects just inside the envelope edge
beyond ~35 m; organizer Q1 (rails or sensor axis), on which the union reference's gains
rest; the far-evidence tracks whose sparse early hits delay confirmation (set F 1 m box −2 frames
at 83–85 m); the 16 remaining GO overclaims; the standing-train platform STOPs that dominate the
history stress. Release publication remains on hold. The text below is the record of 26.09.

Status (26.09): the registered quality cycle and its follow-up diagnosis/T1 experiment are complete;
final detector acceptance and release publication remained on hold. See the
[quality-cycle results](QUALITY_CYCLE_2026-09-26.md).

## 26 September status (historical)

- Node and dashboard freshness are implemented: explicit live/replay clocks, bounded source and
  residence age, invalid-range suppression, consumer expiry, STOP retention and valid recovery.
  All 15 stock Humble/Fast DDS functional checks pass. Freshness establishes the age of evidence;
  it does not establish that the monitored region contains no undetected obstacle.
- Missed-object tracing, all 45 ride false-target histories, all 72 placement cases and the
  exact clear-failure diagnosis are complete. Fourteen ride targets remain physically unresolved.
- M1, A1 and D1 were evaluated and rejected. M2 passes its offline gates but remains unmerged:
  the combined image fails the registered standalone clear-bag zero-alarm criterion.
- T1 completes the causal follow-up. It removes the two traced clear-sequence false STOPs, but
  range retention falls to 50% on one ride segment and 93.4% on a platform/switch recording,
  below the required 95%. T1 is rejected; no replacement detector is accepted.
- Earlier P3d plus freshness code `d480b1330491da838d6fb4996e34e37b3c060915` passes all six jobs
  in [CI run 36275557220](https://github.com/pmixay/ReSense/actions/runs/36275557220), including
  loaded runtime native-kernel assertions and synthetic replay with required freshness.
  Local download, checksum, offline loading and source/native verification pass
  ([receipts](evidence/results/quality_delivery_2026-09-26/README.md)); the previous local image
  is restored. Public publication remains prohibited.
  [Captain checklist](CAPTAIN.md#4-current-completion-and-remaining-actions).

## Further development proposals from 26 September (historical)

The current registered experiments are closed. Any next candidate needs a new bounded proposal,
preregistered acceptance checks and independent review. Remaining goals are:

- Resolve known GO/range overclaims without excessive uncertainty or loss of useful range.
  The baseline detector retains 46 GO overclaims in the existing diagnostic.
- Improve sustained edge/small-object detection while preserving positives and background gates.
- Reduce ride false events from the baseline's 45 toward the registered target of 30
  or fewer, and resolve the reproduced standalone clear failure without sacrificing coverage.
- Obtain the organizer's Q1 envelope-reference decision. Axis union remains off. The user has
  confirmed that no additional untouched real-obstacle recording is available; known-bag tests
  remain development validation.
- Rejudge an accepted improvement against the quality criteria. The current provisional
  independent aggregation is 64/100; the 75/100 target remains unmet.

Public archive delivery, approved team information/photos, human rehearsals and the captain's personal
submission remain on the [captain board](CAPTAIN.md#4-current-completion-and-remaining-actions).

## Original priority and evidence, before this cycle

The proposal below is retained as the starting record. Its freshness observations describe the
earlier node, before the implemented controls; its proposed work is not an ongoing task list.

1. **Decision freshness and uncertainty.** The final loaded cold capture contains 27 catch-up
   rows, including three GO decisions. The first reports healthy input and 196.8 m monitored
   range. `node.catchup` is telemetry; the decision ignores it. The watchdog measures elapsed wall
   time since processing, not acquisition age. The log reaches 5.6 s behind the newest queued
   recording stamp, but per-row acquisition age is unrecorded: do not assign that maximum to
   each GO. Define replay/live clock handling, queue age and validity before changing the policy.
2. **Missed obstacles can coexist with apparently useful monitored range.** Frozen cache replay
   overclaims known rail-envelope objects in 54/505 object-frames, 46 with GO. At frame 303,
   the small central object is at 110.12 m with two in-envelope returns, GO and range 133.6 m.
   The cap depends on surviving clusters and excludes columns. UI wording now says estimate;
   the algorithm still needs explicit uncertainty behavior and bounded loss of useful coverage.
3. **Edge, small and elevated obstacles remain late or unstable.** Organizer edge objects have
   2/83 and 6/125 STOP frames, starting at 5.2/10.3 m; cubes start at 42.7/52.5 m, thin hanging
   object at 30.1 m. Q1 (sensor versus rail reference) is unresolved. Hard geometry and shape
   rules can demote or remove evidence before temporal confirmation. Trace each failure before
   changing a threshold; do not infer that axis union fixes every cause.
4. **False STOPs remain frequent.** The ride has 45 events/38 STOP episodes over about 13 km;
   five empty recordings have 13 events. Near-sensor scene labels do not identify the false
   target or its cause. Review and classify the distant alarm points through time.
5. **Generalization evidence is weak.** Real positives come from a stationary-train recording
   around 56 m. The moving ride contains no real obstacles. The 72-case synthetic study finds
   matches in 45 cases and 544/2,458 visible frames, with zero target matches in paired controls.
   Backgrounds and source shapes were seen; placement lacks surveyed envelope truth and aligned
   source/destination motion. This exposes sensitivity, not real holdout recall. The user has
   confirmed no additional untouched real-obstacle recording is available.

## Original proposed work order

- P1: specify and test result freshness, including startup backlog, later stalls, pauses,
  clock jumps and input switching. Preserve STOP priority. Non-current results must not silently
  carry GO as an actionable current result. Publish enough timing information to verify this.
- P3/P4: trace missed object points through corridor membership, infrastructure removal,
  clustering, advisory reasons and tracker confirmation. Build an independently checked diagnostic
  set with object visibility, intended/reference envelope and rejection reason per frame.
- P3: test one general change that retains obstacle evidence while representing uncertainty in
  rail/height estimates and infrastructure classification. Keep candidate development separate
  from acceptance evidence; avoid fixes selected solely for one failed organizer object.
- P4: score raw bags and quantized caches, paired controls, sustained STOP distance, longest miss,
  false STOP events/episodes and extra CAUTION exposure. Re-run rate, mount and start-offset tests.
  Further tests on known bags remain development validation; reserve any future new real sequence
  untouched for a once-only final evaluation.

## Original proposed exit checks

These are suggested engineering gates, not organizer promises or measured achievements:

- Existing full regression gate passes without waivers; preserve current real positives and
  outside-object/background false alarms. Separate changes to the output contract explicitly.
- No actionable GO while a result is outside the declared freshness bound or while monitoring
  validity is unknown in the targeted tests. STOP remains highest priority.
- No GO/range overclaims on independently checked diagnostic positives; bound extra uncertain
  exposure on empty recordings so an always-CAUTION implementation cannot pass by itself.
- Material improvement in sustained detection across several object/background groups, with no
  regression on the current small-object cases. One extra late STOP frame is insufficient.
- A preregistered false-event reduction target; a candidate objective is at least one third
  fewer ride events (45 to 30 or less), preserving positives and monitored coverage. Confirm the
  objective and its tradeoffs before selecting code changes.
- Original-bag cold/warm/bounded-load and stock DDS checks still pass; evaluate freshness in
  addition to compute latency and post-settle loss. Rejudge the resulting evidence independently.

Final release publication remains on hold until the user authorizes it. A score of 75/100 is a
quality target; completing this checklist does not predetermine independent judges' scores.

## Evidence

- [Fresh full gate](evidence/results/regression_gate_2026-09-26_freeze.json)
- [P4 audit and study](P4_AUDIT.md)
- [Loaded cold capture](evidence/freeze_2026-09-26/cold_load_final/status.jsonl.gz)
- [Loaded cold node log](evidence/freeze_2026-09-26/cold_load_final/node.log.gz)
- [Frozen organizer-object frame output](evidence/freeze_2026-09-26/gate_frames/cloud_with_fake_obj.jsonl.gz)
- [Current independent scorecard](SCORECARD.md#freeze-review-26-september-night)
