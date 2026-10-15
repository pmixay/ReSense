# H2: structure-cut physical evidence bar (pre-registration)

**Baseline:** `d0d17bb` (`origin/final/silent-misses` on 15.10), detector code
equivalent to `a188a2d` / review fixes `14f83dd`. **Candidate branch:**
`h2/cut-bar`. **Status:** acceptance specification, no detector change yet.

## Defect and scope

A cut fragment can have eight voxels but only one azimuth column: repeated
echoes and vertically stacked returns must not be treated as a resolved body.
The 14.10 review's wall-anchored mast 1.2 m proud creates two new matching
STOP frames. C with dropout or 5 Hz can also create isolated cut fragments.
The minimum voxel count alone is not a physical evidence bar.

## Acceptance cases to commit before implementing a candidate

* An eight-voxel vertical fragment in a single azimuth column remains dropped
  by the cut; adding duplicate echoes must not change that verdict.
* A resolved face spanning at least two azimuth columns and enough vertical
  support remains eligible for all existing corridor/column rules. The new
  bar never exempts it from those rules.
* Input order and a reflection across the track do not change eligibility.
* Ordinary non-cut clusters and the existing part voxel threshold retain
  their current behavior; the new check applies only to structure-cut parts.

Measure raw cut-part azimuth spans, distinct ring support where available,
voxel counts and matching STOP frames before choosing a threshold. Do not
select a threshold solely because it clears a particular bad frame.

## Recorded-data acceptance

1. Run the wall-anchored battery in
   `../silent_misses_2026-10-14/harness/safety_review/` on the seal, baseline
   and candidate with the same inputs. No object-attributable STOP may be
   added to the seal (including the mast 1.2 m proud).
2. Preserve C's person-size probe: first matching STOP 82.8 m and 55 matching
   STOP frames, against the same baseline axis and ICP as the 14.10 result.
3. Replay plain C, C 30% point dropout and C 5 Hz; require no spurious gauge
   cut part at or above the physical bar under dropout/5 Hz.
4. Affected tests pass; full gate on committed code exits 0 against
   `../results/regression_baseline_2026-09-29_shell_off.json`, no `--allow`.
   Run an explicit frame diff and explain every difference.
5. H4 remains an independent P4 review. This experiment does not reseal.

## Environment

Continuation uses isolated worktrees, `PYTHONPATH` and `RESENSE_REPO` pinned
to the code under test, native kernels built from that tree, one BLAS thread
per process. Gate and node-decoded caches are prepared from organizer bags;
they are different formats and are never substituted for each other.
