# Work before a final detector freeze

Status: authorized and underway; see the [quality-cycle results](QUALITY_CYCLE_2026-09-26.md).
The original work proposal below is retained for comparison. No release tag
has been created or pushed. Keep the sealed P3d version as the comparison baseline. The source
seal and green regression gate establish reproducibility; they do not close the quality gaps.

## Priority and evidence

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

## Proposed work order

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

## Proposed exit checks to register before implementation

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
