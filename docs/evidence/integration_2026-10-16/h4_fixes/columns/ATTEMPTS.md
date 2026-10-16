# Author iteration ledger

All raw runs live at `C:/Users/alikh/AppData/Local/Temp/opencode/resense-h4-columns-author-20261016/`.
Each reserves a new directory and Linux source volume; `source.patch`, source and
native identities, worker output and launch argv remain intact. This is author
evidence, not an independent-review result.

* `parent-witness`: infrastructure failure before measurements, installed-source
  eager import caught by path assertion. Python restart fixes the adapter.
* `parent-witness-02`: unchanged column code at concurrent e623aad, 11 failed /
  6 passed. Case-45 input SHA and 80-voxel/20-ring geometry match independently.
  Long-range absorbing stumps can bypass the column-height signature: test scope
  clarified before production change, retaining the actual failure output.
* `attempt-01-witness`: follow continuation for all column calls, require positive
  footprint sight. 16 passed / 1 failed. The beam at 3.05 m is ABOVE the sight line
  of the first free ring over a 2.72 m pole at 67 m; it does not fully occlude the
  evidence. The portable beam control is corrected to 2.65 m bottom (physical
  immediate over-top sight at the beam is about 2.67 m), requiring actual occlusion.
  Independent H4's original over-top beam matrix is still run unchanged and is
  not reinterpreted as fully occluded. Add the exact inherited observer mask as
  a separate self-contained test; it leaves candidate arrays untouched.
* `attempt-01-probes`: REJECTED, A-axis 95/177 instead of 157/177; C-person retains
  first STOP 82.77 m / 55 matching frames. Failure identified: _follow treats
  elevation jitter within the already observed head ring as a tall continuation.
  The next attempt requires new measured height and follows only the object's
  own lateral face; the numeric-cut threshold is not used to skip case 45.

Further results will be appended, not substituted for these attempts.

* `attempt-02-probes`: REJECTED, still 95/177 on A-axis (C unchanged). The
  height/jitter guard alone does not explain the losses. Observed-grid diagnostics
  show the actual cause: some recorded upper channels emit every **0.2 degrees**;
  the old tall-only helper assumes 0.1 and demands unemitted slots. All actual
  footprint returns on the sampled failed near calls are beyond the object.
  Attempt 03 infers each ring's 0.1/0.2 grid from returns BESIDE the footprint,
  never from absent returns inside the possible absorbing face. Unknown grid
  support fails closed. Far calls with no positive under-vault sight remain an
  explicit unresolved concern until the positive replay is measured.

* `attempt-03-witness`: 18 passed / 1 failed (137 m short-pole control). Wider
  grid observation correctly sees a low ring missing on the footprint, while a
  higher ring positively passes. A missing ring cannot itself prove freedom,
  but must not invalidate independent positive sight on another ring. Short
  evidence now counts complete passing rings; tall-following retains its
  stronger all-rays / two-ring requirement. Absorbing columns have no complete
  passing ring under the vault and remain rejected.
* `attempt-04-probes`: REJECTED, A-axis 141/177, C-person still 82.77 / 55.
  Correct observed grids restore every nominal STOP within 100 m. Remaining
  far loss is where the 1.2 m continuation window / edge-curvature margin caps
  positive-sight geometry. Attempt 05 separates the continuation-search window
  from positive sight below the vault, and removes the crown-to-edge correction
  ONLY where the entire measured footprint is inside the +/-0.5 m vault band
  whose minimum height is already the conservative bound across that footprint
  (3 cm measurement clearance remains). Outside that band and for followed
  tall tops the full configured margin remains. No frame IDs, range exception,
  signature bar or target waiver is introduced.

* `attempt-05-probes`: REJECTED, A-axis 137/177, C-person 82.77 / 55. Expanding
  positive sight also includes later roof returns; checking every later ring
  defeats an already complete positive short-top ring. Attempt 06 accepts a
  complete positive short ring immediately, retaining stricter tall evidence.
* `attempt-06-probes` / `attempt-06-dark`: REJECTED, A-axis 147/177; dark rides
  22 / 2, i.e. 8 / 0 excess, zero removed sealed STOPs. All eight residual
  detection centers match sealed warnings exactly. The original head-ring span
  can be narrower than the body; attempt 07 requires the full observed body
  azimuth footprint (union with the followed top if it extends beyond it).
* `attempt-07-probes` / `attempt-07-dark`: REJECTED, still A-axis 147/177 and
  dark 22 / 2 (8 / 0 excess). Full-footprint one-ring sight is insufficient to
  remove this artificial observer sensitivity. Affected suite: 118 passed,
  3 failed, no skips; unchanged assertions expose the unaccepted default and
  changed dark-to-vault policy. No existing assertions are rewritten.
* `attempt-08-probes` / `attempt-08-dark`: REJECTED despite zero dark excess:
  require two complete positive footprint rings for short tops as well, while
  allowing other unreturned short-top rings to remain ambiguous. Tall tops
  retain the stronger every-ring requirement. Actual dark frame sets become
  exactly sealed 14 / 2, no extra or removed STOP, but A-axis falls to 139/177.
  The same-runtime parent control independently reproduces 157/177 and C-person
  82.77 / 55. Published range-probe placements and matcher are unchanged.
* `attempt-08-components`: independent full 1,576-scene / 144-component matrix,
  with exact input identities verified against the sealed fixtures. Case 45 is
  recovered (STOP 5..9,11..19); case 44 re-arms on 11 with the separately owned
  tracker fix. No sealed matched STOP is lost in this matrix, but **208** prior
  short-pole updates and **1,200** prior surface-component updates are lost.
  Physical absorbing and beam-control losses are also retained explicitly.
* `attempt-08-normal`: B/S dropout 0 / 51; plain rides 14 / 2. All detection and
  warning descriptors are identical to sealed plain, including exact centers.
  Other serialized differences are the inherited H3 wall-drift/clear-range
  fields (`normal_diff_details.json`), not hidden or claimed byte-identical.
* `attempt-08-tests`: 117 passed, 4 failed, no skips. All 19 new H4 witnesses
  pass; native 28, structure 22 and synthetic 40 pass. In addition to unaccepted
  policy/default assertions, the existing free-pole-under-beam positive fails.
  The two-ring candidate is therefore unsuitable even beyond its P3 loss.
* `parent-final-witness`: the final portable test file on unchanged runtime is
  7 passed / 12 failed, no skips: the tall miss, nine absorption cases and both
  inherited-mask cases remain visible. These failures are not xfailed/skipped.

All runtime author changes are restored after retaining exact attempt-08 source
as `rejected_attempt_08.patch`. No accepted column fix or default results from
these iterations. Further author work / joint temporal-evidence design and review
remain the parent's decision; no claim of a general impossibility is made.

* `retained-08-reconstruction`: archived patch reconstructs exactly the measured
  source/config/native identities and passes all 19 portable witnesses in a new
  Linux source volume; it remains rejected on the measured acceptance losses.
* `restored-dark`: new full paired replay on the restored integration runtime
  reproduces 23 / 7 STOP frames, exactly 9 / 5 excess and no removed sealed STOPs;
  all 14 excess detection centers match sealed warnings exactly. The current
  runtime's residual is therefore measured rather than inferred from old reports.
