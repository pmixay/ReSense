# H4 independent object-safety review — registered before measurement

Reviewer: fresh H4 safety session, no authorship of reviewed production changes.
Registration date: 2026-10-16. Review target: `707ea9c..7cc640f` on
`integration/2026-10-15-16`; H3 measured detector `f8c088dc4f3243fbd15a3aae9be0459e8a0aa941`.
Production is read-only. Only this evidence directory and its new review scripts are writable.
This is a safety review, not release approval. Medium-or-worse confirmed findings block H4.

## Identity and environment

Use the H3 immutable Linux image
`sha256:5e2659e8f8d3a7e9f64d7c269ae920badd86b8a388e48e9449dda7028b920c19`,
retained sealed/combined Linux checkouts mounted read-only, native enabled, one thread per
numerical library. Assert `PYTHONPATH`, `RESENSE_REPO`, `resense.__file__`, Git HEAD,
config/source/native hashes. Check production Git blobs against `7cc640f` and `f8c088d`.
Own scratch root: `resense-integration-h4-safety-20261016`. Unique Docker names only.
Record input arrays' hashes, geometry, sensor grid, seeds, labels and per-frame outcomes.
No G3 heldout specification, windows, seeds or shapes are read or used.

## Independent experiments

1. **Physical ray scenes, clustering plus shipped tracker.** New analytic slab-intersection
   caster, nearest opaque/absorbing hit, sensor height 1.83 m, rectangular tunnel ceiling
   4.12 m, side walls +/-2.43 m, far end 247 m, max range 225 m, azimuth phase 0.037 deg,
   0.1 deg azimuth steps, Pandar elevation grid. Independent physical GT is the known
   straight rail axis y=0 and the configured physical envelope, never a fitted detector axis.
   Distances 37, 67, 109, 137 m; lateral centers 0, +0.68, -0.68, +1.30 m;
   square pole widths 0.28 and 0.46 m, heights 2.72, 3.22, 3.62 m, and ceiling-height
   column controls. Include 2.54..3.18 m and 2.54..ceiling absorbing bands, beam-occluded
   free poles, multiple columns at distinct ranges. Ring modes highest-first, reversed,
   permuted (seed 461019), absent. Point dropout 0 and 27% (seed 461021).
   Twenty identical-frame observations per scene model a stationary train; object-only
   dropout at frames 9 and 10 tests hold/release. Compare exact sealed and combined code,
   match STOPs to labeled returns / physical bounding boxes; retain every matched STOP
   frame, candidate reason, zone, column/spare history and reported state. Tall misses
   and false releases are assessed even if inherited from the seal.
2. **Surface-cut / partial-body controls.** Fresh analytic smooth surface with x=76..143 m,
   y=1.17-0.073*(x-103)+0.31*h-0.12*h^2, h=0.11..2.97, sampling 0.23 x 0.19 m;
   faces at x=93 and 111 m, width 0.17/0.39/0.63 m, top 1.73/2.71 m, front residuals
   1.12/1.36/1.64 m, mirrored and reversed order, one/two echoes. This is a component
   probe with known supplied corridor coordinates, not a physical ray-cast claim.
   Observe parts, matching STOPs, shortening and the single-column/resolved-column
   threshold. Exercise actual low-duplicate filter followed by tracker, including a
   newly spared cut part and a separate low obstacle; report realizability limitations.
3. **Real development stress.** Replay complete development B and S caches with independent
   dropout 27%, seed 461023, exact same masks/stamps for both sources, fresh detector per
   recording. Compare STOP frame sets and detection/warning descriptors, not just counts.
4. **H3 promotion provenance.** Independently replay ride piece 1 (the H3 eight-piece
   boundary) from a fresh detector, original stamps, both sources. At
   `new_data_54_0009`, identify the changed candidate by geometry and actual `t.last is c`,
   capture pre/post spare processing and all track qualification histories. Check track 422
   and output membership rather than trusting the authored trace. Compare the replay's
   serialized non-timing outputs to retained H3 outputs.
5. **Dark-band residual.** Replay ride pieces 1 and 3 with the inherited 0.6-degree
   observation-only continuation deletion, independently implemented; preserve its artificial
   nature (edits the free-top observation, not an entire physical scene). Same mask for the
   sealed classifier is vacuous because it has no free-top observer; compare exact STOP
   frame sets and matched tracks against plain sealed runs. Independently test physically
   absorbing synthetic column bands in experiment 1. Do not waive the inherited 9+5 excess.
6. **Azimuth cache.** Independent brute-force azimuth-window identity checks, seed 461029,
   80,000 float32 returns, 150 windows including front/back, x=0 and bucket boundaries.

## Interpretation / completion

Separate measured end-to-end real replay results, physical ray/component results and
constructed state-machine witnesses. An expected rule response is not automatically safe.
For findings retain severity, exact input and source identity, reproducible command, per-frame
STOP presence/absence, source lines and reason. No production tuning or core fixes.
Any protocol extension is registered as an addendum before measuring it. Commit only own
new evidence after status/diff/log inspection; local commit only, no amend/push/delegation.
