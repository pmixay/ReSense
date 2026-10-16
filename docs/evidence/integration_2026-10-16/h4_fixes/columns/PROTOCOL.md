# H4 column author-fix protocol (pre-implementation)

Author work, not independent review or merge approval. Registered against
`838dd321b56a22596b7830aeb17b424136f5156a`; independent H4 remains immutable.
Scope: clustering.py, column configuration and mirrors, test_column_free_top.py,
new portable test_h4_column_evidence.py, and this evidence directory. Tracking is
owned separately. No version, freeze manifest, G3 cases or acceptance rules change.

## Failure witnesses committed before patch/replay/tuning

* New pure-NumPy physical caster reconstructs independent case 45: 1.83 m sensor,
  4.12 m ceiling, centered (67,+0.68), square width 0.46, top 3.22. Input bytes must
  match the published SHA, with 84 object returns, 80 core voxels / 20 rings and
  observed cut top below 2.95. Require actual free-top gauge evidence and matched
  STOP before/after the two missing frames.
* Nearest-hit absorbing columns (2.54 m to ceiling) must stay columns, including
  highest-first/reversed/absent IDs at 67/109/137 m. Neighboring returns or missing
  ring IDs alone do not prove free sight through the object's footprint.
* Opaque column, resumed face and occluding beam controls remain advisory. Short
  2.72 m physical poles at 37/67/109/137 m retain gauge evidence.
* Tests are self-contained under tests/, copied by the normal Docker test build;
  no docs fixtures or external data imports. Run unchanged on the registered parent
  first and retain failures. The parent defect is already independently published.

## Implementation hypothesis and rejection policy

Follow physically observed same-face continuation even when the last candidate
ring is below the numerical maximum-top threshold. Require positive sight through
the object's footprint where missing continuation could be absorbing; retain a
narrow geometry-supported far-field path only with a physical justification.
Do not globally loosen signatures, bars, ranges or target acceptance. Merely
turning tall_gap to 0.3 has already failed and is not an accepted fix. Preserve
failed author attempts and measurements in new directories, never overwrite them.

## Required measurements

1. Parent failure run, then affected column/structure/native/synthetic unit tests
   in Linux image `sha256:5e2659e8f8d3a7e9f64d7c269ae920badd86b8a388e48e9449dda7028b920c19`.
   Never build native on the shared Windows source. Clone committed Git objects
   from common .git mounted read-only; build only Linux .so in a scratch volume.
2. Reuse independent H4 components.py geometry and replay.py inherited observer
   definition pinned to 838dd32 via an author-owned adapter. Reviewer sources,
   sealed/candidate reference volumes and data stay read-only. Verify imported
   source path, actual HEAD, source/config/native identities and single-thread
   numerical settings. Label every result author measurement.
3. Physical tall/dark/opaque/beam controls, ring order and dropout. Report matched
   STOP frame sets and any losses, including the short-pole re-arm owned by tracking.
4. Actual ride pieces 1 and 3, fresh detector each: plain and EXACT inherited dark
   observer (0.6 deg above candidate top, inherited range/azimuth mask). Compare
   exact frame sets and serialized centers to sealed plain; zero excess STOPs and
   no lost sealed STOP required. Counts alone are insufficient; no spatial tolerance.
5. All 27 development P3 probes if practical; specifically A-axis short pole must
   retain 157/177 STOPs, C person first detection 82.77/55, plus normal S/B dropout
   stress (seed 461023, 27%). Preserve full outputs externally and compact evidence
   with commands/source hashes here. Parent agent owns the final full gate after
   the committed fix. Successful local tests do not waive a blocker or tradeoff.

Local commits only, stage owned paths explicitly after status/diff/log inspection.
If positive controls and zero dark excess cannot coexist, report BLOCKED with
the exact remaining limits, rather than call the author fix a review PASS.

## Pre-patch witness execution / adapter clarification

`parent-witness` failed source-path validation: the image eagerly imports installed
resense in sitecustomize before the clone exists. Retained untouched; the adapter
now restarts Python with the clone present. `parent-witness-02` measured unchanged
column source (HEAD advanced concurrently to e623aad, tracking-test registration):
11 failures / 6 passes, including the exact case-45 hash and all absorbing controls.
At 109/137 m the observed absorbing stump is shorter than column_min_height, so its
gauge classification bypasses the column signature entirely (spared=false). The
test is clarified to require no false free-top evidence and no spare, with the
column-zone assertion only where that signature applies. No global signature is
changed to make these in-envelope physical collision objects advisory. The raw
initial assertion failure is retained. Beam and tall assertions are unchanged.
