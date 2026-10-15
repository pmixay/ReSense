# C1 base decision policy / additive status contract (15 October 2026)

Status: implemented proposal, **v1 remains the default**. v2 is an explicit opt-in
for measurement and captain review after final 1.1.0 column semantics. This is not
organizer approval or a claim that the C1 acceptance checks have passed.

## API

```python
from resense_ros.decision_policy import DecisionPolicy, decision, evaluate_decision

policy = DecisionPolicy(version="v1", caution_distance_m=80.0, compact_max_size_m=3.0)
word = decision(result, policy)                 # str: GO / CAUTION / STOP / FAULT
answer = evaluate_decision(result, policy)      # immutable PolicyDecision
status.update(answer.to_dict())                # additive, JSON-ready fields
```

Both entry points take a `FrameResult` object or serialized mapping. They do not
import `rclpy`, numpy or `resense`, mutate input, inspect clocks, change detector
parameters, update tracking, cap clear distance, or implement a STOP latch. The
word-only API also accepts `"v1"` / `"v2"`. Unknown versions and non-positive or
non-finite configuration raise configuration errors; they never silently select
another version.

Source observers load their own checkout's policy by absolute path through
`scripts/decision_policy_import.py`, independently of the selected detector or an
older installed ROS overlay. An already imported node module is never replaced.
The synthetic evaluator records the observer policy path/hash separately from
the selected detector hashes. If no source policy exists, the helper uses the
installed `resense_ros.decision_policy`.

The backend imports the installed policy first, with an explicit local-source
fallback for checkout use (including older overlays missing the policy module).
Its wheel declares `resense-ros>=1.0.0`; the existing ROS Python distribution must
be provided alongside root/backend wheels. The local launcher and CI install all
three projects. No sourced ROS runtime / `rclpy` is needed for pure policy use.
See `webapp/backend/README.md` for local wheel installation and the isolated
`scripts/check_webapp_wheels.py` verification.

## Semantics

1. A valid true `obstacle` wins **STOP**, even with bad health or no current boxes.
   Only the detector / caller confirms gauge objects: policy never promotes boxes.
2. Health `level == error` gives **FAULT** even when `decision_level == ok`.
   Invalid flag types, malformed health, unknown health levels, and an error in
   `decision_level` also give FAULT. These are untrustworthy input, outside the
   well-formed historical v1 domain. Missing legacy flags default false, missing
   or null health defaults to `{}` / ok. In particular `{}` retains legacy GO.
3. A health `decision_level == warn` retains **CAUTION** in both versions. Missing
   `decision_level` falls back to `level`. Latency-only warn with explicit
   `decision_level == ok` is not promoted to CAUTION.
4. v1 retains the original aggregate `warning -> CAUTION`, regardless of details.
5. v2 examines confirmed `warnings` **when aggregate `warning` is true**:
   - `column`: suppressed, relying on reviewed 1.1.0 column semantics;
   - `beyond_axis` / `beyond_height_ref`: retain only if compact;
   - empty reason `""` (the detector's margin advisory): retain at distance <= D_c;
   - `doubt`: always retain, at any range / size;
   - all other / future named reasons: retain for compatibility;
   - missing or unusable evidence required for a suppression: retain CAUTION.
6. Otherwise **GO**. GO is a base decision, not a claim of trustworthy freshness
   or guaranteed absence of objects beyond the detector's monitored range.

The proposed compactness definition is **three finite, positive bounding-box
extents, each <= 3.0 m**, inclusive (configurable). This numeric definition was
not fixed in C1's prose; it is explicit here for review, not inferred from the
card's historical percentages. D_c starts at 80 m, inclusive. No lateral geometry
or axis uncertainty is re-estimated by policy. Object-to-JSON rounding may move a
value very close to a boundary across it; offline rescores use the saved numbers.
Invalid / missing distance or box size cannot prove an advisory suppressible.

## Additive `caution_reason` contract

`PolicyDecision.to_dict()` emits:

```json
{"decision": "CAUTION", "decision_policy": "v2", "caution_reason": ["doubt", "health_warning"]}
```

- `caution_reason` is **always an array of strings**, sorted, deduplicated. It is
  empty on GO / STOP / FAULT, even if lower-priority warnings also exist.
- Codes: `advisory_object` (v1 aggregate warning, or another retained v2 reason),
  `health_warning`, `doubt`, `margin_object`, `compact_range_object`,
  `incomplete_advisory` (v2 lacks evidence for suppression).
- These are categories, not free-form health messages, track IDs or object-match
  claims. Details remain in `health.messages` and the original `warnings` list.
- Existing `obstacle`, `warning`, boxes, ranges and health keep their detector
  meanings. A suppressed v2 warning may therefore coexist with GO; consumers use
  `decision` for the base answer, and must not rederive it from `warning`.
- Old status files have no `caution_reason` / `decision_policy`. Displays should
  treat absent reasons as unavailable, not as proof that no CAUTION cause exists;
  preserve the published decision. Unknown future reason codes should display
  generically. Word-only consumers keep the existing callable names and v1 output.

## Parent node/launch integration (outside this commit's ownership)

Suggested launch PARAMS / node runtime parameters (not sealed YAML):

| parameter | default | passed to |
|---|---|---|
| `decision_policy` | `v1` | `DecisionPolicy.version` |
| `caution_distance_m` | `80.0` | `DecisionPolicy.caution_distance_m` |
| `caution_compact_max_size_m` | `3.0` | `DecisionPolicy.compact_max_size_m` |

Validate the policy once when initializing / changing parameters, then reuse the
immutable instance. Keep a compatibility `DetectorNode.decision(res)` delegating
to `decision(res)` if existing callers require it. In `publish`, after existing
freshness health projection and held-obstacle projection:

```python
answer = evaluate_decision(res, self.decision_policy)
word = answer.decision
status.update(answer.to_dict())
```

Keep all freshness checks, source/residence-age guards, range invalidation,
watchdog/error handling, latch acquisition/release and `go_allowed` logic in the
node. Do not pass the unprojected raw result to policy and thereby release a held
STOP. For watchdog / processing-error snapshots, use the node's final held STOP /
FAULT decision and add `decision_policy` plus `caution_reason: []`; do not pretend
these snapshots are detector frames. The node owns the proposed <= one-input-period
catch-up freshness rule and its tests. Policy cannot remove freshness CAUTION by
discarding health warnings. P2 owns display use of the additive reasons.

The five existing offline/backend consumers use default v1 through the shared
function; `analyze_cross_ring_measurement` also keeps its geometry comparison and
now includes the shared decision so a health-only answer change is visible.
`scripts/rescore_decisions.py` supplies the explicit v2 evaluation path.
