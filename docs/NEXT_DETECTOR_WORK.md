# Work before a final detector freeze

Status: the registered quality cycle and its follow-up diagnosis/T1 experiment are complete;
**final detector acceptance and release publication remain on hold**. See the
[quality-cycle results](QUALITY_CYCLE_2026-09-26.md). No release tag has been created or pushed.
The [sealed P3d version](DETECTOR_FREEZE.md) remains the comparison baseline; its integrity record
and green regression gate do not close the quality gaps.

## Completed work and current disposition

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
- Current P3d plus freshness code `d480b1330491da838d6fb4996e34e37b3c060915` passes all six jobs
  in [CI run 36275557220](https://github.com/pmixay/ReSense/actions/runs/36275557220), including
  loaded runtime native-kernel assertions and synthetic replay with required freshness.
  Local download, checksum, offline loading and source/native verification pass
  ([receipts](evidence/results/quality_delivery_2026-09-26/README.md)); the previous local image
  is restored. Public publication remains prohibited.
  [Captain checklist](CAPTAIN.md#4-current-completion-and-remaining-actions).

## Further detector development remains

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
