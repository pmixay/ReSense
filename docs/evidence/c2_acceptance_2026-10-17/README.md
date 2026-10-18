# C2 conservative profile — approved 17 October; original profile FAIL

The user explicitly chose **“Use conservative ranges and record the measured loss.”**
The revised `conservative_2026_10_17` profile passes the measured-envelope targets
and a **65% minimum retained median clear range** on each empty recording (35%
maximum loss). This guard implements the tradeoff disclosed in the approval
question; the measured worst loss is 34.7%. The
instruction, bound and scope are recorded in
[ACCEPTANCE_PROFILE.json](ACCEPTANCE_PROFILE.json); the reproducible result is
[approved_conservative.json](approved_conservative.json).

Use `clear_range_policy:=conservative range_sensor_model:=pandar128` to select it.
The launch default remains `legacy` until release/DDS integration; no release or
deployment is claimed. The node and offline scorer use exactly the same range
function. Decision policy remains **v1**; GO/CAUTION/STOP/FAULT decisions and
detection tracks are unchanged.

The original C2 targets cannot all hold with v1: even the *largest*
range consistent with every active advisory loses more than 10% of median clear
range on four of the five empty recordings. Adding a small-target cap can only
shorten those ranges further. The original **90%** retention profile is preserved
and still fails. The separately named approved profile does not rewrite that result.

## Measured results and the two score definitions

Every row comes from the complete, archived, sealed 1.1.0 outputs: **1,510 Set O
frames and 2,287 empty frames**. Inputs and archive members are identified in
[reproduction.json](reproduction.json). This is deterministic postprocessing of
saved results, not a new detector run or a full regression gate.

The unchanged [`score_clear_distance.py`](../../../scripts/score_clear_distance.py)
counts **object-frames**. Its target is visible, plausible, organizer-intended
in-gauge objects with at least one return in the measured rail envelope; excess
must exceed **0.5 m**. There are **505 target object-frames** (801 intended
object-frames before applying the measured-envelope condition).

| Output | GO target overclaims | CAUTION target overclaims | STOP target overclaims |
|---|---:|---:|---:|
| Sealed 1.1.0 | 16 | 1 | 2 |
| Advisory candidate | 16 | 0 | 2 |
| Approved conservative / small-target output | **4** | **0** | 2 |

The new scorer reports this definition **and** a reconstructed historical judge
definition. The original 13.10 scorer is absent, but counting **unique scan
frames**, with any visible/plausible organizer-intended in-gauge object exceeded
by **more than 2 m**, reproduces **148/694 (90 GO)** exactly on the durable v1.0.0
control capture. The 694 frames contain 801 object-frames. This is an explicit
count-compatible reconstruction, not a claim to have recovered the original code.

| Output | Historical-definition total / 694 | GO | CAUTION | STOP |
|---|---:|---:|---:|---:|
| v1.0.0 control | 148 | 90 | 57 | 1 |
| Sealed 1.1.0 | 147 | 90 | 56 | 1 |
| Advisory candidate | 106 | 90 | 15 | 1 |
| Advisory + small-target candidate | 52 | 40 | 11 | 1 |

[Historical reconstruction](historical_reconstruction.json) retains all counts.
The smaller measured-envelope score must **not** be presented as solving all
organizer-intended cases. Objects intended inside but lying outside the fitted
rail envelope still contribute to the historical score. A revised coverage limit
alone would not eliminate that distinction or close those residuals.

## Empty-recording coverage conflict

| Recording | 1.1.0 median, m | Advisory cap, m | With small cap, m | Small-cap change |
|---|---:|---:|---:|---:|
| doubleT_platform | 120.0 | 78.4 | 78.4 | −34.7% |
| roundT_doubleT | 127.0 | 102.0 | 88.7 | −30.2% |
| roundT_pressureGate_roundT | 98.0 | 85.3 | 85.3 | −13.0% |
| roundT_squareT_pressureGate_squareT | 120.0 | 98.0 | 88.7 | −26.1% |
| squareT_platform_squareT_switch | 84.4 | 82.9 | 82.9 | −1.8% |

The cap applies only on CAUTION frames, using the shared active-advisory predicate;
health-only warnings do not invent an object distance. Under v1 every confirmed
warning is active, including columns and range demotions. It would be inconsistent
to retain their CAUTION output but exempt them from the cap.

For each frame let `M = min(original_clear, nearest_active_advisory)` where an
active advisory exists, otherwise `M = original_clear`. Every non-lengthening
range consistent with the requested advisory cap is at most `M`. Its median can
therefore be no larger than the advisory-candidate median above. Four medians are
already below 90% of the original, so no additional conservative cap can pass the
original coverage condition. This is a constraint conflict, not a rounding issue.

## Output contract

- `advisory_candidate`: cap only at the nearest warning responsible for CAUTION.
  Missing/nonfinite active-advisory geometry gives range 0. Health-only CAUTION
  gives no geometric cap. This uses the same predicate as `evaluate_decision`.
- `conservative` (and the retained `small_candidate`): additionally cap clear range at `monitored_small`. The
  existing Pandar `expected_points(d, 0.3, 0.3) >= cfg.cluster.min_points_far`
  prior gives **88.762 m** for threshold 3; conservative decimetre output is
  **88.7 m**, further bounded by the frame's monitored range. The calculation is
  cached by sensor model, threshold and configured maximum range.
- The prior predicts ideal return density. It is **not measured detection range,
  evidence that the track is empty, or a braking guarantee**. All four residual GO
  object-frames are still listed: small_center 318 and small_on_rail 392/394/396.
- Sensor applicability is explicit: `range_sensor_model:=pandar128`. Falcon Prime
  and unknown profiles return `monitored_small: null`; requesting the small-target
  candidate then reports clear range 0, never a silently reused Pandar model.
  Topic names, frame names and the presence of a ring field do not select a model.
- The node preserves `detector_clear_distance`, and publishes the same candidate
  clear range in its scalar topic, status JSON and health mapping. Freshness faults,
  watchdogs and held STOPs keep exposed ranges invalid. Default behavior is unchanged.

Approved profile, explicitly selected on a Pandar recording:

```bash
ros2 launch resense_ros detector.launch.py \
  clear_range_policy:=conservative range_sensor_model:=pandar128
```

## Reproduction and validation

```bash
python docs/evidence/c2_acceptance_2026-10-17/reproduce.py --inputs /tmp/resense-c2-inputs
python scripts/score_clear_distance.py /tmp/resense-c2-inputs/small_candidate.jsonl \
  --gt labels/cloud_with_fake_obj.json
python -m pytest -q tests/test_range_reporting.py tests/test_score_overclaim.py \
  tests/test_decision_policy.py tests/test_rescore_decisions.py tests/test_node.py
python scripts/detector_freeze.py verify
```

The three original `--require-c2` screens intentionally exit **1**. The fourth,
explicit `--acceptance-profile conservative_2026_10_17`, exits **0** with the
qualified Pandar cap and revised 65% retention floor. It requires the Pandar
expected-return prior and the evaluated threshold of 3; approval does not waive missing recordings or change
the target population. The scorer refuses a changed tolerance for either profile, missing
or malformed evidence, duplicate frame indices, truncated recordings, or substituted
Set O labels. It retains the legacy scorer's target counts and publishes every
residual. [`legacy_scorer_small_candidate.json`](legacy_scorer_small_candidate.json)
records the separate legacy CLI result on the emitted candidate JSONL.

The final combined local suite passed **1,752 tests and 12 subtests**, with **0
skips** and **8 explicitly deselected** tests requiring unavailable recorded
fixtures. `RESENSE_REQUIRE_SYNTHETIC=1`, Open3D and the native extension were
enabled; see [final_combined_tests.json](final_combined_tests.json) and
[final_combined_tests.txt](final_combined_tests.txt). Two N5 annotation-builder
files received formatting/import edits during that run; the source-hash drift is
retained in the report, and their **2 affected tests passed** again after the
files were frozen: [final_annotation_followup.json](final_annotation_followup.json).
C2 source stayed unchanged during the full run. The focused approved-profile
suite also passed **238 tests, 0 skipped**; [approved_profile_tests.json](approved_profile_tests.json)
and [approved_profile_tests.txt](approved_profile_tests.txt) record that result.

The node tests execute the actual node class with ROS message/transport stand-ins;
they verify scalar/status parity, raw-range preservation, active warnings,
unknown/Falcon profiles, freshness invalidation and the STOP latch. They are not
a DDS playback or Docker integration run. The detector's 36-file seal still
verifies (`db3f588d…d751`); no sealed detector file changed and no new full gate is
claimed here. [Independent review](INDEPENDENT_REVIEW.md) records separate findings.

The approved projection was also applied to **all 59 archived 1.1.0 JSONL
captures, 42,536 rows**, including all X3 variants and retained attribution
captures. Every decision/detection/warning row remained unchanged, and no clear
range lengthened: [archive_parity.json](archive_parity.json), reproduced by
`python docs/evidence/c2_acceptance_2026-10-17/check_archive_parity.py --scratch /tmp/c2-parity`.
This validates the output projection over archived evidence; it does not claim a
new detector gate or real-time ROS replay. Pinned CI lint, parameter-copy sync,
seal verification and whitespace checks are recorded in
[integrity_checks.json](integrity_checks.json).

[benchmark.json](benchmark.json) measures warm range projection only on the actual
**one available CPU**, while other work was active. Its model cache has one miss
and 6,000 hits. It excludes decode, detection and ROS and does not establish 10 Hz
end-to-end performance or predict performance on 2–4 or 8 cores.
