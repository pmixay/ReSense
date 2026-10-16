# Independent H4 correctness review — registered before measurements

Reviewer role: fresh independent correctness reviewer; no authorship of the implementation.
Registration target: `7cc640fb39698b1fe45bc6ab069eab68ad4ac6ae` on
`integration/2026-10-15-16`. H3 measured core:
`f8c088dc4f3243fbd15a3aae9be0459e8a0aa941`; sealed control:
`707ea9cda051369326fb9407c42488c1033dad76`.

## Scope and boundaries

- Read the complete baseline-to-target config/detector/track/tracking/health changes,
  clustering interfaces, config synchronization, evidence import and metadata wiring.
- Check all 36 H3 inventory hashes against target Git blobs and the Linux filesystem.
- Independently inspect the final shipping node at `d4850c5`: published defaults and
  16 queue/clock/continuity methods, shared v1 policy, invalid raw result projection,
  STOP latch/freshness, v2 rejection and removal of shipping S1 behavior.
- Inspect H3 range equations and the one unreported candidate promotion from retained
  evidence; authenticate relevant packaged and external evidence hashes/import paths.
- New work stays in this folder. Return implementation defects for an author to fix.
  No changes to implementation, versions, seals, manifests or existing tests.
- No held-out G3 data or tests. Only deterministic synthetic scenes and, if needed,
  A/B/C/S development data. Independent clustering positive/negative probes belong to
  the other reviewer and are excluded from this review's new measurements.

## Registered execution

Use the installed tools image by immutable identity:
`sha256:5e2659e8f8d3a7e9f64d7c269ae920badd86b8a388e48e9449dda7028b920c19`.
Create a uniquely named Linux source volume and detached checkout of the exact target
using the common Git directory mounted read-only. Check clean LF source, explicit
import paths and all H3 inventory hashes before/after. Build native using the unchanged
`scripts/build_native.sh`; record interpreter, NumPy, Open3D and native paths/hashes.
Run source tests with explicit checkout PYTHONPATH and one numerical-library thread.
No cross-environment imports; no timing-performance claim.

1. Run existing focused unit suites for track/gauge/health/detector/tracking/history,
   free-top/structure-cut integration, node/FastCloud/shared decision policy and
   rescorer. Select by explicit file list after inspecting test names; do not run
   regression/held-out acceptance tooling. Require installed Open3D and enabled native.
2. New independent axis boundary checks: both signs, asymmetric offsets and sides,
   parallel curved axes, threshold equality and just-beyond, near reference bounds,
   slope/MAD/near-bin eligibility, consecutive evidence, gaps at/beyond three bins,
   structural steps, diverging walls, missing/failed wall fits, priors/smoothing and
   final-coordinate consistency. Use deterministic bins and transition-curve scenes.
3. Health property matrix: varied trusted/visible/gauge/drift/candidate/obstacle ranges,
   including disabled/sentinel, zero and negative caps; check clear <= monitored,
   cap never increases either range, and all other non-timing fields unchanged.
4. Matched sealed-control and target detector runs on the same deterministic straight,
   constant-curve and transition-curve scenes, both turn directions and asymmetric
   visible walls, with/without a near object: exact non-timing geometry, corridor and
   detections unchanged by the axis cap; no STOP downgrade; capped values obey min.
   Isolate the axis comparison by disabling only the other newly added mechanisms
   on the target for this differential, and separately compare target axis on/off.
5. Independently exercise spare/vote/column-held logic and clear-cap source
   compatibility with actual Track objects. Inspect cached frame coordinates' lifecycle
   and instrument cache reuse, rather than claiming shared-host timing gains.
6. Brief independent v1/node matrix for malformed health/flags, stale and fresh results,
   latched STOP, and strict true obstacle precedence; AST-check published behavior.

Every invocation, exit/result, source/import identity and any deviation will be retained
under this folder. Newly discovered follow-up measurements will be registered here
before execution. Failures are preserved and classified, not erased or tuned away.

## Acceptance

PASS only if no supported remaining medium-or-higher correctness defect within this
scope. A failed independent oracle is investigated against the documented algorithm
before assigning severity. Existing gate PASS and parent self-review are evidence,
not substitutes for H4. Intentional pre-H5 unsealed version 1.0.0 and archived failed
S1/v2 reports are not shipping defects. Review findings include file/line, reproduction,
impact, and result/source identities. Commit only this owned folder after status,
diff and recent-log inspection; no amend, push or integration action.
