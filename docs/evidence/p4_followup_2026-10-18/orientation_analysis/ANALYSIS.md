# L16: why a wall passes the mount check

P4's result is a real unresolved limitation. Eight 90-degree side-mount cases report a plausible mount while producing 395–509 STOP rows on a known-empty 545-frame recording. The fresh experiment in [PROTOCOL.md](PROTOCOL.md) tests only an explicit configuration workaround for two known rotations. No automatic-orientation or STOP-suppression change is proposed for the current candidate.

The reports and P4 harness are preserved byte-for-byte in `p4_inputs/`; [registration.json](registration.json) binds their original remote paths and commit. P4 checked `b423562`; the current version-only experiment uses `e9d8fc6`. The [source continuity check](../source_continuity.json) establishes the exact relevant source relationship. This analysis does not treat the remote summary as a new execution of its unavailable raw captures.

## The forward-axis hypothesis

`observe_mount()` already counts forward/rear cone returns **before** it fits the floor or rails (`resense/calibration.py:227`). The count uses `X > 15` versus `X < -15`, with `hypot(Y,Z) < 0.35 abs(X)`. For a roll around forward X, X is unchanged and `(Y,Z)` undergoes a two-dimensional rotation. Its Euclidean length is unchanged. Thus both cone counts and their ratio are invariant. Moving this check earlier, or tightening its ratio, cannot distinguish an upright input from the corresponding rolled input on this evidence.

This argument applies to P4 cases 4 and 5, the opposite rolls chosen for the experiment. It does not claim every arbitrary axis permutation has the same score. Falcon's narrow forward field of view can help identify its **forward** axis, but forward alone leaves the roll/up ambiguity. Its forward-only observation also cannot be applied as a universal rule to the Pandar 360-degree sensor.

The remaining mount check asks for a fitted surface below the sensor and two parallel ridges of the configured rail spacing. A tunnel side wall with cable trays can satisfy those same geometric predicates. `_search_orientation()` ranks passing candidates by rail score without an independent up cue or ambiguity margin. More importantly, `MountCalibrator.update()` does not search alternatives when the configured mapping passes: `ob.ok` immediately sets `_config_passed` and `orientation_confirmed`, and stops orientation search. Small residual roll/pitch against the wrong wall can then finish with `status=ok`. The drift monitor observes that same accepted frame, so it is not an independent gravity check.

## Why suppressing STOP while pending does not fix it

`status=pending` is the tilt-estimation state; it does not mean that `orientation_confirmed` is false. The correct upright empty control itself remains pending for 190 frames. The confirmation flag means an observed/adopted mapping passed the existing geometric test, not that physical up was independently measured.

Even without the underlying P4 raw rows, its counts prove a pending-only block is insufficient. Empty case 5 has 509 STOP rows and only 192 pending rows, leaving **at least 317 STOP rows** outside pending. Case 4 has 395 STOP and 202 pending, leaving at least 193. Case 16 has 509 STOP but six pending rows, leaving at least 503; even blocking its 191 provisional rows as well leaves at least 312. These are lower bounds from the summaries, not reconstructed exact frame intersections. The fresh case-5 run records the exact intersections and confirmation flags.

The completed fresh run makes the case stronger: case 5 is confirmed from frame 0, all 509 empty STOP rows occur while confirmed, and 327 occur with `status=ok`. P4's case-5 JSON also contains **two GO rows** despite the general "no silent GO" wording in its earlier narrative. The fresh run reproduces them at frames 311 and 316, both with the wrong configured orientation still `ok` and confirmed. They are on known-empty data, so they do not prove a missed real obstacle; they do rule out the blanket claim that an unsupported side mount never reports GO. The real-obstacle wrong case additionally loses six upright STOP rows (189–194) and adds three (5–7), even though its aggregate STOP count remains high.

Suppressing an obstacle STOP because calibration is uncertain would also discard real obstacle evidence. The existing readiness guard intentionally zeros the trusted monitored/clear range and prevents an otherwise GO from looking ready, while retaining STOP and existing FAULT evidence. Extending it into blanket STOP suppression would require a separate safety case and violates the registered no-lost-STOP rule if deployed without that review. No suppression is applied here.

## Narrow workaround and P3 handoff

For a **known** mounting transform, correct the explicit sensor axes before auto-calibration. The registered algebra derives the signs; the experiment verifies every corrected point byte and every operational output against a fresh upright run. Keep the ordinary tilt calibration enabled and replay disabled. The driver-frame profiles `falcon_ros` and `falcon_native` describe known coordinate conventions; their names alone do not prove an arbitrary physical mounting orientation. Manual axes are needed for the tested side mounts.

For unknown side mounts, a credible next candidate should separate `orientation_confirmed` into the evidence actually available: configured coordinate convention, geometry passing, and any independent up/mount assumption. An explicit supported-up requirement or an ambiguity/degraded diagnostic is a bounded contract change, but **it does not automatically remove false STOPs**. Automatically choosing among wall/bed hypotheses needs an independently justified cue, such as a declared mount transform, calibrated mounting geometry, or gravity data. None is established by the current two-recording battery. Do not pick a universal height cutoff from the observed 2.29 m false fit or enable all 24 candidates merely to make these cases pass.

P3's proposed regression set should include:

- The real square-tunnel wall/tray counterexample, the two signed-mapping identities, and the forward-cone invariance proof; retain the failing default result.
- A fixture where a wrong wall passes `observe_mount`, demonstrating that pending, geometric confirmation, and physical-up confidence are distinct. The current synthetic side-mount test expects fallback and does not cover this real counterexample.
- Correct upright/inverted controls, no silent GO while unconfirmed, zero trusted range for an explicitly unsupported/ambiguous state, and retained STOP/FAULT evidence. An ambiguity warning alone must not be called a false-STOP fix.
- Exact STOP boundaries and detection/range payloads for both full recordings; all existing real-Falcon STOPs; profile/reset isolation; unchanged replay default0. If production behavior changes, repeat the full gate and X3 with the new source identity.

The configuration experiment is bounded at 2,984 rows and requires no new runtime parameters. A status/assumption diagnostic is a small implementation hypothesis but needs the counterexample and regression checks above before acceptance. A general automatic 90-degree mount fix has no defensible completion estimate until an independent cue is available; the current evidence cannot justify one. N2's original acceptance distinguishes the eight upright/inverted mounts from the documented arbitrary-sideways limit, so this workaround does not silently expand the accepted automatic-orientation scope.
