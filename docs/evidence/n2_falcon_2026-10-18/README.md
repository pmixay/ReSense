# N2: complete Falcon intake and measured input adaptation

The entire organizer Falcon recording is now available as a verified float32 cache:
**4,443 frames over 444.209 seconds**, including the previously unseen remainder.
Explicit ROS and manufacturer-native profiles produce identical full-recording
decisions and detections. The supported eight automatic orientations now preserve
all **193 STOP frames, first STOP at frame 8**, on `doubleT_obstacle`; unconfirmed
orientation cannot report clear space. The remaining far static-support alarms
and sampling sensitivity are recorded below, not suppressed by target-specific rules.

This is development evidence on `work/n5-labels-c2-acceptance`, not a release or
an independent hidden-set score. The sensor proxy full gate and final combined
default gate are separate experiments; completion links are added when their
complete input receipts and results are available.
Completed raw JSONL captures are portable in the [verified raw archive](raw/README.md);
extract it to restore the paths used by these reports and reproduction scripts.

## Data and actual sensor contract

| Item | Complete-recording observation |
|---|---|
| Source | Organizer `falcon_test.zst`, SHA256 `90dea27d8636bcb2e5cdddf9bc15add3eae0e05196c2b3de959482da7e505611` |
| Topic / frame | `/iv_points` / `seyond` |
| Actual coordinates | ROS FLU: +X forward, +Y left, +Z up |
| Manufacturer-native coordinates | Separate profile: +Z forward, −Y left, +X up |
| Points | 94,183 / 94,991 / 95,494 raw returns per frame, minimum / median / maximum |
| Ring | Absent. `scan_id` is a curved raster line, not a fixed-elevation Pandar channel |
| Returns | Valid `is_2nd_return` flags: median 2,005 points per frame, about 2.1%; earlier blanket single-return wording is superseded |
| Range | Raw maximum 509.97 m. The explicit node range crop remains radial 2.5–250 m |
| Clock | Continuous 10 Hz header timestamps; minimum/median/maximum step 0.099996311/0.100002044/0.100007840 s |

The [source receipt](source_receipt.json), [cache receipt](cache_receipt.json),
[per-frame checksums](cache_inventory.json) and
[all nine 50-second characterization windows](characterization_summary.json)
record the actual bytes, field layout, return flags and crop counts. The float32
cache avoids the old int16-centimetre range limit and always passes `ring=None`.
Background nearest-neighbour probes across the whole recording support a
stationary scene; they are not odometry or exhaustive obstacle truth.

The temporary 20.28 GB raw DB3 was deleted only after all 4,443 cached frames had
been reloaded and checked. The [cleanup receipt](temporary_db3_cleanup.json)
retains its hash and source, and the original first 100 raw messages remain as a
playable bag for actual DDS testing ([subset receipt](playback_subset_receipt.json)).
The cache is `/home/resense/data/decoded/falcon_test_second_dark`; the short bag is
`/home/resense/data/n2/falcon_first100`.

The first actual Humble playback found an extraction bug: the auxiliary SQLite
`schema` table had been created without its required row. The
[repair receipt](playback_subset_repair.json) supersedes the original subset DB3
hash and preserves the [failed player log](playback_subset_failed_player.txt).
The repair inserts the schema row from an identical, playable Humble storage
layout; it is explicitly reconstructed compatibility metadata. All 100 serialized
CDR hashes, message timestamps/IDs, topic/QoS and the 100-frame YAML metadata remain
unchanged. `ros2 bag info` now opens the bag successfully. The builder now copies
original schema rows. The final actual DDS retry receives all 100 Falcon frames
after all 40 preceding Pandar frames in one node. An independent
[100-frame comparison](actual_dds_prefix_comparison.json) finds exact shared
detection/warning payloads and post-initial decisions versus the offline prefix.
STOP occurs at frames 25–28 for the 115 m support, with no held stale STOP.
The initial epoch guard remains FAULT; the selected conservative Falcon policy
reports unavailable small-target range as null and clear range zero.
The corrected-core `7b7b02c` image repeats the same 140-input DDS test. Its
[independent Falcon prefix comparison](actual_dds_prefix_7b7b02c.json) also passes
all 100 frames with the same four STOP frames and no stale held result.

## Input profiles and startup behavior

The node profiles are `manual`, `pandar128`, `falcon_ros` and `falcon_native`.
Named profiles set a consistent signed-axis mapping, clear old fixed mount angles,
enable calibration, and preserve the configured up axis during automatic search.
They are selected explicitly, not guessed from topic names. A runtime profile
switch resets the queued input, calibration, detector, STOP history and display
through N4's generation boundary. The profile sets the range sensor model to
Falcon, so the Pandar small-target prior is not silently reused.

```sh
docker run --rm -it --net=host --ipc=host resense:lidar-7b7b02c \
  ros2 launch resense_ros detector.launch.py freshness_mode:=replay \
  sensor_profile:=falcon_ros input_topic:=/iv_points clear_range_policy:=conservative
```

This is the development image already built and tested on this host, not a
published release tag; its [image identity and source receipt](../n1_n4_2026-10-18/final_core_7b7b02c/image_receipt.json)
are retained with the actual DDS test.

Use `falcon_native` for actual manufacturer-native coordinates. Explicit mappings
for all 24 proper axis permutations produce exactly the same vehicle-frame points
on every tested obstacle and ride frame. Expanding automatic search to 24 candidates
remains an experimental option: a wrong orientation can pass a geometric sanity
check. Explicit mappings are the operational route for sideways mounts.

The completed [24-orientation baseline sweep](orientation_obstacle/summary.json)
confirms that limitation over all 201 obstacle frames. Two sideways cases
(`auto_04`, `auto_05`) never recover the correct orientation and produce 8 and
4 GO frames respectively with the wrong geometry. Fourteen other non-upright
cases adopt at frame 2 but lose the baseline STOP frames 8–10. These are baseline
measurements, not a claim that the new readiness guard solves a wrongly accepted
configured mapping. The corrected eight-orientation results below are the supported
automatic scope; all 24 explicit mappings preserve exact vehicle coordinates.

The core readiness guard, committed as `63b4c92`, preserves STOP/error priority
and reports CAUTION with zero clear range until the existing configured-mapping
check or orientation adoption succeeds. It does not lower any confirmation bar.

The bounded replay candidate `71d3067` rebuilds the first few real inputs only
after validated discrete orientation adoption, then publishes only the current
input's result. It has a current-inclusive maximum of four frames and a conservative
32 MiB history budget, rejects unsupported metadata, and drops history on a reset,
non-finite/non-increasing timestamp, gap over one second or input identity change.
Late adoption falls back without replay. Unsupported detector subclasses are
explicitly skipped. The total physical call time includes replay cost.

| Check | Result |
|---|---|
| Obstacle, guard only | Seven remounts adopt frame 1; 191 STOP frames, first at 10; no unconfirmed GO |
| Obstacle, bounded replay | All eight mappings: 193 STOP frames, first at 8; no lost or delayed STOP |
| Post-adoption obstacle outputs | Every serialized detection, warning, decision, nearest/clear/monitored range equals the unrotated control |
| Initial remounted output | One CAUTION or FAULT frame, clear range zero; adoption at frame 1 |
| Ride split 200, all 51 frames | Baseline 51 GO, no alarms; remounts have one initial CAUTION/FAULT then 50 GO, identical post-adoption detections/warnings |
| Explicit axis mappings | All 24 preserve exact vehicle coordinates across all 201 obstacle and 51 ride frames |
| Actual replay history | Two frames, counted 24,542,114 bytes; one-time physical CPU 132–163 ms on the shared host |

The ride split was selected from already completed intake before inspecting its
detector output; it was not the chronologically first decoded split. Its original
bag receive timestamps are preserved. No extra full ride cache was created.

See [guard-only results](orientation_candidate/summary.json),
[replay results](orientation_replay_candidate/summary.json),
[frame-level comparison](orientation_replay_candidate/independent_frame_check.json),
and [ride results and input hashes](orientation_ride200/summary.json).
Four remounts have tiny unrounded track-coefficient differences (at most 3.71e−8
in the floor coefficients) without changed emitted detections or ranges.
Concurrent wall times of 2.05–3.32 seconds for the adoption call, and a 4.29-second
maximum outer call including orientation search, are not an idle-host benchmark.
Default four-frame replay was enabled by the parent integration in `5b8bbfd`,
subject to the unhooked combined gate.

An independent review then found that `deepcopy` can allocate larger nested-list
containers than their source. The original 32 MiB accounting was therefore not a
hard bound for arbitrary supported metadata, although the measured decoder inputs
remained within budget. Commit `7b7b02c` reserves container expansion before copying,
charges independently copied array aliases separately, and checks actual retained
storage afterward. The original failing case now stops before allocation. The
[independent review](INDEPENDENT_ORIENTATION_REVIEW.md) includes a 216-case container
sweep and unchanged storage/acceptance for the real obstacle and Falcon inputs.
The [focused corrected-source checks](orientation_replay_candidate/bound_fix_tests.json)
pass 149 tests. Original results above retain their original source identities;
the [corrected-source eight-orientation replay](orientation_bound_fix/summary.json)
also completes all 201 frames per case: 193 STOP frames, first at 8, no loss,
delay or unconfirmed GO. Its two-frame reservation is 24,542,818 bytes.
[Comparison with the previous replay and ordinary baseline](orientation_bound_fix/previous_and_ordinary_comparison.json)
finds identical decisions, detections, warnings, ranges and point counts. The
recorded unrounded coefficient differences are at most 1.33e−15; these are
disclosed separately from the exact output comparison. Corrected-source combined
gates remain separate integration evidence.

## Full recording: static supports and the person

The raw-cloud reviewer inspected 11 selected positive anchors and all 113 dense
trajectory anchors without using detector decisions as labels. The main approach
is linked from about 249 m at frame 1725 to 3.8 m at frame 4400, including pauses
near 243.5 m and 100 m. The earlier sparse episode at frames 1200–1300 remains a
separate uncertain identity. These are observed body supports, not exact physical
extent, surveyed gauge membership or an exhaustive first-visible claim.

The [manual anchors](falcon_reviewed_anchors.json),
[reviewed trajectory](raw_person_review/atlas_proposals.json),
[review receipt](raw_person_review/atlas_review_receipt.json) and ten raw contact
sheets preserve this distinction. `summarize_falcon.py` inverse-transforms output
centres to raw ROS coordinates and interpolates only between reviewed anchors
at most 25 frames apart. Generous and tighter association margins are both
reported; unassociated detections remain unknown.
The field `frames_with_any_unassociated_stop_detection` includes frames that
also contain a matched person or support. It is not a count of false STOP decisions.

| Full 4,443-frame baseline replay | Default Pandar axes + auto | Explicit ROS | Native encoding + explicit native |
|---|---:|---:|---:|
| GO / CAUTION / STOP / FAULT | 8 / 3,062 / 1,372 / 1 | 13 / 3,043 / 1,387 / 0 | identical to explicit ROS |
| Person-associated STOP frames | 1,350 | 1,369 | 1,369 |
| First person association | frame 2972, about 124.67 m raw forward | frame 2950, about 127.07 m | same |
| 115 m support gauge detections | 13 | 29 | 29 |
| 105 m support gauge detections | 0 | 0 | 0 |

All explicit ROS/native serialized decisions, detections, warnings, nearest,
clear and monitored ranges are identical over the whole recording. Tighter body
matching gives 1,345/1,363 person-associated rows, demonstrating the annotation
and association sensitivity. Counts are not exact TP/FP scores.

Explicit axes change 28 frames into overall STOP and 13 out of STOP (net +15)
relative to old auto startup. Five of the added overall STOP frames are the 115 m
support; one lost overall STOP is the same support. Other changes include person
associations and near-pass overhead outputs of unknown identity. Across all
detection payloads, support STOP associations rise by 16 and person associations
by 19; these overlap in frames and must not be summed as decision changes.
This is not a blanket improvement or a claim that false alarms are fixed.

[Static attribution](STATIC_ATTRIBUTION.md) traces the actual ordinary-cluster
and tracker route: at frame 159 a changed axis/support estimate places four
occupied voxels of the real 115 m support inside the strict gauge, and five of
ten recent zone votes trigger STOP. Applied mount pitch is still zero. Height
and lateral mount estimates are metadata, not an applied translation. The cause
is axis/support variation and temporal votes; a distance/shape blacklist would
also remove plausible obstacles. No such suppression is introduced.

[Complete per-window associations](falcon_full_associations.json) retain all
frames, association lists and unknown outputs. The full **4,443-frame new automatic
startup replay is complete**: every detection and warning equals explicit ROS;
every decision, nearest, clear and monitored range also equals it after the initial
frame. That first frame remains FAULT with zero range until orientation is confirmed.
The new auto totals are 1 FAULT, 12 GO, 3,043 CAUTION and 1,387 STOP. Its person
and static-support association counts equal explicit ROS, including the disclosed
increase in static-support alarms. See [candidate capture](falcon_replay_candidate/summary.json).

## Fields and sampling sensitivity

All 201 obstacle frames were replayed for every variant against immutable `9b92df5`.
The complete [field results](fields_obstacle/summary.json) include each changed frame.

| Variant | STOP frames | First STOP | Interpretation |
|---|---:|---:|---|
| Baseline | 193 | 8 | Control |
| No ring; intensity 0–1; uint8 intensity; padded float32; padded float64; new topic/frame | 193 each | 8 each | All decisions identical |
| Exact-XYZ deduplication, historical `single_return` case name | 189 | 8 | Four lost STOP rows: 138, 165, 182, 196; this is a return-count stress transform, not exact sensor echo physics |
| Every second channel removed | 65 | 8 | 128 baseline STOP rows lost from frame 73 onward |

Removing points also changes calibration and floor/track evidence: provisional
roll is 3.62° in the control, 3.12° after deduplication and 2.87° after channel
removal. Field-layout compatibility therefore does not establish robustness to
sparser sampling. The tests report this degradation rather than weakening
confirmation thresholds without negative-control evidence.

The Falcon proxy crops the forward FOV, retains the nearest real return per
documented approximate angular cell, uses the denser central ROI and passes no
ring. It cannot create denser ROI rays, curved raster geometry, wavelength or
noise. Inputs are already range-cropped; original `n_raw/n_near` metadata remains
unchanged, so raw health statistics are not a complete sensor simulation.
The original gate's visibility and injected-point denominators are also retained:
measured loss can include positive returns removed by the transform, so it is
not an isolated detector-recall measurement on unchanged observable objects.

The ten decoded-bag stress captures are complete: **5,665 frames per arm**,
with every raw hash and frame identity checked in [the paired summary](proxy_summary.json).
The proxy retains median 15.3% of obstacle-recording points and about 24–25% in
the other recordings. It clearly fails to preserve the baseline behavior:

| Recording | Baseline STOP frames | Proxy STOP frames | Baseline STOP rows lost | Added STOP rows |
|---|---:|---:|---:|---:|
| `doubleT_obstacle` | 193 | 68 | 125 | 0 |
| `doubleT_platform` | 0 | 13 | 0 | 13 |
| `roundT_doubleT` | 0 | 6 | 0 | 6 |
| `roundT_pressureGate_roundT` | 2 | 0 | 2 | 0 |
| `roundT_squareT_pressureGate_squareT` | 0 | 0 | 0 | 0 |
| `squareT_platform_squareT_switch` | 11 | 58 | 9 | 56 |
| Set O | 452 | 324 | 140 | 12 |
| Synthetic platform | 185 | 270 | 10 | 95 |
| Synthetic switch | 142 | 120 | 34 | 12 |
| Synthetic tunnels | 126 | 117 | 9 | 0 |

The five known obstacle-free recordings rise from 13 to 77 STOP frames. Increased
STOP on the synthetic platform is not automatically improved recall: these are
overall decisions, with uncertain gauge membership and changed visibility/geometry.
The decoded replay uses original header stamps and the radial crop; its totals
must not be substituted for the separate compact-input, receive-stamp full gate.
No detector thresholds are relaxed to make this sampling experiment pass.

The separate
`run_proxy_gate.py` executes the entire normal gate on transformed input, including
Set F after object insertion, and refuses an incomplete ride receipt. It records
per-source-frame before/after point counts, requires child-process hook activation
and verifies the total processed-frame count. **Its source hash must never be used
as default-input freeze evidence.** The paired sealed reference is
`../integration_2026-10-16/h5/candidate/gate.json`, SHA256
`e0b2c76f61d6b65b1f6d3901af91c96d6370e76c125b5192735399b889a5547a`;
`git diff 5211565 9b92df5 -- resense configs native setup.py` is empty.
Current intake receipts establish the cache provenance separately.

## Reproduction

```sh
python docs/evidence/n2_falcon_2026-10-18/replay_inputs.py \
  --source /path/to/immutable/source --cache /path/to/float32/cache \
  --out /path/to/new/output --suite falcon
python docs/evidence/n2_falcon_2026-10-18/replay_inputs.py \
  --source /path/to/immutable/source --cache /path/to/doubleT_obstacle \
  --out /path/to/new/output --suite orientation --upright-only --replay-frames 4
python docs/evidence/n2_falcon_2026-10-18/run_proxy_gate.py \
  --source /path/to/immutable/baseline --cache /path/to/complete/gate_cache \
  --out /path/to/new/transformed_gate --baseline /path/to/sealed/gate.json
python docs/evidence/n2_falcon_2026-10-18/summarize_falcon.py
```

All long measurements use one BLAS/OpenMP thread. The available VM exposes one
CPU and 4 GB RAM; timings under simultaneous intake/replay are diagnostic. The
available-hardware node/DDS benchmark belongs to N1/N4 and the parent integration.

The final focused N2 checks passed **48 tests** in 14.94 seconds, including field
layout, explicit profiles, readiness, bounded replay and child-process proxy
activation ([test output](focused_tests.txt), [JUnit](focused_tests.xml)). Pinned
Ruff 0.15.8 also passes the owned N2 scripts and tests. The parent integration
records the broader test and gate results separately.

The final integration follow-up passed **51 tests** in 22.48 seconds
([receipt](integration_followup.json)). Its three test-only adjustments supply
the deterministic CPU clock and explicitly verify the observer's unsupported
startup-replay diagnostic before comparing all other fields. Runtime and the
historical comparison helpers remain unchanged; an independent reviewer checked
the fixes. Instrumentation subclasses still do not promise orientation-adoption
parity.
