# H1 continuation on 1.3.0 (f24d939): partial, BLOCKED

**Status: incomplete.** The detector, configs and ROS package in this commit are unchanged from
f24d939, and the 1.3.0 seal verifies. No fix is shipped, no gate has been run and there is no reseal.

## Done and checked
* Synthetic directed matrix (31 sequences / 518 scans; geometry of h1_rail_limits_2026-10-20,
  caster `h1_cast.py` copied byte for byte, SHA-256 ebe88a40…deae44), run with `matrix.py`
  on f24d939: `baseline-directed518-f24d939.json`.
  * Plain = traced on 518/518 scans: every non-timing FrameResult field plus the full tracker state, hashed.
  * Against the f56 archive: target STOP and target core frames equal on all 31 sequences;
    detections, warnings and candidates byte-equal on all 518 scans. Differences are structural or
    monitoring-only: new track and tracker fields (518 / 423 scans) and health/clear_distance on 288 scans.
  * Reproduced: 56 false-core / 40 false target-STOP rows in the 4 outside-target wrong-pair sequences;
    the 4 inside-target sequences miss 14/14 scans each.
* Cause of the wrong pair: `estimate_rails` keeps the most prominent pair, and the distractor rails are
  taller (0.30 vs 0.20 m). In all 11 distractor scenes the host and the distractor form separate runs of
  qualifying centres. Checked with a standalone prototype (a separate script, not the production function).

## Not verified / not done
* `rails_nearest_pair.UNVERIFIED.patch`: a proposed fix, **not applied**. With two or more separate
  qualifying runs it keeps the run nearest the prior axis; with one run the output is identical to before.
  The 104 existing H1 tests passed with it applied. Its full-pipeline effect on the matrix and on real data
  was **not measured**.
* STOP surviving rail loss: provisionally correct conservative behaviour. The target stays inside the true
  host envelope (lateral 0.68 m, |Y| ≤ 1.05 m), so the 4 retained STOPs are true STOPs. This is geometric
  reasoning only; the outside-target control was not run.
* Not done: A340 baseline, the 43 column-hold and 7 zone-vote misses, every real-data gate, the reseal,
  and the cleanup-lane merge.

## Blockers
The permission check refused (1) the dataset download and (2) evaluation runs on a detector tree with
changes (reason "Modify Shared Resources", probably the CLAUDE.md rule that detector changes are P3's).
Both need explicit user authorization before this work can continue.

Run: `RESENSE_REPO=<checkout> OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 python matrix.py OUT.json
[--compare-archive <unpacked h1_rail_limits raw-evidence.tar.xz>]`
