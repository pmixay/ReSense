# A1: directional association allowance

Preregistration, 26 September 2026. Commit this file before implementing or evaluating A1.
Baseline source: `2d25c13`, retaining the sealed P3d detector. Development data are already seen;
this experiment provides no independent real-obstacle recall estimate.

## Evidence and scope

Exact replay of 11,271 ride frames reproduced all frozen outputs and traced all 45 false-event
identities. The existing tracker promises extra allowance for along-X approach motion, but adds
`ego_speed_max * dt` to a complete 3D sphere when `dx < 0`. In two false identities this admits
transverse residuals beyond the original range-dependent base radius: `new_data_5:144`, frame321,
residual (-1.27, 2.57, 0.70) m with base2.19 m; and `new_data_2:581`, frame1340, residual
(-1.51, -2.19, -0.51) m with base2.15 m. Exact physical coordinates are compared after mount
reseeding. Existing confirmation history transfers between separate low cross-section fragments.

Other cross-fragment jumps fit the base radius. A1 is a bounded bugfix and potential partial
improvement. It cannot by itself be assumed to close the broader 45-to-30 false-event objective.

## One fixed implementation

For each predicted track/candidate pair, let `delta = candidate - predicted`, `dx = delta.x`,
`base = gate_base + gate_per_m * max(previous_track_x, 0)`, and `step` be the existing
`ego_speed_max * effective_frame_dt`. Keep the original Euclidean-distance gate unchanged:

```text
norm(delta) <= base + (step if dx < 0 else 0)
```

Add the distance-to-segment test, where the approach segment extends from `(-step,0,0)` to zero:

```text
qx = dx if dx >= 0 else min(dx + step, 0)
qx*qx + delta.y*delta.y + delta.z*delta.z <= base*base
```

Apply both tests identically to normal and thin-continuation association. Preserve original
Euclidean distance for greedy ranking. Add no configuration parameter; change no radius, timing,
confirmation, track lifetime, geometry, health or output rule. Retain the original total-distance
bound explicitly. No parameter sweep or post-result radius adjustment belongs to A1.

## Checks and acceptance

1. Focused tests: allowed pure approach and measured gaps; rejection of transverse movement made
   possible only by the approach bonus; boundary inclusion; unchanged away-motion gate; normal and
   thin paths; velocity prediction and mount-reseed behavior. Existing tracker tests must pass.
2. Full regression gate with all original caches and eight ride pieces, actual stamps, no waivers,
   missing rows or changed baseline. Every positive and background row must be no worse.
3. Repeat all 72 preregistered novel placements with unchanged plan and input hashes. For each case,
   target-matched frame count, injection-only matched count and maximum matched sensor X must be
   no worse; target matches in paired controls must not increase. Any regression rejects A1.
4. On the ride, require fewer than45 false events, no more than38 STOP episodes, and fewer than183
   alarm frames. This requires an actual exposure benefit, rather than a change in track-ID counting.
   Five empty recordings must have no more than13 false events and pass the full background gate.
5. Per empty recording and aggregate ride, extra CAUTION exposure must not exceed5 percentage
   points, and median estimated clear range must remain at least95% of the frozen baseline.
   Use the root acceptance scorer on aligned outputs. Positive monitoring overclaims cannot worsen.
6. Record every result, including a rejection. No A1 acceptance is a final detector freeze: combined
   candidates still require full gates, raw/cache comparison, rate/mount/start-offset checks,
   runtime/freshness verification and independent rejudging. The release remains on hold.

Run the full gate first. If it fails, retain the failed artifacts and stop A1; do not spend time
claiming secondary acceptance on a rejected candidate. If it passes, run all72 placements and the
aligned coverage scorer. Preserve one candidate and its tests in an isolated worktree.

### Code receipt for the repeated 72-case study

The original plan validates detector source hashes, so it intentionally cannot execute changed
code. Before any A1 evaluation, specify this repetition procedure: retain the original plan file
unchanged; create an A1 receipt that copies every case, input hash, source fixture, configuration,
window and limitation exactly, replaces only `code_sha256` with the A1 code hashes, and adds
`parent_plan_sha256` plus the candidate commit. Assert all remaining original fields are equal.
This is a new code receipt for the identical planned data, not a new placement selection. Commit
the receipt before the repeated study. Keep the evaluator and its code-hash validation unchanged.
