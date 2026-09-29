# Complete detector timing: registered contract, 28 September 2026

Registered before production edits on branch `improvement/complete-timing-20260928`.
Parent: accepted health histogram commit `5fa978f59d4e787bce04da3ab9b4257f5474d772`;
the measured production source is `ef71c9dc4f88147327dcb41ea79358dfc690ba77`.
Source SHA-256: `c0273a13a67ab4872dab00154caa75f6b30f50416775062c591fbb47906a0fa4`.
Effective default config: `22a30ff265035e06358a21696cfb8bc61b598d16e5a64aa3536abfefbc4bd5fb`.
Native library: `b5a5c2dc08be8fa1ab00e27dee7662d31413a99f819a760d2d2d4b16b93e8534`.

## Problem and intended behavior

`Detector.process` currently stops `timing_ms.total` before mount serialization, health
monitoring and result construction. It also sends that incomplete interval to health.
This change corrects the measured interval; a larger reported time is not a regression in
execution speed. Existing evidence keeps its original timing definition.

- Keep all six existing stage intervals. Add `timing_ms.stages` for their sum, exactly the
  previous `total` interval (entry through tracking and clear-cap computation).
- Add `health` from the end of tracking through mount serialization and one health update,
  and `result` for constructing `FrameResult`. Set `total` at the clock read immediately
  after result construction: `stages + health + result = total`. The final timing-field
  assignments and return are outside this internal measurement.
- Health uses the previous completed call's unrounded `total`, with one sample per next
  processed frame. The first call after construction/reset has no completed sample:
  `latency_p95_ms = 0`, no latency warning. No synthetic zero enters the history.
  The existing ten-sample warning threshold therefore first applies on result 11.
  The last call enters health history only if another call follows. The configured window
  retains at most that many completed samples; reset clears history and the pending sample.
- Detector health results declare `latency_basis: previous_complete_process` and
  `latency_sample_age_frames: 1` when a previous completed sample was supplied, otherwise
  `null`. Numeric direct health callers keep their output contract. Consume the pending
  sample at entry so an exception cannot label an older call as the previous frame.
- Preserve numeric `HealthMonitor.update(..., latency_ms)` behavior. Extend this argument
  to accept `None` for no new latency sample. Run health once per frame; do not repeat its
  point, lock or floor-shadow updates to amend timing.
- `latency_affects_decision` remains false by default. With true, warnings may change
  because the measured interval now includes health, and they arrive one result later.
  Non-latency warnings, faults, detections, track/mount state and range estimates must stay
  unchanged. Document this intentional monitoring behavior change in the release notes.

`node.detect_ms` wraps the complete call, including the final writes/return;
`node.decode_ms` measures decoding and `node.latency_ms` measures decode plus detection.
End-to-end result latency additionally includes transport, scheduling and publication and
must continue to be measured by the node/player capture. These quantities are distinct.

## Acceptance and scope

1. Deterministic clock tests inject slow health and result construction. Require complete
   coverage, preserved stage duration, and no double counting. A slow health call must
   appear exactly once in the next health history; no sleep-based timing assertion.
2. Test both latency decision policies, ten-sample warm-up, window eviction, reset and
   numeric health callers. Verify point/rail/floor counters update once per frame.
3. Compare non-timing outputs for representative clear, warning and fault sequences with
   the prior numeric-latency call behavior. Use the existing calibration/node policy tests
   to verify default decisions and explicit opt-in warnings.
4. Run focused timing, health and relevant node tests in `resense-cycle-dev`, with
   `PYTHONPATH` selecting this checkout. Preserve command, output, source and config hashes
   under `/home/likikikpa/ReSense-cycle-data/complete_timing`.
5. The parent agent coordinates any full native gate, complete history comparison or quiet
   ROS runtime check. This isolated task makes no new full-gate, runtime, recall or score
   acceptance claim. Native source, configs and all detection rules stay unchanged.

No edits to the primary worktree and no push are part of this task.
