# Falcon static-support attribution

The recurring 105.6 m and 115 m outputs come from real, stable vertical returns on the left side of the tunnel. The 115 m track intermittently changes from advisory to STOP when the estimated axis and supported range change. The pitch correction is not a necessary cause: the first observed STOP occurs before that correction is applied.

This is development analysis of the verified organizer recording, using immutable baseline `9b92df5` and the original detector functions. `trace_static.py` selects raw ROS-coordinate boxes from the point views, then observes their actual corridor, clustering and tracker routes. It never uses detector decisions to define target points. The retained trace covers selected frames within a continuous 600-frame replay; `static_inventory.jsonl` covers every frame in that prefix. Full-recording classification is separate.

## Observed route

| Frame | Supported axis | Fitted axis at 115.2 m | 115 m target's measured lateral interval | Result |
|---|---:|---:|---:|---|
| 158 | 111 m | +0.700 m | +0.934…+1.256 m | `beyond_axis`, CAUTION |
| 159 | 123 m | +0.866 m | +0.748…+1.035 m | strict-gauge cluster, STOP |
| 160 | 107 m | +0.854 m | +0.792…+1.080 m | `beyond_axis`, CAUTION |

At frame159 the target has nine raw points, eight occupied voxels and four strict-gauge voxels. Its existing tracker has 158 hits; five of its latest ten zone votes are in the gauge, so it reports STOP. The next frame's axis support ends before the target and the cluster is demoted again. This route uses ordinary cluster evidence, with no near-envelope escalation, column hold, or STOP retention. The 105 m support remains outside the measured strict gauge and continues as advisory evidence.

At frames158–160 the applied mount pitch is **0°**. Final calibration at frame192 applies −2.39° and reports height1.77m/lateral0.77m. Height and lateral are reported estimates; the calibration applies a rotation, not a translation by those values. At frame192 the 115 m target's lateral interval becomes +1.40…+1.67m after reseeding; later the fitted axis again puts some of its points inside the gauge. At frame500 a fresh gauge cluster still remains advisory because its tracker has only two gauge votes in ten frames. These observations isolate axis/support variation and temporal zone votes as the direct decision mechanism.

## Physical interpretation and limits

The raw views show repeated fixed supports at similar heights along the left-side structure. Their positions remain stable while the fitted axis varies. This supports an infrastructure interpretation and explains the earlier “false STOP” description. The recording has no surveyed far-track axis or organizer labels, so exact physical gauge membership is not asserted from the detector's own axis. Static-support alarms and the separately tracked moving person are reported separately, with that uncertainty retained.

Suppressing these targets by a special distance, width or height threshold would also suppress plausible obstacles of comparable size. No such rule is introduced. Explicit Falcon coordinate profiles and the orientation readiness guard address input compatibility; they do not certify that these far-axis alarms have disappeared. Further axis correction requires independently supported far geometry and the same positive/negative regression controls.

- [Raw support views](pictures/static_supports_raw.png): raw x/y and y/z, frames0/159/500, intensity colors.
- [Raw corridor context](pictures/raw_corridor_context.png): five static frames; height slices use the approximate near-bed pitch only for visualization, not ground-truth labeling.
- [Actual detector traces](static_trace.json), [continuous prefix inventory](static_inventory.jsonl).
