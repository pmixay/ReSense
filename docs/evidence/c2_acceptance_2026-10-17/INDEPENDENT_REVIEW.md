# Independent C2 review — 17 October 2026

**Verdict:** the explicitly selected `clear_range_policy=conservative`, `range_sensor_model=pandar128`
branch profile passes the revised numerical contract and this independent safety review.
The user authorized "Use conservative ranges and record the measured loss" after the choice
disclosed up to 35% loss; the implementation records that limit as a 65% per-bag median-retention
floor. **The original 90% C2 acceptance remains FAIL.**
No unresolved blocking defect was found for this explicit development profile after the
corrections below. `clear_range_policy=legacy` remains the runtime default. This review does
not approve release, real DDS playback, or a full detector/node throughput claim.

The reviewer independently inspected the shared policy, ROS node publication and watchdog
paths, launch configuration, scorer, and tests. The reviewer did not implement those changes.
The reviewer owns this C2 review; the separate N5 scoring implementation is outside this review's scope.

## Independent measurements

The committed P4 archive was authenticated as SHA-256
`417e701deca4bdfe24f7c9d1530c4b78cb8f3d07804386554bda3be44e10223a`.
All six 1.1.0 member hashes plus the historical control in `reproduction.json` matched. The review independently
counted **3,797 captured rows**: Set O's 1,510 and the five empty recordings' 2,287.

A separate arithmetic implementation, without importing the new range helper or scorer,
reconstructed the selected v1 decisions, advisory distance cap, decimetre rounding and
88.7 m small-target cap. Its medians and overclaim counts exactly matched all three saved
reports. The final CLI was then rerun for each report into scratch storage: every semantic
report section matched and `--require-c2` exited **1** for all three.

After the user's instruction, the reviewer independently reran the explicit
`conservative_2026_10_17` command into separate scratch output. The entire resulting JSON
equals `approved_conservative.json`, and `--require-c2` exits **0**. Its four GO and zero
CAUTION measured-envelope overclaims satisfy the fixed 0.5 m diagnostic. Per-bag median
losses are **34.67%, 30.16%, 12.96%, 26.08% and 1.78%**, in the table's order below.
The 65% floor implements the disclosed maximum 35% loss in the user-approved option; it is
not a separate numerical instruction typed by the user. The tradeoff was offered after
measuring these recordings and is not an independent held-out performance guarantee.

The existing `score_clear_distance.py` definition has **505 eligible measured-envelope
object-frames** on this captured Set O run:

| Variant | GO overclaims | CAUTION overclaims | STOP overclaims |
| --- | ---: | ---: | ---: |
| Baseline | 16 | 1 | 2 |
| Advisory candidate | 16 | 0 | 2 |
| Advisory + small-target candidate | 4 | 0 | 2 |

Empty-recording median clear distances, in metres:

| Recording | Baseline | Advisory | Advisory + small target |
| --- | ---: | ---: | ---: |
| doubleT_platform | 120.0 | 78.4 | 78.4 |
| roundT_doubleT | 127.0 | 102.0 | 88.7 |
| roundT_pressureGate_roundT | 98.0 | 85.3 | 85.3 |
| roundT_squareT_pressureGate_squareT | 120.0 | 98.0 | 88.7 |
| squareT_platform_squareT_switch | 84.4 | 82.9 | 82.9 |

Both candidates fail the original 90% median-retention requirement on **four of five** bags.
For fixed v1 advisories, `min(old_clear, nearest_active_advisory)` is already the largest
range satisfying the advisory consistency rule. Additional caps cannot recover these lost
medians. The small-target candidate satisfies the measured-envelope GO/CAUTION numerical
targets by changing the meaning of the exposed range; it does not satisfy the complete C2 card.

The reviewer also independently reconstructed the historical **148/694, including 90 GO**
headline on the archived v1.0.0 control: 694 is the number of **unique eligible scan frames**,
not its 801 eligible object-frames; count a frame if any intended-in-gauge visible plausible
object is exceeded by more than 2 m. This count-compatible definition produces exactly
148 = 90 GO + 57 CAUTION + 1 STOP. The original judge scorer is unavailable, so identifying
its exact implementation from this agreement would be an inference. The explicit reconstructed
definition and the existing 0.5 m measured-envelope diagnostic must remain separate.
For example, the small-target candidate still has **40 GO and 11 CAUTION** overclaim frames
under the reconstructed intended-in-gauge definition; the smaller 4/0 figures are not a claim
about that population.

## Runtime and evidence checks

- The original v1 decision implementation is unchanged; runtime v2 remains rejected.
  Candidate policies are explicit opt-ins. The legacy branch does not run the projection.
- The candidate operates on a copied result after freshness evaluation and STOP-latch handling.
  The scalar range topic, status `clear_distance`, and health range agree. The original detector
  range remains available as `detector_clear_distance`; detections and warnings are retained.
- Active v1 advisories, including columns, cap actual CAUTION rows. Incomplete active advisory
  geometry conservatively gives a zero cap. Health-only CAUTION does not invent object geometry.
- Stale/catchup/error results zero exposed ranges and preserve STOP precedence. Malformed health
  also invalidates candidate ranges. Watchdog status preserves the candidate identity and zeroes
  its range fields. The existing node exception path catches invalid numerical configuration or
  projection inputs and publishes its error/held-STOP state.
- Unknown and Falcon profiles never silently use the Pandar prior: `monitored_small` is null;
  a requested small-target scalar is zero. Sensor applicability is explicitly configured, not
  inferred from a topic name. The operator must configure a matching profile when changing
  sensors; this candidate has no calibrated Falcon density model.
- The accepted profile requires the measured `min_points_far=3` configuration. A different
  threshold is rejected instead of retaining an accepted policy name with a larger range.
  Both decision identity and detection/warning identity are explicit numerical checks.
- `monitored_small` is an expected-return-density prior for a 0.3 x 0.3 m target, qualified by
  monitored range. It is not measured small-object recall or proof of obstacle-free track.
- Input/result copying preserves observed decision, detection and warning rows. This is an
  output projection on archived evidence; it is not a fresh full regression-gate replay.

Review-discovered defects corrected before this verdict:

1. Invalid freshness could leave a contradictory positive health monitored range in the helper.
   It now zeros that range as well as clear/small ranges.
2. Matching truncated labels/results could masquerade as complete Set O. Completeness now
   requires all frame IDs 0–1509 and the canonical Set O label contents; blank/full-frame labels
   cannot erase the positive population.
3. A relaxed scoring tolerance could make the original acceptance appear to pass. The acceptance
   check fixes 0.5 m, and the CLI rejects an alternate tolerance with `--require-c2`.
4. Malformed health could relabel all evidence as FAULT and hide GO/CAUTION overclaims. The
   evidence parser now rejects missing/invalid health levels, and the range helper zeros malformed
   health ranges. These were tooling issues; the existing node already invalidated malformed
   producer health before publication.
5. The accepted profile initially allowed another `min_points_far` value, which could expose
   a longer range under the same accepted policy identity. It now rejects any value other
   than the measured threshold of three; the existing node error path remains fail-closed.

## Verification and limits

Independent final command:

```text
/home/resense/.venv/bin/python -m pytest -q -rs \
  tests/test_range_reporting.py tests/test_score_overclaim.py \
  tests/test_decision_policy.py tests/test_rescore_decisions.py tests/test_node.py
```

Final result after profile hardening and Open3D installation: **238 passed, no skips** in 5.18 s.
The actual node class is exercised against ROS stand-ins, including scalar/
status agreement, invalid freshness, held STOP, unknown/Falcon handling and unchanged defaults.
This does not substitute for a real ROS/Docker replay or CI. Direct probes independently confirmed
malformed-health rejection and alternate-tolerance rejection. Detector seal verification passed
for the existing 36-file seal.

The implementation agent's final combined strict local suite also passed **1,752 tests plus
12 subtests**, with no skips and eight real-data tests deselected by the repository's default
selection; its command, environment and source hashes are recorded in `final_combined_tests.json`.
The C2 runtime/scorer and N5 scorer stayed unchanged during that run. Separate N5 annotation
builder files changed during it, so that record correctly sets `source_unchanged_during_run`
to false. Both affected annotation-builder tests subsequently passed against frozen final
hashes in `final_annotation_followup.json`; pinned lint, parameter sync, detector seal and
whitespace checks also pass. Neither run is GitHub CI or real ROS middleware playback.
The approved numerical report was independently rerun
again after the authorization wording was corrected; its complete JSON still matches.

The measured small helper benchmark excludes decoding, detection and ROS. It cannot establish
the complete node's throughput or fresh-frame acceptance on any CPU count. No held-out dataset,
new ground-truth annotation, or release artifact is covered by this C2 review.

Reviewed source SHA-256 values:

| Path | SHA-256 |
| --- | --- |
| `ros2_ws/src/resense_ros/resense_ros/decision_policy.py` | `7003f70146290666450b8ef8f21630cba3b7457fbb8f588af65badf3d6033fa4` |
| `ros2_ws/src/resense_ros/resense_ros/detector_node.py` | `f47f0ff9d0712d5ddb80e984645dab92c421dea128bd55611ad37b40ebd09515` |
| `ros2_ws/src/resense_ros/launch/detector.launch.py` | `cc017d2397f7aea36d035fd63683dbeac7c75f6499d2b6bedffd9ed61db19840` |
| `scripts/score_overclaim.py` | `51be206b7296378655e1fd69d54fe38abcdec76695c85de64b9f89a73e83be51` |
| `scripts/range_reporting.py` | `90a8d8d2cdf0953d52c3e6d0142cc955cce1b2f439ecc4ac111016f97069d7ea` |
| `tests/test_range_reporting.py` | `ecb27d1693e97fd29091d14933875ac62b83d626374b96df1dd464345bc8f6b3` |
| `tests/test_score_overclaim.py` | `4ccca975e895eee5069ceb9f0a15c1e627ca93c498bf5b7c19a2ce6308abe642` |
| `tests/test_node.py` | `edbc39976f4458a10fd850ccd725133a471c2ec25f677eb6f71853c546e741d4` |
