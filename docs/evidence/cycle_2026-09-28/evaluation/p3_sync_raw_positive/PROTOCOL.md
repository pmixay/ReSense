# Common-source four-config raw positive check

Registered before replay. The input is known development data, not a holdout.
Production source remains fixed at `b84ea8f229be8d11d9db82ebd337198803ce92bf`.

| Variant | `stop_keep_low_s` | `fresh_stop_evidence` |
|---|---:|---|
| both_off | 0 | false |
| continuation_only | 0.3 | false |
| onset_only | 0 | true |
| both_on | 0.3 | true |

All configurations load the same committed canonical YAML and dataclass defaults.
Cross-ring relaxation/filtering and local bed support remain disabled. The onset
window/minimum remain 3/2. No settings will be tuned using the results.

Replay all original 201 `doubleT_obstacle` frames in message order, preserving raw
float returns, channel IDs, source frame indices, frame IDs and timestamps. Each
configuration uses a fresh detector and an independent copy of each frame. No
cache quantization, subsampling, injected targets, observer masks or oracle
coordinates enter the detector.

Source files must match the exact expected commit before replay. Preserve the
source inventory, effective configurations, source/import paths, native backend,
input/label hashes, per-frame input array hashes and observer hash. Verify source,
input, labels, native binary and observer/dependency hashes again after replay.
The observer requires exact 0–200 coverage and matching identities across variants.

Use the existing committed labels and one-to-one physical assignment from
`resense.metrics`. Retain every public result, detection and label match; report
per-target onsets, STOP/missed intervals and the established rail-only window
(frame 75 onward). Retain every unmatched detection and STOP track onset/interval.
An unmatched detection means unmatched to the existing labels; labels are not an
independent exhaustive scene annotation.

Compare both_off→continuation_only, both_off→onset_only,
continuation_only→both_on and onset_only→both_on. Require no newly missed labelled
frame and no new unmatched detection. Compare unmatched detections physically,
one-to-one within 0.5 m along track and 0.25 m lateral with matching kind; differing
track IDs neither establish a new false detection nor excuse a physical change.
Retain exact lost/gained target frame IDs even if aggregate recall is equal.

Run one process and one numerical thread. Timings during the concurrent default
gate are diagnostic only. A pass is a positive-recording precheck: opt-in defaults
still require the other bags, ride, sets O/F and paired histories. Unit tests
separately expose P3's current veto of near escalation on advisory clusters and
verify weak-low provenance, expiry, reacquisition and opinion ordering.

Reproduction (after the default-gate CPU slot is released):

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 scripts/compare_raw_positive_configs.py \
  --source-root /workspace/ReSense-p3-sync \
  --expect-commit b84ea8f229be8d11d9db82ebd337198803ce92bf \
  --bag /data/raw/for_hackathon/doubleT_obstacle \
  --out /cycle/p3_sync/raw_positive_four_configs
```
