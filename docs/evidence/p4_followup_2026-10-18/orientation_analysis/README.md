# L16: known side mounts corrected; automatic ambiguity remains open

The existing explicit axis parameters restore the upright result for **both tested known 90-degree side rotations**. Across all 545 empty and 201 real-obstacle frames, each correction produces exactly the upright non-timing serialized output: decisions, detections, warnings, ranges, track/mount fields, and every STOP boundary. No production code or default changed; startup replay remains **0**. This is a configuration workaround, not an automatic-orientation fix.

| Full recording | Upright STOP | Case 4, explicit axes | Case 5, explicit axes | Case 5, wrong default axes |
|---|---:|---:|---:|---:|
| `roundT_squareT_pressureGate_squareT`, 545 known-empty frames | 0 | 0 | 0 | **509** |
| `doubleT_obstacle`, 201 real-obstacle frames | 193 | 193 | 193 | 190 |

The corrected real-obstacle interval is exactly **frames 8–200**, with no lost, added, delayed or shortened STOP. The wrong case loses six upright STOP rows, 189–194, and adds three, 5–7. A large aggregate STOP count in that case does not establish obstacle detection correctness. The fresh upright 0/193 counts agree with P4's archived controls.

The measurement completed at **12:56:44 UTC on 18 October**: **2,984 rows**, exit 0, no repeats. It used the immutable version-only candidate `e9d8fc649f2dd51dd5cd1e4b04ac8c306cc02569`, native SHA `511f7766639f0ddab471a77263f7a343de19d0a8217dd7cd3a11635c8a7db2c8`, Haswell, one BLAS thread and nice 5. The shared one-CPU run took 459.8 s wall / 108.5 s process CPU, peak RSS 336.5 MiB. These are diagnostic costs for four interleaved offline replicas, not a live throughput claim.

## Exact mapping and usable configuration

For original sensor-to-vehicle matrix `B`, P4 encodes the synthetic remount as `s′ = s Bᵀ Rᵀ B` using row-vector points. The inverse sensor mapping is **`C = Rᵀ B`**. The harness derives the signed axes and checks the resulting `axis_matrix`. Every corrected vehicle XYZ byte equals the upright input before processing, on all 746 frames for each correction. Intensity, ring, point order, stamps, topic, frame identity and raw/near counts are preserved.

| P4 case | Vehicle-frame input transform `R` | Correct sensor axes |
|---|---|---|
| 4 | `[[1,0,0],[0,0,1],[0,-1,0]]` | forward `-y`, left `-z`, up `+x` |
| 5, one of the worst empty cases | `[[1,0,0],[0,0,-1],[0,1,0]]` | forward `-y`, left `+z`, up `-x` |

For a driver/mount **known to have exactly the corresponding raw-axis convention**, the current launch contract is:

```sh
# P4 case 4 convention
ros2 launch resense_ros detector.launch.py sensor_profile:=manual \
  sensor_forward:=-y sensor_left:=-z sensor_up:=+x \
  auto_calibrate:=true keep_up_axis:=true

# P4 case 5 convention
ros2 launch resense_ros detector.launch.py sensor_profile:=manual \
  sensor_forward:=-y sensor_left:=+z sensor_up:=-x \
  auto_calibrate:=true keep_up_axis:=true
```

Use the candidate's default YAML, which keeps orientation replay zero. These commands describe the source-checked launch parameters; this experiment exercised the identical axes in the offline node replica, not a new DDS run. Do not apply these mappings to the original upright bag or guess the signs for an unknown physical mount. `falcon_ros`/`falcon_native` resolve documented driver conventions, not every physical mounting rotation. Auto-calibration stays enabled after the explicit mapping to retain the ordinary tilt behavior.

## Why the suggested guards are insufficient

The forward/rear cone check already precedes bed/rail fitting. It uses X and `hypot(Y,Z)`, which are invariant under these rolls about forward X. The run confirms identical cone counts on every selected input. Reordering that check cannot resolve wall-versus-bed ambiguity.

The wrong empty case is `orientation_confirmed=true` from frame 0; STOP starts at frame 4. **All 509 STOP rows occur while confirmed, and 327 after `status=ok`.** Thus neither an unconfirmed-only guard nor a pending-only block fixes the failure. Suppressing real STOP evidence while calibration is uncertain would introduce a separate safety regression.

The wrong case also reports **GO on frames 311 and 316**, both with `status=ok` and the wrong orientation confirmed. P4's original case-5 JSON contains those same two GOs, so a blanket "side mounts never give GO" statement is not supported. These empty-data rows do not establish a missed real obstacle; they show the unsupported mapping is not reliably identified as such.

[ANALYSIS.md](ANALYSIS.md) explains the source predicates, evidence limits and P3 regression plan. A future automatic fix needs independent up/mount evidence or a carefully validated ambiguity contract. The existing scalar confirmation flag is not a gravity measurement. No arbitrary height threshold, full24 default search, STOP suppression, or replay activation was introduced.

## Reproduction and evidence

- [PROTOCOL.md](PROTOCOL.md) and [registration.json](registration.json): preregistered cases, 2,984-row bound, exact 38-source/native and 746-input hashes, and original P4 snapshot identities.
- [run_mapping.py](run_mapping.py), [execute_mapping.py](execute_mapping.py), [execution.json](execution.json), [run.log](run.log): complete producer and command/exit receipt.
- [summary.json](summary.json): all per-case decisions, intersections, STOP indices/intervals and differences. Both explicit cases have zero changed non-timing rows on both recordings.
- [review_mapping.py](review_mapping.py), [review.json](review.json): separate producer-side saved-row revalidation, including counts, decision reconstruction, exact STOP boundaries, metadata and hash bindings; no detector rerun.
- [HARNESS_REVIEW.md](HARNESS_REVIEW.md): independent acceptance-audit review of the frozen protocol, transform and harness before completion.
- [raw_mapping.tar.gz](raw_mapping.tar.gz), [raw_manifest.json](raw_manifest.json): all eight complete JSONL files, 504,077 bytes, archive SHA `8bc0483a5b10490c8f4515299117737b059078a55c05a29338b15e350556b315`; every member was reopened and verified. Plain originals remain on the machine.

To inspect the archived rows, extract `raw_mapping.tar.gz` into this directory, then run `python docs/evidence/p4_followup_2026-10-18/orientation_analysis/review_mapping.py` with the pinned source tree and metadata available. Registration and the producer intentionally refuse to overwrite an existing measurement. The corrected input bytes are checked in the pinned producer; only serialized output fields, not every internal floating-point value, are retained.

This closes the bounded known-mapping experiment and P3 handoff. L16 automatic side-mount recovery remains open. It does not establish general 24-orientation recovery, a physical remount test, live freshness behavior, new C2 range acceptance, or final P4 approval of the separate 1.2.0 candidate.
