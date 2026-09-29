# Fresh STOP evidence — opt-in tracking experiment

**Status: candidate, default-off, full available-data replay measured; no acceptance claim.**
Source base: `3ba4521` (the 28 September cross-ring false-target trace).

## Motivation

The ride trace contains 11,271 empty-scene frames, 130 alarm frames, 32 track identities/events,
and 31 distinct STOP episodes. The per-event rollup separates 149 alarm track-frames into 78 fresh
strict-gauge, 19 fresh low-object, 13 fresh off-gauge, and 39 missed-track frames. The first alarm
of several event identities occurs on a warning/off-gauge cluster even though an earlier zone vote
has accumulated strict hits. That is a different causal history from a new STOP supported by the
current cluster.

This experiment tests the narrow hypothesis that a new STOP should not be *started* by an old strict
zone vote when its onset-frame cluster is advisory/off-gauge or is only a thin continuation. A real
obstacle can still arrive late: once the current cluster is strict gauge and the bounded evidence
record contains enough eligible hits, the track may start. Low-object clusters count as ordinary
fresh strict evidence because they are a separate real-object mechanism.

## Mechanism and parameters

The candidate is configured in [`configs/experimental_fresh_stop_evidence.yaml`](../configs/experimental_fresh_stop_evidence.yaml):

| Parameter | Dataclass default | Experiment | Meaning |
|---|---:|---:|---|
| `tracking.fresh_stop_evidence` | `false` | `true` | Enable the onset-only provenance check. |
| `tracking.fresh_stop_evidence_window` | `3` | `3` | Number of most recent matched hits retained. |
| `tracking.fresh_stop_evidence_min_hits` | `2` | `2` | Eligible ordinary/low or approaching far-sparse hits required in that window. |

An ordinary or low hit is eligible only when its own cluster is `zone == "gauge"`. A hit supplied
through the separate `far_thin` path is eligible only when the existing approach fit identifies a
consistent approach. A `stop_keep_thin` continuation is recorded separately and cannot create an
onset; its purpose remains continuation of a track that already earned a STOP. The current onset
hit must be strict gauge evidence in all cases, so stale evidence cannot confirm on an off-gauge
frame.

The check runs until a track actually earns a gauge STOP, including when an already reported
advisory track transitions toward the gauge. A blocked advisory report remains visible.
It does not change `confirm_hits`,
`confirm_time_s`, zone votes, `hold_misses`, association, far-ring filtering, or the existing
stop-keep rules. A reported STOP remains reported through the existing reasonable one-miss hold and
can continue through the existing signature/scan-line keep paths subject to their configured cap.

## Available-data measurement

Ran the audited receive-stamp cache with eight independent ride chunks, four NumPy workers
and single-threaded OpenMP/OpenBLAS/MKL. Opt-in command (PowerShell):

```powershell
& 'C:\Users\alikh\AppData\Local\Temp\opencode\resense-cross-ring-venv\Scripts\python.exe' -m scripts.eval_real --cache 'D:\Datasets\ReSense' --out 'D:\Datasets\ReSense\cross_ring_2026-09-28_measurement\fresh_stop_v1' --bags 'new_data,cloud_with_fake_obj' --jobs 4 --chunks 8 --set 'tracking.fresh_stop_evidence=true'
```

| Audited data | Default | Fresh onset candidate |
|---|---:|---:|
| Empty ride false STOP frames / track events / episodes | 130 / 32 / 31 | **117 / 27 / 26** |
| Set O STOP frames / events | 447 / 9 | **447 / 9** |

The five removed ride identities are `new_data_1.jsonl:295`, `new_data_2.jsonl:586`,
`new_data_4.jsonl:210`, `new_data_5.jsonl:146` and `new_data_6.jsonl:250`.
Each baseline onset followed earlier strict support with an off-gauge hit or a miss.
Two overlapping identities do not change the ride's node-level STOP. Among surviving
identities, `new_data_6.jsonl:331` retains its original onset but loses four STOP frames
after a longer gap and off-gauge reacquisition; `new_data_5.jsonl:358` starts one frame
later. In total 13 ride node-decision frames change from STOP to CAUTION/GO. The ride is
confirmed empty by the organizers; for real obstacles, these changes are a recall risk.

Set O's eight in-gauge objects retain exactly the same per-object first STOP frame,
first/sustained STOP distance, alarm frames and missed intervals; `big_outside` still incurs
six false STOP frames. At frame `cloud_with_fake_obj_1131` one warning track disappears,
but the node decision stays CAUTION and clear range is unchanged. Set O lacks physical
ring metadata, although this candidate does not use ring counts.

Additional paired set F *synthetic* positives were ray-cast on 80 consecutive real ride
frames for each of split files 46 and 47 (same frame cache, stamps, seed and sampled
reflectivity; placement `legacy`, no given speed). The exact result files are
`C:\Users\alikh\AppData\Local\Temp\opencode\fresh-stop-positive-stress\setF_{base,fresh}.json`
and `setF_edge_{base,fresh}.json`. In both A/B comparisons every per-kind first range,
sustained range and per-distance-bin hit count matched exactly: centre persons 2/2 at
139.6/141.5 m, centre cables 2/2 at 80.2/92.1 m; edge persons 2/2 at 80.2/104.6 m.
The baseline missed both centre planks; edge 0.3 m boxes and rail objects were detected
only 1/2 and extremely late (~13–15 m). Unchanged poor baseline recall for those
objects is **not** evidence of adequate recall or independent positive acceptance.
Synthetic placement is derived from the scene's track model and cannot test every
single-hit or flickering real obstruction.

The same current checkout with defaults off had **zero semantic frame differences** against
the source base `df24c18` on all 12,781 audited frames. Validated local comparisons and
provenance are in `quality_candidate_defaults_v2.json` and `quality_fresh_stop_v1.json`
under `D:\Datasets\ReSense\cross_ring_2026-09-28_measurement`. Windows NumPy ride total
p95 varied between runs: 116.8 ms for the current defaults versus 104.8 ms for the
candidate; that is not evidence of a production latency improvement.

**Decision:** retain this opt-in candidate for positive/holdout evaluation. The measured
5-event reduction is real on this ride but below the ambitious ≤10-event target. It has
not passed full acceptance and must not change shipped defaults or the detector seal.

## Original impact hypothesis

On the supplied empty ride trace, the candidate is expected to target onset histories whose current
support is warning/off-gauge or whose apparent confirmation depends on stale strict hits. It should
not remove an onset whose current ordinary or low cluster is strict gauge, and it should not remove
an approaching far-sparse onset supported by the existing approach rule. The trace's far summary
shows 13 of 15 far events beginning with multi-ring strict support, one with single-ring strict
support, and one with no fresh strict corridor support; therefore a ring-count threshold is not the
mechanism being tested here.

The numbers above are diagnostic counts, not a predicted reduction. The trace has no real-obstacle
labels, and multiple track identities can alarm on the same frame. Measure event count, STOP
episodes, per-frame onset changes, and continuation fragmentation before judging the candidate.

## Focused verification

Use the specified Windows environment:

```text
C:/Users/alikh/AppData/Local/Temp/opencode/resense-cross-ring-venv/Scripts/python.exe -m pytest -q tests/test_fresh_stop_evidence.py tests/test_far_thin.py tests/test_stop_keep.py tests/test_history_robustness.py
```

The new tests cover:

- a stale gauge vote followed by an off-gauge onset and a later strict late arrival;
- low-object strict evidence;
- an already earned STOP through one missed frame and subsequent reacquisition;
- approaching versus static `far_thin` evidence and ordinary-cluster onset;
- thin continuation not confirming an unreported track;
- default-off dataclass and independent YAML loading.

## Limits and integration needs

- This is not a detector acceptance result. The local A/B includes synthetic-object scoring,
  but still lacks recall and range evidence for the six short organizer recordings.
- The two-hit/three-hit window is a bounded policy choice. A real object visible in only one strict
  frame, or an object whose strict evidence flickers while it approaches, may remain advisory until
  another eligible hit arrives. That risk must be measured against labelled obstacle bags.
- One missed frame is preserved by the existing `hold_misses` path; longer occlusion, calibration
  reseed, and shape demotion still follow their existing limits. The candidate does not globally
  disable or extend any of those paths.
- The far-thin distinction is based on tracker input provenance. It does not infer physical sensor
  identity, and it does not repair off-gauge association or a wrong track identity.
- The full **available-data** replay and paired set F positives are reported above. Run the
  missing-bag Linux quality screen before considering any default integration: compare
  source-base semantic frames, alarm events and STOP episodes, onset reasons, missed
  intervals, real and synthetic-object first/sustained STOP coverage, monitored range,
  history stress and native/node latency. Keep defaults, the detector seal, and acceptance
  records unchanged until that review.
