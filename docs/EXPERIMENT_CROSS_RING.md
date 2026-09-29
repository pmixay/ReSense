# Cross-ring sparse evidence — P3 experiment, 28 September 2026

**Status: implemented, default-off, local replay completed; no acceptance claim.** The local replay
did not show a detection-distance gain. The filter reduced alarm frames on the available recordings,
but also removed synthetic-object STOP frames and the set O cache has no real ring metadata, so this
is not evidence for shipping the filter. This working-tree experiment is not a replacement for the
[sealed detector](DETECTOR_FREEZE.md). Source base: `df24c18`.

## Hypothesis and mechanism

At long range, a small object may have too few occupied voxels for the ordinary weak-cluster
threshold. Distinct LiDAR elevation channels might supply useful additional evidence. Conversely,
some false far scan-line tracks might have only one channel. These are hypotheses: the remaining
false events have not been classified by ring support, and different rings are not independent
sensors or statistically independent observations.

Two independently configurable changes allow an ablation before trying their combination:

| Parameter | Default | Experiment | Effect |
|---|---:|---:|---|
| `cluster.weak_min_rings` | 0 | 2 | Enables an additional weak-cluster path with this many distinct channels. |
| `cluster.weak_min_points_with_rings` | 3 | 3 | Minimum occupied voxels for that path. |
| `tracking.far_min_ring_count` | 0 | 2 | Excludes known single-channel clusters from the far-evidence list. |

The combined opt-in profile is [`configs/experimental_cross_ring.yaml`](../configs/experimental_cross_ring.yaml).
It supplies overrides to dataclass defaults through `DetectorConfig.from_yaml`; it is not a full
copy of the shipped YAML. The ablation commands below instead override the canonical default file.

Implementation:

- `Candidates.ring` follows the current frame through the finite-point filter, candidate selection,
  concatenation and subsetting. Missing entries in a mixed candidate array use signed `-1`.
- `Cluster.ring_count` counts only nonnegative, decoded channel IDs of **current-frame points inside
  the strict gauge**. Neither off-gauge neighbors nor accumulated history can supply a second ring.
  The existing compact16 decoder expands dual returns and removes its flag before this stage.
- Cross-ring relaxation applies only at or beyond `tracking.thin_far_min_distance` (60 m), with that
  distance enabled. It also works with the ordinary `cluster.weak_min_points` path disabled.
- Admitted clusters remain `weak`: the DBSCAN, shape, strict-gauge, trusted-range and temporal
  approach checks still apply. A three-voxel cluster that is also flat must still satisfy the
  separate `thin_far_min_voxels` threshold; this experiment does not lower it.
- The ring filter affects `Detector._far_thin`, not normal clusters or the separate scan-line
  continuation list. Existing STOP continuation retains its voxel and time limits.
- A zero ring count means no usable current strict-gauge ring evidence. The filter falls back to
  the old path in that case; it cannot enable the three-voxel relaxation. With both flags off,
  ring metadata does not affect the decision rules.

## Limits to measure

Real far obstacles can be visible on one ring. In particular, the ring filter can delay or lose a
new obstacle track even though the sparse relaxation improves another one. A single aggregate
false-event count is insufficient to choose this profile. Different channels may still hit the
same infrastructure surface or share the same pose error.

The normal input contract uses `Frame.ring=None` for absent metadata. Some existing input converters
fill a compact array's ring field with zero when the source has no ring field. Such a cache cannot
distinguish unavailable metadata from physical channel 0: it looks like a single-channel recording.
Verify the source metadata before applying the filter to a cache. Synthetic injected points also
need a provenance check; a ring value derived or fabricated by an injector is not real sensor evidence.

Counting channels adds work even with decision flags off. Measure latency on the same execution
backend and machine, in addition to frame-by-frame default-output parity against the source base.

## Local replay result

The Windows replay was run on 28 September 2026 with Python 3.11.9, the NumPy backend, four jobs,
eight independent ride chunks, and one thread for OpenMP/OpenBLAS/MKL. All five variants processed
the same `new_data` cache (11,271 frames) and `cloud_with_fake_obj` cache (1,510 frames). The full
audit and outputs are under
`D:\Datasets\ReSense\cross_ring_2026-09-28_measurement`; `analysis.json` contains the frame-level
comparison and `audit.json` contains cache/DB3 provenance.

The source-base versus candidate-default comparison had **zero decision differences** on both
recordings. Health levels and latency are timing-derived and varied between replays; they were
reported separately rather than used to hide semantic differences.

| Variant | Ride alarm frames/events | Set O alarm frames/events | Ride advisory frames | Ride total latency median/p95 (ms) | Wall (s) |
|---|---:|---:|---:|---:|---:|
| source | 130 / 32 | 447 / 9 | 4,759 | 109.4 / 131.8 | 568.4 |
| candidate defaults | 130 / 32 | 447 / 9 | 4,759 | 105.7 / 129.4 | 547.4 |
| relaxation only | 130 / 32 | 447 / 9 | 4,762 | 113.5 / 136.9 | 589.9 |
| filter only | 129 / 32 | 437 / 9 | 4,757 | 113.7 / 133.2 | 654.0 |
| combined | 129 / 32 | 437 / 9 | 4,760 | 109.3 / 130.3 | 597.7 |

On the ride, relaxation changed three frames from clear to advisory and did not change STOP
frames/events. The filter changed four semantic frames; it removed one alarm frame in chunk 6 and
changed two warning frames plus one STOP frame elsewhere. The combined run had the union of those
seven ride changes. On set O, filter and combined removed 10 alarm frames while retaining nine
alarm events.

The synthetic-object score was unchanged for source, candidate defaults, and relaxation. Filter and
combined changed no object verdicts, but lost STOP coverage:

| Object | Candidate defaults | Filter / combined |
|---|---:|---:|
| `small_center` first STOP / held from | 55.8 / 60.8 m | 52.5 / 57.5 m |
| `big_above` first STOP / held from | 111.4 / 123.6 m | 101.3 / 111.4 m |
| `long_low_on_rails` first STOP / held from | 87.2 / 95.9 m | 82.2 / 90.8 m |

The remaining six in-gauge objects kept their scored values, and the outside-object false-alarm
result was unchanged (`big_outside`: six frames). These set O results are diagnostic only: the raw
PointCloud2 messages contain `x,y,z,intensity` and no `ring`, every sampled injected-object point
also lacks ring provenance, and the compact cache presents one artificial channel 0 in all 1,510
frames. Therefore the filter/combined set O reduction is not a valid physical cross-ring result.

The ride cache does contain real `ring` metadata (128 channels in all 11,271 cached frames), and
the DB3 receive stamps and sampled quantized point multisets matched the cache. Even there, the
three new advisory frames and one fewer alarm frame do not establish an improvement: the ride has no
object labels suitable for recall scoring, and the available replay is not the complete acceptance
set.

### Full ride false-alarm trace

The organizers explicitly confirmed that `new_data` contains no obstacles (`DATASET.md`,
"Extended real recording"). We replayed the complete source-default ride with
`scripts/trace_false_targets.py --expect-events 32`: all **11,271 frames / 32 track identities**
matched the saved source detections exactly (zero mismatch frames). The independent chunk resets
produced **130 distinct STOP frames / 31 STOP episodes**; 32 track identities accounted for 149
track-alarm frames, since multiple tracks can STOP in the same frame. The read-only trace, 32-event
inventory and target point snapshots live in `false_target_trace/`, `false_alarm_scenes_source/`
and `false_target_views/` under the measurement directory. A reproducible per-event rollup is
[`cross_ring_false_alarm_analysis_2026-09-28.json`](evidence/results/cross_ring_false_alarm_analysis_2026-09-28.json)
in the repo (also saved as `false_alarm_analysis.json` beside the full local trace), generated by
`scripts/summarize_false_target_trace.py`. The compact rollup records SHA-256 hashes of its trace
and inventory inputs; full point clouds and images are not included in Git.

| Track-event group (by maximum STOP distance) | Events | Finding on STOP frames |
|---|---:|---|
| Nearer than 60 m | 17 | Ten involved the low-object path. The exact target-point views repeatedly show a few returns at/near the fitted bed or rail-head edge; surface identity is not surveyed. |
| At least 80 m, every **fresh strict-gauge corridor** STOP support has ≥2 rings | 9 | Cannot be removed by a two-ring requirement on these clusters. |
| At least 80 m, mixed multi-/single-ring fresh strict support | 4 | Earlier multi-ring STOPs usually survive the filter. |
| At least 80 m, only one ring on every fresh strict support | 1 | `new_data_7.jsonl:264` (96–98 m); its STOP comes from an ordinary cluster, outside the current far-evidence filter's scope. |
| At least 80 m, no fresh strict-gauge corridor support on STOP frames | 1 | `new_data_6.jsonl:250` (82–84 m): one off-gauge fresh cluster, one missed-track frame; zero strict-ring count is **not** proof of a single-ring target. |

Of the 15 far events, **13 began STOP with at least two strict-gauge rings**, one with one ring,
one without a fresh strict-gauge cluster. The ring-count statistic excludes missed-track frames:
`track.last` would otherwise repeat an older cluster. Low-object clusters do not populate
`Cluster.ring_count`; all-current-point channel IDs were recorded separately. Five of the ten
low-involved events had at least one fresh low cluster spanning ≥2 raw rings, so even a hypothetical
low-ring gate would not separate all such returns.

The point-level examples show why a scalar ring threshold misses different mechanisms:

- `new_data_1.jsonl:292` (29.9–32.7 m): 6–7 low-object voxels only 3–12 cm above the fitted bed;
  observed raw channels include 60, then 59/60 and 60/61. Its `ring_count=0` is a **low-path
  placeholder**, not missing channel metadata.
- `new_data_5.jsonl:330` (40–48 m): an ordinary edge cluster 3.5–5.5 m along the track,
  56–69 voxels with 3 strict-gauge rings, surviving an approach to a STOP. The raw points span
  many rings; the narrow strict-gauge part supplies the three that count.
- `new_data_6.jsonl:331` (97–110 m): the STOP begins with a 1.2 m long, roughly 1.9 m tall cluster
  supported by **9 strict-gauge rings (35–43)**; later the track continues after its support leaves
  the strict gauge. This is not a single-channel scan-line error.
- `new_data_7.jsonl:264` (96–98 m): fresh strict support is one ring, but the cluster's *full*
  current points span two or three rings. Off-gauge points cannot legitimately promote its strict
  ring count, and the normal cluster path (8–11 voxels) bypasses `far_thin` anyway.

The filter's only ride STOP change was `new_data_9800`, track `new_data_6.jsonl:518`: a **single-ring,
four-voxel flat cluster** at 118.8 m on frame 9799 was advisory in the source and excluded from
`far_thin` by the filter. The next frame had a five-voxel, **two-ring ordinary cluster** at 118.4 m;
the source issued STOP there, the filter remained advisory. But the same track had already STOPped
on frames 9786–9787 and still STOPped on 9801–9809: the filter removed **one frame, zero events,
zero STOP episodes**. No tracked STOP frame used a thin cluster directly; this was a one-frame
history effect. Target-point views also show multi-ring, vertically extended far returns in several
scenes, and rail/lining-like close returns; the plots alone do not establish a particular physical
surface for every false target.

**Implication:** the present hard two-ring `far_thin` filter addresses only a narrow entrance to
the tracker, while most false STOPs arise from ordinary multi-ring clusters, near low evidence,
or continuation across missed/off-gauge frames. Raising ring requirements globally would need
independent real-object recall evidence (including the six missing short bags and objects that
occupy only one channel); this trace is diagnostic, not a safe new rejection rule.

## Local verification

Windows, Python 3.11.9. Open3D 0.20.0 was installed in the isolated environment
`C:\Users\alikh\AppData\Local\Temp\opencode\resense-cross-ring-venv` (system site packages visible).
Use that environment's Python for the following tests:

```text
python -m pytest -q tests/test_cross_ring.py tests/test_far_thin.py tests/test_stage_trace.py tests/test_stop_keep.py tests/test_algorithm.py tests/test_reseed_safety.py tests/test_history_robustness.py tests/test_track_opinion.py tests/test_late_candidates.py
```

Result on the final code: **167 passed**, 81.43 s. Coverage includes current/strict-gauge provenance,
missing metadata, accumulation, dual returns, finite filtering, reset, default decision parity with
and without rings, sparse-to-tracker integration, approach gating, STOP continuation and tracing.
The point fixtures prove the mechanism; they are not a range/recall benchmark.

A preceding full `python -m pytest -q --tb=short`, before the final reset cleanup and parity test,
reported **637 passed, 80 failed, 28 skipped, 1 deselected, 6 subtests passed**, 196.18 s. Remaining
failures were inspected:

| Failure group | Count | Local cause |
|---|---:|---|
| `test_check_no_network` | 4 | Windows `WSAE*` error names differ from expected POSIX names. |
| `test_dds_transport` and one `test_detector_freeze` case | 16 | Windows symlink privilege unavailable. |
| `test_load_image`, `test_release` | 55 | `bash` resolves to WSL, which has no `/bin/bash` in the available distribution. |
| `test_unpack_dataset` | 3 | Backslash paths compared with slash paths. |
| `test_far_range_eval` | 2 | Test timestamp keys use `rsplit("/", 1)` on Windows paths; the runner uses the basename. |

The trace rejection assertion was updated for the new weak-branch condition; its tests pass.
Ruff and whitespace checks passed. A full green Linux suite remains pending.

`python scripts/detector_freeze.py verify` reports **FAIL** for this experimental tree. It also
reports byte differences in untouched CRLF checkout files; these are not additional source edits
in `git diff`. The seal and acceptance evidence have not been regenerated.

## Remaining acceptance protocol

The local replay is not the full acceptance run. The six short organizer recordings are absent,
Docker's Linux daemon is unavailable, and `quality_screen.py` requires Linux (`fcntl` and the normal
Linux evaluation environment). The complete acceptance still requires a Linux data machine with
the full cache, including all six recordings, set O, ride, and set F inputs.

On that machine, run these four experiments sequentially in the same candidate checkout and with
the same backend:

```bash
python scripts/quality_screen.py --name ring_base --cache /data/cache --work /data/work \
  --reference /data/work/ring_base/gate

python scripts/quality_screen.py --name ring_relax --cache /data/cache --work /data/work \
  --reference /data/work/ring_base/gate \
  --set cluster.weak_min_rings=2 --set cluster.weak_min_points_with_rings=3

python scripts/quality_screen.py --name ring_filter --cache /data/cache --work /data/work \
  --reference /data/work/ring_base/gate --set tracking.far_min_ring_count=2

python scripts/quality_screen.py --name ring_combined --cache /data/cache --work /data/work \
  --reference /data/work/ring_base/gate \
  --set cluster.weak_min_rings=2 --set cluster.weak_min_points_with_rings=3 \
  --set tracking.far_min_ring_count=2
```

Before drawing conclusions, compare `ring_base` per-frame semantic outputs with the unmodified
source base `df24c18`. Preserve the patch/source identity, effective config, cache identity and logs
with each result. A smoke or quick subset is not full acceptance.

Inspect `gate.json`, `acceptance.json`, `history.json` and the stage logs, not just the command's exit
code (since 29.09 the quality-screen wrapper exits with the first failing stage's code and reports
only the stages it ran in that invocation). Check:

1. No missing or worse gated metric against the current 27.09 baseline, without waivers.
2. First/sustained STOP distances, per-object and per-distance-bin coverage, and missed intervals
   (especially the far plank and upper-edge box, often seen on a single scan line).
3. False events **and** STOP episodes per empty recording and ride segment; trace every changed
   event's strict-gauge rings and distinguish loss of confirmation from fragmentation of a track.
4. Monitoring/GO overclaims, history stress and latency; a lower false-event count must not come
   from hidden objects or a loss of monitored range.

Choose a candidate only after these measurements. The current result is a tested opt-in mechanism,
with no demonstrated improvement in the approximately forty-event false-alarm plateau. Defaults,
the detector seal, and release acceptance remain unchanged.
