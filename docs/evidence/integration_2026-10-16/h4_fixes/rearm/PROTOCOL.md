# H4 re-arm implementation protocol (test first)

Author scope: `resense/tracking.py`, `tests/test_h4_spare_rearm.py`, and this directory.
Finding source: `838dd32`, H4 safety `BLOCKED.md`, medium case-44 re-arm finding.
Starting integration HEAD: `838dd32` (the supplied `57cd546` is its ancestor).

Commit this protocol, regression tests, and execution harness before a production
patch or new measurement. Run the committed tests against that unchanged production
source first. Required red: the case-44 assertion on the first returning frame 11
is false, with 72 strict voxels / 18 rings, confidence 0.85, 9/10 gauge votes,
no column hold, and `fresh_blocked=true`.

## Intended narrow semantics

An uncorroborated free-top spare is provisionally treated as a column for the zone
vote and column hold. Its imputed explanation is distinct from a measured
infrastructure explanation. Keep the existing advisory-release clean-run guard:
one noisy spare followed by ordinary objects must still wait for the clean run.
Only accepted, repeated free-top evidence completing that run may discharge the
provisional explanation. Genuine infrastructure explanations retain the existing
bounded matched-hit history, including across misses and after a previous STOP.
No lifetime ever-STOP exemption and no new configuration parameter.

## Checks fixed in advance

- Exact retained pre-tracker case-44 measurements, defaults and opt-in fresh gate:
  STOP frames 5..9 and 11..19; frame 9 holds, frame 10 releases, frame 11 re-arms.
- Actual column / overhead / retro / shell measurements still block frame 11;
  misses reset the run but never erase those measurements.
- Actual column plus one spare still reaches column hold, including through gaps.
- Existing single-noisy-spare advisory release needs five clean hits.
- A new ordinary object associated to actual column history still needs the run.
- Previous STOP does not bypass fresh-onset, ego-veto, or doubt checks.
- Run existing tracking, explained, free-top, history, ego, fresh, stop-keep,
  reseed and native tests, with meaningful Open3D and **zero skips**.
- Capture paired physical case-44 and genuine-column controls from the independent
  H4 caster (source committed with the regression). Parent independent reviewer
  will separately rerun the full physical matrix after both author fixes.

## Reproducibility

`launch.py COMMIT LABEL` creates an isolated Linux clone from a read-only common
Git mount, checks out exactly COMMIT, builds its native `.so` in that clone, and
runs `verify.py`. Only committed files enter the clone. Image:
`sha256:5e2659e8f8d3a7e9f64d7c269ae920badd86b8a388e48e9449dda7028b920c19`.
No shared editable install or worktree binaries. Exact source commit, imported
paths, native hash/status, pytest output/XML, and physical frame histories are
retained under the run label in this directory. The launcher itself runs on the
host but uses no host production imports.
