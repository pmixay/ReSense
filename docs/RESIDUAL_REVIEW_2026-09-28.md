# Residual-event investigation: coordinator closeout

## Outcome

All three research directions are complete for this cycle. **No additional detector candidate is
justified by the measured evidence.** Fresh STOP remains the previously measured default-off
experiment: ride **130/32/31 → 117/27/26** STOP frames/events/episodes, with the previously recorded
set O result **447/9 → 447/9**. This closeout does not add a new full-ride or set O replay.

* [Inventory](RESIDUAL_EVENTS_2026-09-28.md): independently regenerated all **27 events**, **117 node
  STOP frames**, **26 episodes**, **133 STOP track-frames** across 11,271 saved ride frames. All first
  onsets have current mapped support: 18 ordinary and nine low. Saved-default/base semantic parity
  was revalidated by the analyzer; its source-default mapping limitations still apply.
* [Range/shape](EXPERIMENT_RANGE_SHAPE_SUPPORT.md): replayed 12 synthetic approaches with the live
  working-tree tracker. **714/714 evaluation rows** match both saved baseline and saved fresh results.
  Resolved person support is rejected after background connection in eleven frames at 114.8–77.7 m;
  cable support has the analogous loss at 98.4 m. Oracle-only target subsets pass the unchanged
  descriptor. Small edge targets also lack sufficient observed count/height or fail distinct
  low/straddle guards. No runtime subset selector or range gain has been demonstrated.
* [Temporal coherence](EXPERIMENT_EVIDENCE_COHERENCE.md): independently reproduced **467 matched
  transitions**, **nine interval discontinuities across six histories**, and **six gauge-to-gauge
  reset proxies**. These are diagnostics, not six removed events. Whole-cluster intervals in moving
  reference coordinates do not establish body identity. Controlled positive counterexamples show
  delayed onset, while overlapping projections can admit a wrong association. The unfinished
  candidate source changes, config fields and experimental YAML were removed.

The three temporal distances for `1:293` are explicitly distinguished: raw bbox gap **0.560 m**,
fitted center/width gap **0.656 m**, snapshot-support gap approximately **0.635 m**. Association
residual **1.695 m** is inside the **2.357 m** gate; this proves neither correct nor wrong identity.

## Integrated verification

Source revision: `6385ff9804f359624aacb062bad4ed4f42d0e83f`. After candidate removal, `git diff`
contains no substantive tracked-file changes. Existing LF/CRLF-only status entries remain.
New files are research diagnostics, tests, reports and the inventory JSON.

The combined run completed with **228 passed, 1 deselected, 6 subtests passed** in 16.91 seconds.
Repository-wide Ruff passed. The deselected Windows symlink-privilege test is explicit below.
After tightening the reference-movement fixtures to keep sensor-space support fixed, the affected
temporal suite was rerun: **15 passed**; focused Ruff and final `git diff --check` passed.
This test selection is not Linux/ROS release acceptance; the six short organizer recordings remain
unavailable. Instrumented replay timings are not latency evidence. Since no new candidate survives,
there is no additional full-ride A/B or candidate latency result to report.

```powershell
$py = 'C:/Users/alikh/AppData/Local/Temp/opencode/resense-cross-ring-venv/Scripts/python.exe'
$tmp = 'C:/Users/alikh/AppData/Local/Temp/opencode'
$stress = "$tmp/fresh-stop-positive-stress"
$measurement = 'D:/Datasets/ReSense/cross_ring_2026-09-28_measurement'

& $py -m scripts.analyze_residual_events --measurement $measurement --out 'docs/evidence/results/residual_events_2026-09-28.json' --markdown 'docs/RESIDUAL_EVENTS_2026-09-28.md'
& $py tests/test_evidence_coherence.py --measurement $measurement --out "$tmp/evidence-coherence-coordinator.json"

$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
& $py tests/test_range_shape_support.py replay "$stress/setF_edge_base.json" "$tmp/range-shape-edge-coordinator.json" --paired-report "$stress/setF_edge_fresh.json"
& $py tests/test_range_shape_support.py replay "$stress/setF_base.json" "$tmp/range-shape-centre-coordinator.json" --paired-report "$stress/setF_fresh.json"

& $py -m pytest -q -p no:cacheprovider tests/test_fastcloud.py tests/test_lowobj_near.py tests/test_far_thin.py tests/test_stop_keep.py tests/test_history_robustness.py tests/test_cross_ring.py tests/test_detector_freeze.py tests/test_fresh_stop_evidence.py tests/test_low_local_support.py tests/test_far_structure.py tests/test_quality_candidate_analysis.py tests/test_range_shape_support.py tests/test_residual_events.py tests/test_evidence_coherence.py tests/test_stage_trace.py tests/test_false_target_trace.py -k 'not test_symlink_in_detector_scope_is_rejected'
ruff check --no-cache .
git diff --check
```

## Next experiment: local support with a common reference

The remaining research question is whether a **runtime-identifiable local intrusion** can be
separated from connected background and followed across moving fitted references. The current
reports establish the cases needed to test this, but not the selection rule.

1. Capture the actual fresh candidate's input-source flags, onset evidence, point/voxel identities,
   strict/union masks and effective height/axis references with state warmup. Start with the mixed
   2668–2678 window and the compact false bodies `1:74`, `1:298`, `6:331`. Require instrumented output
   equality with the corresponding uninstrumented fresh replay before inferring cause.
2. Express old and new local support under a common reference, separating actual return movement,
   changed visible subsets and reference movement. A gap between whole-cluster boxes is insufficient.
3. Evaluate any proposed runtime decomposition on resolved person/cable positives and those compact
   negatives together. Injection identity is an oracle for evaluation only. Keep unresolved small
   edge targets separate: removing background cannot create missing height/count evidence.
4. Only if that comparison supports a narrow rule, implement an independent default-off candidate
   and pair it with fresh-only on the full available ride/set O and identical centre/edge stress
   draws. Record node STOPs, events/episodes, first/sustained distances, missed intervals, defaults
   parity and uninstrumented latency. Reject a claimed gain that is merely fragmented continuation
   or delayed positive onset.

No physical identity is assigned to the observed false-return surfaces by this closeout.

## Follow-up: direct Fresh STOP trace

The proposed diagnostic was subsequently executed; see
[direct Fresh STOP provenance and local support](EXPERIMENT_FRESH_LOCAL_SUPPORT.md). It validates
the saved fresh output on **9,255 paired ride frames**, including all **27 retained identities**,
**117 node STOP frames**, **26 episodes** and **133 STOP track-frames**, with **439 exact accepted
corridor descriptor replays**. Positive fresh
stress draws also reproduce **714/714** saved evaluation rows. In the exact local comparison, `1:74`
and `1:298` are demoted beyond the effective height reference after isolation, while `6:331`
remains an ordinary gauge body. Person (11 frames) and cable (one frame) positive subsets remain
recoverable in an oracle-scored local decomposition. No runtime selector or new measured detection
gain was demonstrated; the original closeout's next-experiment list records the prerequisites for
such a selector. Final combined verification for this follow-up: **247 passed, 1 deselected,
6 subtests passed**; Ruff and diff whitespace check passed.
