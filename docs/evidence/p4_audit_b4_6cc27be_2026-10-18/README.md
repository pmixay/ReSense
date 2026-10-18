# P4 audit of the B4 candidate `6cc27be` (det/b4-orientation), 18.10

Candidate: **`6cc27bef7b8aa36b758017a45430496485d3c9fc`**, base sealed 1.1.0 `3b7d7aa` (package 1.1.0; changes
`resense/calibration.py`, `detector.py`, `health.py`). Reference: sealed 1.1.0 tree (`492e407`, detector identical to
`3b7d7aa`). Runtime of the P4 protocol (`OPENBLAS_CORETYPE=Haswell`, one thread, Python 3.10, NumPy 1.26.4); native
library built from the unchanged `native/`. P4 changed no detector code. This audit answers P3's request to close
B1/B2 of the earlier AI review (`docs/evidence/b4_release_2026-10-18/p4/README.md` on the candidate branch).

## Conclusion

| item | status | why |
|---|---|---|
| **B1** (lost voting observation delays a real STOP) | **CLOSED** for the reported case | reproducer passes on `6cc27be`, fails on the earlier source (positive control) |
| **B2** (committed-candidate acceptance evidence) | **NOT CLOSED: the gate part is open.** The X3 part is closed by this audit | the branch's gate and B4 receipts measure the **earlier** `calibration.py`, not the committed one; no committed-candidate gate pair exists; P4 could not run the gate here |
| B4 behaviour on the committed source | **PASS** | independent 24-mount battery, both recordings |
| X3 | **PASS** | 40 / 40 cases, all 29,765 rows equal to 1.1.0 |
| new findings | **no blocker**; 4 should-fix (S1–S4) | code review, verified in source |

**Formal acceptance cannot be given yet.** It needs a complete gate on the exact committed `6cc27be` plus a same-runtime
sealed-reference gate (both with the ride and Set F), with raw outputs, as the release protocol itself requires.
If that gate passes with 208/208 non-latency rows equal and no lost matched STOP, P4 has no further blocking item.

## B2: identity of the existing evidence

| file | committed `6cc27be` | measured by the branch's gate / B4 / tests (`provenance.json`) |
|---|---|---|
| `resense/calibration.py` | `10b127d5…` | `b340acda…` (**different**) |
| `resense/detector.py` | `4fa84cf7…` | `4fa84cf7…` |
| `resense/health.py` | `6b392b75…` | `6b392b75…` |

The B1 fix changed `calibration.py` after those runs. The branch README says so itself ("the receipts here describe the
earlier exact source hashes"). `docs/evidence/b4_release_2026-10-18/` contains the protocol, the earlier review, the
author response and the runner `run_acceptance.py`, but **no results**. X3 was never run by the author (the driver
refuses an uncommitted tree). The seal check on `6cc27be` fails, as expected before P1's reseal.

## What P4 ran on the committed candidate

**B1 reproducer** (the earlier reviewer's `directed_checks.py --only-short-window --assert-no-loss`; real
`doubleT_obstacle`, `frames=5, obs_spacing=1, provisional_min_deg=10`), on three trees:

| tree | rotation 4 first STOP | lost matched `person_crossing` frames | exit |
|---|---|---|---|
| **candidate `6cc27be`** | **frame 8** (= identity control) | **none** | 0 |
| earlier author source (`b340acda…`, from `candidate_source.tar.xz`) — positive control | frame 9 | **[8]** | 1 |
| sealed 1.1.0 | rotation 4 never recovered (wrong mapping) | all, as expected | 1 |

([b1_repro_*.json](.)). A first attempt crashed on an import path for the two reference trees; it was rerun with the
judge scripts on `PYTHONPATH` and only the rerun is used.

**B4, P4's own 24-orientation battery** (`scripts/orientation_battery.py`, the same harness as the original B4 finding):

* Empty `roundT_squareT_pressureGate_squareT` (545 frames): all 24 mounts adopt the correct orientation by frame 1,
  **0 STOP in every case** (1.1.0: 395–509 in eight rolled cases), 0 GO before confirmation. Frame 0 is FAULT
  (new orientation-conflict health error) in the 23 non-identity cases. After adoption every case differs from the
  plain run on the same 10 frames (CAUTION↔GO), exactly as the correctly recovered upright case 1 does on 1.1.0: an
  existing calibration-timing shift, not new.
* Obstacle `doubleT_obstacle` (201 frames): all 24 correct by frame 1; **no STOP frame lost** against the comparator
  (same rotation on 1.1.0 for upright mounts, the correctly oriented plain run for sideways ones); 16 sideways mounts
  193 STOP from frame 8; the 7 other upright mounts keep their existing 2-frame start delay (191). The plain
  (unrotated) runs equal 1.1.0 frame by frame on both recordings.

**X3** (`robustness_battery.py -j 2 --reference` the 1.1.0 Linux battery): **PASS**, 40 / 40 cases, zero metric deltas;
all **29,765** processed rows equal 1.1.0 in every field except timing / latency messages
([battery_6cc27be.json](battery_6cc27be.json)). The same row comparison flags all 40 entries between two runtimes known
to differ (positive control, 1.2.0 review).

**Gate: not run.** The gate needs its 1 cm `.npy` frame cache and the ride; this container has only node-decoded
float32 caches and 13 GB free. Both attempts stopped before measuring ([gate_*.log](.)). Converting caches would not be
the gate's input, so it was not done.

Raw rows: [raw_6cc27be.tar.xz](raw_6cc27be.tar.xz) ([SHA256SUMS](SHA256SUMS)).

## Code review (fresh-context agent, findings checked in source)

No blocking finding. 169 focused tests pass. On 900 real startup frames of the six bags, decision, obstacle, health
level, calibration status, detection centres and clear distance equal 1.1.0. STOP precedence holds: obstacle → STOP is
checked before health → FAULT (`decision_policy.py:124–140`); the conflict flag cannot hide a STOP.

**Should fix:**
* **S1** `calibration.py:399–401`: `orientation_conflict` is set whenever any scan axis was measured and an alternative
  wins a vote, **including a vertical axis that agrees with the configuration**. A correctly mounted upright Pandar
  whose configured mapping fails the forward check on a frame (tunnel end, platform) shows **FAULT** with clear range 0
  where 1.1.0 showed GO/CAUTION. Not seen on the six bags.
* **S2** the flag is cleared only at adoption (`:430`) or when the configured mount passes (`:440`). If calibration
  gives up (`fallback`), it stays set and **every frame without an obstacle is FAULT**; 1.1.0 gives CAUTION. Fail-closed
  (availability, not safety), but a default-path change. Fix: set the flag only for a non-vertical axis, or clear it at
  fallback.
* **S3** the message "alternative orientation awaiting confirmation" is never reset; a correct mount ending `identity`
  keeps it (cosmetic, misleading in logs).
* **S4** `scan_axis` returns None on 38 of 300 real Pandar frames (7–22 % per bag), because after the 16k subsample
  some of the 8 channels have < 24 points (75 % channel rule). On such a first frame the protection is absent and a
  wall can still confirm a wrong sideways mapping (the original failure). Not a regression; the README should say the
  protection is probabilistic. A per-channel sample floor would likely fix it (unverified).

**Notes:** the B1 fix applies to sideways recoveries with a measured horizontal axis only; upright-family recoveries
and ring-free recoveries still discard their votes, as in 1.1.0 (not a regression, but "all voting observations are
fed" is not true in general). The replay counts elapsed frames, the normal path counts frames with a rail pair; the
difference is at most one observation. N2 fix (≥ 3 cone offsets ≥ 0.005 apart) is correct.

## Not covered

The gate (above); the real ROS node and Docker; recordings at 5 Hz (`periods > 1`) beyond the author's unit test;
raw Hesai driver output (decoded cones are exact; a real driver's optical offsets could make `scan_axis` always None —
fail-safe); Falcon (no ring: the feature is inert there); G3 (not touched, by rule).
