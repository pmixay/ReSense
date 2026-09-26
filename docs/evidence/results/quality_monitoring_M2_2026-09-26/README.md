# M2: supported thin evidence limits the monitoring estimate

**Observer result: eligible for review as a partial improvement.** Production integration and
acceptance remain separate. The exact protocol was committed as `57bc3dd` before implementation;
the observer was committed as `f2994d1` before measurement. No detector parameter changed.

Every upstream frame output across all 15 sealed captures reproduced the baseline, excluding
informational timing. The observer retained existing detections and tracking and changed only
the range estimate and explicit uncertainty. All compressed per-frame outputs, the summary
and their hashes are retained here.

- Set O diagnostic target overclaims: **54 → 44**, including GO **46 → 36**. Capping never
  increases an estimate, so it introduces no new overclaim frame.
- Five empty recordings: extra uncertain exposure **0–1.19 percentage points**; median range
  retains **98.25–100%** of baseline. Every recording passes the registered limits.
- Full ride: extra uncertain exposure **0.612 percentage points** (69/11,271 frames); median
  range **122.6 → 121.4 m**, retaining **99.02%**. STOP output is unchanged.
- Original real-positive recording: detections and median range unchanged.

This does **not** meet the central zero-GO-overclaim objective. Sparse cubes, points removed by
confidence margins and other filter losses remain unrepresented. The diagnostic labels inherit
an earlier rail fit, not surveyed envelope truth. These measurements are development evidence.

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python scripts/evaluate_thin_monitoring.py \
  --cache /path/to/cache --reference docs/evidence/freeze_2026-09-26/gate_frames \
  --out /path/to/monitoring_M2
```

Run this observer from its recorded baseline checkout. After production integration, it should
reject source/output changes rather than silently comparing against different detector behavior.
