# Independent orientation-readiness and startup-history review

Reviewer: `c2_implementation`, independent of the N2 implementation author.
Review date: 2026-10-18. The source review covers the registered N2 protocol,
readiness guard, bounded history, configuration and explicit profile resolver.
It does not replace the final full regression gate or authorize a release/seal.

## Finding and correction

The original `f5ff15f` history counter was not a conservative bound for all
accepted metadata. Python's `deepcopy` can allocate more list capacity than the
input. A valid empty frame with 600 unique five-element metadata lists passed a
scaled 65,536-byte limit while retaining at least 78,108 bytes; its source charge
was 64,736. The ordinary node decoder's scalar `n_raw`/`n_near` metadata does not
exercise this defect.

Commit `7b7b02c` corrects the bound before copying by reserving container growth
and charging independently copied arrays/metadata separately. It then verifies
actual retained allocation. Frame count, timestamp/identity checks, orientation
adoption, detector thresholds and publication semantics remain unchanged. The
independent original probe now rejects with `byte_budget`. A separate 216-case
list/dict/tuple sweep accepted 161 cases with no retained-size violation, including
Frame and wrapper storage; the smallest accepted reservation slack was 505 bytes.

Four original startup frames each from real `doubleT_obstacle` and Falcon were
fed into both old and corrected buffers. Capture/discard decisions and saved
array hashes are identical. Only conservative charges changed: two obstacle
frames 24,542,114→24,542,818 bytes; four Falcon frames 12,140,240→12,141,712 bytes.
The review approves this correction. Evidence and exact source hashes are in
[the review receipt](orientation_replay_candidate/independent_source_review.json).

## Source and evidence checks

- Unconfirmed orientation adds a decision warning and zeroes trusted/clear
  range. Existing input errors retain FAULT priority; obstacle evidence retains
  STOP priority. Disabled automatic calibration intentionally trusts explicit
  coordinates. Final tilt fitting is distinct from orientation confirmation.
- Replay uses only owned, original startup inputs, including the current input
  in the four-frame/32 MiB cap. Nonfinite/nonincreasing stamps, gaps over one
  second, changed frame identity, reset, overflow and late adoption discard
  history. Unsupported instrumented subclasses are explicitly diagnosed.
- Only an already validated discrete rotation seeds a fresh detector. Buffered
  inputs run through the unchanged processing stages in original order, and
  only the current result/stamp is returned. There is no recursive adoption
  replay or publication of past results. Scene reset clears pending history;
  changing sensor profiles creates a fresh node detector/calibrator.
- Physical-call timing includes replay. Health retains physical latency samples
  rather than treating internal replay iterations as new received calls. The
  one-time shared-host wall measurements remain diagnostics, not throughput.
- Explicit profiles reset fixed mount angles and axes, retain supported
  upright/inverted search, and distinguish ROS/native Falcon coordinates.
  Falcon never receives a Pandar small-target density model.

The reviewer independently read and verified all 1,809 archived obstacle records
(baseline plus eight mappings), including each summary hash and frame index.
Every case has exactly 193 STOP rows at frames 8–200. All post-adoption serialized
decisions, detections, warnings and nearest/clear/monitored ranges match baseline;
every pending remount output is CAUTION/FAULT with zero range. The four-decimal
archived stamp matches the current replay stamp. Tiny unrounded track-coefficient
differences remain disclosed rather than included in an exact-equality claim.
This is an independent artifact comparison, not another full detector replay.

The readiness/history tests also cover owned arrays and metadata, frame/byte
limits, discontinuity/reset, empty/FAULT input, late adoption and subclass
handling. The source guard/node tests retain STOP/FAULT precedence. No test or
acceptance threshold was weakened by this review.
The author's [149 affected tests](orientation_replay_candidate/bound_fix_tests.json)
passed in 36.90 seconds after the correction. The independent checks above were
run separately. A new eight-orientation real-recording replay is pending at this
review point; earlier measurements retain their original source identity.

## Remaining acceptance limits

The corrected core requires the complete default gate and source-seal workflow.
The earlier full host suite, Docker/DDS and display measurements retain their
original source versions; they are not retroactively relabeled as the corrected
build. Recorded ordinary-input buffer parity explains the narrow correction.

The eight supported remounts are distinct from the experimental 24-way automatic
search: wall-as-floor false acceptance remains a documented limitation. Explicit
24-way coordinate mappings are tested, not general 24-way automatic safety.
Falcon static alarms, uncalibrated density and raw annotation uncertainty remain
open as already reported. No physical dust or surveyed corridor truth is added
by this source review.

Reproduce the independent archived comparison and memory probe from the repo:

```sh
python docs/evidence/n2_falcon_2026-10-18/review_orientation_history.py \
  docs/evidence/n2_falcon_2026-10-18/orientation_replay_candidate --out /tmp/orientation-review.json
python docs/evidence/n2_falcon_2026-10-18/review_orientation_memory.py \
  --source "$PWD" --out /tmp/orientation-memory.json
```
