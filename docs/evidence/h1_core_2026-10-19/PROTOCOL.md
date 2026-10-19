# H1 positive collision core — registered 19 October 2026

P3 branch `det/h1-positive-core`, base `9621024fcced776f157bd68471a4995c38f7dfd7`.
This is a new candidate; the withdrawn free-top feature stays disabled. No G3.

## Hypothesis and candidate A (before production edits)

An observed tall body inside the collision envelope must not become harmless
solely because it has a column's shape or continues above the envelope. Missing
upper returns are not evidence. Test an exemption from **only** the column shape
signature, based on current-frame points of the candidate:

* At least eight occupied voxels, spanning at least 2.2 m vertically, with the
  lowest supported point at/below 1 m above the rail head.
* Observed footprint at most 0.8 m in each horizontal dimension.
* The supporting points pass both ordinary strict membership and a **rail-relative**
  envelope eroded by an additional 0.30 m, retaining the existing range-growing
  edge margin. Sensor-reference unions cannot supply rail support. Historical
  points, duplicate echoes, and a detached upper part cannot supply the core.
* Existing axis/height validity, other shape filters, confirmation time, zone
  votes, doubt and ego-motion guards remain. First test without a special tracker
  release; register any necessary release change separately.

This changes the previous read-only proposal: it requires an **interior subset**,
not the entire body to be inside with an assumed 3 cm error. The erosion is a
specified robustness budget, NOT a measured/calibrated runtime axis-error bound.
Systematic axis errors beyond the tested budget remain an explicit limitation.

## Acceptance

1. Independent physical slab caster reproduces archived case45 (84 raw object
   returns, 80 candidate voxels, 20 rings, exact source XYZ hash). At 67 m the
   opaque 3.22 m body and its mirror become matched STOPs after ordinary temporal
   confirmation. Repeat opaque-to-vault, absorbing continuation and occluding beam;
   every body physically entering the envelope is a positive, not infrastructure
   merely because its upper face is dark. Print observed raw coordinates/counts.
2. Sweep 37/67/109/137 m, both sides, several physical tops; report every miss.
   Fully outside controls use inner face >=1.05 m, including near-edge cases, with
   analytical truth independent of fitted coordinates. Under supplied lateral
   model errors -0.30..+0.30 m no outside body gains a core or a new matched STOP.
   Larger errors are measured as limits, not silently excluded successful trials.
3. Boundary controls: missing core, unknown/reversed rings, duplicates, historical
   accumulation, union-only membership, beyond-axis/height, long/deep structures.
   Feature-off reproduces base behavior. Test missed-frame return and prior
   column histories; no unobserved free-top evidence or one-hit history reset.
4. Full original gate, no overrides/waivers. Fresh same-input base control;
   preserve every previous matched positive and STOP, not just aggregate counts.
   Five empty recordings and the complete ride gain **zero** STOP frames/episodes.
   X3 40 cases; no lost matched positives; no new empty-recording STOPs.
5. Retain A-axis, C-person, R3 E6/hanging and all 4,443 actual Falcon outputs.
   If outputs change, inspect each added/lost detection and its physical context.
6. Audit results independently from serialized/raw rows, exercise comparators on
   planted differences, inspect raw examples; traced/plain outputs must match
   outside registered wall-clock telemetry. Reject failed candidates, preserve
   their exact sources/results. Report author acceptance separately from P4.

No braking-sufficiency or 100 m detection guarantee follows from these component
criteria. Record physically supported detection ranges and remaining limits.
