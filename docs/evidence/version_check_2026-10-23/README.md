# Version check on two organizer bags, 23.10: v1.0.0 vs v1.2.0 vs the 1.3.0 tree

> **Purpose:** independent re-run of the three versions on real organizer data, to check the version statements in the docs.
> **Owner:** P1 · **Language:** EN · **Status:** checked 2026-10-23 · **Not** a G3 run, not the full gate.

**Data.** `doubleT_obstacle` (201 frames, real person + object on the rail) and `roundT_doubleT` (252 frames, no obstacle),
downloaded from the organizers' archive with `scripts/fetch_cold_bags.sh` (sha256 verified against `scripts/cold_bags.sha256`).
The other four recordings, set O (`cloud_with_fake_obj`) and the ride (`new_data`, 17 GB archive) were **not** downloaded
(disk: 28 GB free), so the full regression gate, X3 and the Falcon recording were **not** re-run.

**Method.** `resense run --bag` (offline detector, defaults, no ego speed) on three clean worktrees: tag `v1.0.0` (`5d6e9b5`),
tag `v1.2.0` (`3b73bbe`) and the 1.3.0 tree of this branch, each with its own `build_native.sh`, `RESENSE_REPO` / `PYTHONPATH` set
to its tree, `OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1`. `resense.__file__` and `__version__` printed per tree
(1.0.0 / 1.2.0 / 1.3.0), so the three runs did use three trees. Scripts: `scripts/run_three_trees.sh`, `scripts/compare.py`;
numbers: `results.json`.

| bag | version | STOP frames | first STOP frame | STOP distance | CAUTION-only frames |
|---|---|---:|---:|---|---:|
| `doubleT_obstacle` | v1.0.0 / v1.2.0 / 1.3.0 | **193 / 201** (all three) | 8 | 55.51–56.56 m | 0 |
| `roundT_doubleT` | v1.0.0 / v1.2.0 / 1.3.0 | **0 / 252** (all three) | — | — | 173 (all three) |

* **Decision differences between versions: 0 frames** in both bags (v1.0.0 → v1.2.0 and v1.2.0 → 1.3.0, STOP and CAUTION flags
  compared per frame). On these two Pandar bags the published README figure (193 of 201, 55.5–56.6 m, no STOP on the empty
  tunnel) holds for **all three versions**.
* **Positive control for the comparator:** it does see changes where they exist: `clear_distance` differs on 11 frames
  (v1.0.0 → v1.2.0) and 45 frames (v1.2.0 → 1.3.0) of `roundT_doubleT`, and on 54 frames of `doubleT_obstacle`
  (v1.2.0 → 1.3.0); the decisions do not change. Consistent with the CHANGELOG (the node's range policy and Falcon clear-distance
  changes only move the reported clear range).
* **What this does not show.** The 1.3.0 gains (curve range K2, Falcon far range) are on curve scenes with injected objects
  and on the Falcon recording; none of those scenes is in these two bags, so this check neither confirms nor refutes them.
  CAUTION on 173 of 252 frames of the empty `roundT_doubleT` is the same in all three versions (a known false-advisory issue,
  not a regression).
* **Unverified:** everything else in the 1.3.0 release table (ride, Falcon, set O, X3, K2 range jobs) is taken from the
  independent review of 22.10 (`docs/evidence/review_1.3.0_2026-10-22/README.md`) and was not re-derived here.
