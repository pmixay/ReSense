# H2: resolved horizontal support for structure-cut fragments

**Owner:** P3. **Measured candidate:** `eba9761` on `h2/cut-bar`, from
`d0d17bb` (`final/silent-misses`). **Status:** full gate PASS; P4 independent
review and P1 integration/reseal remain outstanding.

## Defect, acceptance first, change

Eight occupied voxels on a single vertical scan column could pass the cut's
point bar as a body. Duplicate echoes do not provide another horizontal
observation. The acceptance tests and physical threshold were committed
before the patch: `8ddc17f`, corrected/extended by `b34cd24` and `d0b2685`.
The first test reproduced the defect; its resolved-face control passes.

[`protocol.md`](protocol.md) registers the threshold. In
`resense/clustering.py::_off_structure_parts`, a part that already passes
the eight-voxel bar must also span **one full sensor azimuth step, 0.1 deg**
in its raw coordinates (two resolved columns). This is independent of echo
multiplicity and voxel origin. The existing height, length, surface-fit and
corridor/column rules still apply. Ordinary clusters do not use the new bar.

## Reproduced node-path checks

The original judge/safety-review drivers were run on freshly node-decoded
organizer bags. Every code used the same sealed baseline axis and the same
recomputed ICP. The unmodified 14.10 control reproduces the reported 82.8 m
person result and the two false mast hits. Provenance and command details:
[`provenance.json`](provenance.json).

| check | seal | 14.10 control | H2 |
|---|---:|---:|---:|
| C mast 1.2 m proud: object-matching STOP frames | 0 | 2 | **0** |
| C person: first matching STOP, m | 73.94 | 82.77 | **82.77** |
| C person: matching STOP frames | 49 | 55 | **55** |

Exact initial results: [`initial_checks.json`](initial_checks.json).

* **20 wall-anchored cases** from `battery2.sh.txt` and `battery5.sh.txt`:
  zero new wall-object matching STOP frames relative to the seal, zero lost
  matching STOP frames on the axis-object controls
  ([`wall_battery.json`](wall_battery.json)). This includes cabinets, persons,
  masts, a signboard, a column with a dark top, object/equipment pairs, and
  the two sides of B.
* C **30% dropout** and **5 Hz**: **zero retained cut parts / cut candidates**.
* **Full regression gate:** exit **0**, no `--allow`, against
  `regression_baseline_2026-09-29_shell_off.json` ([`gate.json`](gate.json)).
  The local unmodified control reproduced that baseline first.
* **15,269 frames / 15 outputs:** zero changed obstacle/warning flags,
  detections, warnings, nearest/clear distance, candidate count or track
  against the local `final/silent-misses` control
  ([`frame_diff.json`](frame_diff.json)). Timing/latency health telemetry is
  excluded; Set F metrics are covered by the full gate.

## Tests

With the worktree pinned by both `PYTHONPATH` and `RESENSE_REPO`, native loaded,
and `RESENSE_REQUIRE_SYNTHETIC=1`:

* `python -m pytest -q tests/test_structure_cut.py tests/test_column_free_top.py tests/test_native.py`
  -> **48 passed**.
* `python -m pytest -q tests/test_envelope.py tests/test_modules.py tests/test_late_candidates.py tests/test_cross_ring.py`
  -> **123 passed**.
* `python -m ruff check resense/clustering.py tests/test_structure_cut.py`
  -> **all checks passed**.

No test was skipped in these runs. The acceptance cases include echo
duplication, reflected/input-reversed single-column fragments, a resolved
face control, and the original voxel-count and rule-wiring checks.

## Handoff

P3 offers `eba9761` plus this evidence to P1 for H3. H2 has not been combined
with H1 or `r3/axis` here: the combined committed code still needs H3's gate
and H4's independent review before H5 creates a new seal.
