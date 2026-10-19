# Independent review 1 (A11) — verbatim

> Reviewer: a fresh Claude Code remote session (`session_01NmhJmLYynxiDsAbKogwFWr`, started 19.10 12:45 UTC by the
> F1 lane), read-only, given only the branch at `3af832f`, CLAUDE.md, DETECTOR_FREEZE, BACKLOG F1, the protocol's
> criteria and the raw evidence archives; no results README existed yet. Finished 12:52 UTC. The response is
> amendment 6 of [`../PROTOCOL.md`](../PROTOCOL.md). Text below is the reviewer's final message, unedited.

---

**Verdict: PASS WITH CONDITIONS.** H (mount cross-check) and S2 (settle) can ship as configured. F1a (`local_rail_margin` 0.01) should not ship until B1 is fixed and the ride and gate are re-run.

## Blocking

**B1. F1a's rail reference is raised by other low objects in the same rail band** (`resense/lowobj.py:255`, `:286`). `_band_line` leaves out only the cluster's own extent ±0.3 m. Returns from other low clusters on the same rail, with h < 0.3, still count toward the median. A long low object lying along a rail head (a pipe, timber or loose rail) that the clustering splits into pieces at 30–50 m therefore lifts the reference for each of its own pieces.
- **Reproduced** with the real `local_rail_reference` on synthetic points. An 8 cm object alone on the rail gives a reference of 0.003 and is kept (the positive control). Six 0.6 m pieces of an 8 cm object, 1 m apart, each get a reference of 0.080, and all six are made weak.
- **Effect:** weak clusters are removed from `candidates` and warnings (`detector.py:371`). The object therefore gets neither a STOP nor a CAUTION until the pieces merge into one cluster at closer range. How close that happens is unverified.
- **Fix:** leave out the points of every low cluster in the frame (weak or not) from `_band_line`. Also keep weak clusters as advisory instead of dropping them.

## Non-blocking

1. **The rail-reference rule in the code differs from the registered design without an amendment.** Protocol §5 registers ≥ 2 returns per bin and ≥ 4 bins. The code uses 1 return per bin and ≥ 2 bins (`lowobj.py:286`, `local_rail_min_bins` 2). With 2 bins the median is just their mean. The 0.034 m headroom measurement used the same code, so it is consistent with what ships, but the deviation needs recording.
2. **S2 ignores height (`tracking.py:515`), and the stated reason is wrong.** The amendment says only a horizontal move can take an object into the gauge. But the envelope has a height band and changes width with height. A person stepping or falling down from a platform edge, or something lowered from above, can enter the gauge with < 0.5 m horizontal movement. At standstill such a track stays "settled outside" until ≥ 50 of its last 100 hits are inside: about 5 s at 10 Hz, 10 s at 5 Hz, or until the train moves 0.5 m. A correction of the axis while the train stands is delayed the same way.
   - Near escalation still overrides it, but only for non-low clusters with ≥ 10 strict-envelope voxels within 35 m.
   - The registered standing-train probes (`S_person_*`, `S_cube05_*`) put every object at lateral 0, so they never test this.
   - Suggested fix: release the settled state after a run of `zone_window` consecutive inside hits. The Falcon support reached 6/10 inside votes, not 10/10.
3. **H assumes the calibrated mount height is right to within about 0.5 m** (`detector.py:841`). If the height were off by more than 0.5 m and the track model were right, a low near object would read below the mount plane and be demoted to `height_conflict`, which is never near-escalated. It applies only when calibration status is `ok`/`identity`, and no test covers a wrong mount height. Real grades and vertical curves stay well inside 0.5 m + 0.05·X up to 30 m.
4. **The cause of the lost ride STOPs is matched by position, not traced** (`scripts/attribute.py`). Nine of the 21 removed ride STOP frames have non-low detections (4153, 4158–59, 7361, 7365–66, 10506–07). The likely mechanism is that the track's earlier low hits are now weak, so it never earns the STOP. The ride is empty, so no real STOP is lost, but this goes against CLAUDE.md rule 3.
5. **Weak clusters also stop limiting clear distance.** `squareT_platform` frame 83: clear distance 45.2 → 120 m, with the decision unchanged.
6. **Some evidence is missing:**
   - No `gates/*.log` files exist.
   - No artifact for the candidate for A4 (`small_on_rail` through the node path, 48 ± 3 m), A9 (X3 battery) or A6 (full suite, 1,969 passed).
   - The three rail-box probes give identical results at every margin (first STOP 44.86 m, 29 frames), and `held_from` 49.32 m is farther than first STOP. Plausible, but it shows the probe does not tell the settings apart.

## Code review: what checks out

- **Switches off:** every new path is behind its own `> 0` guard. `height_conflict` in `_NOT_ESCALATED` can only matter when H is on. `settled_out` stays False when `settle_min_hits` is 0.
- **What the gates ran:** the candidate gate ran 129415f; `git diff 129415f..HEAD` touches no detector, config or test file. The switch-off gate ran 1144150, whose code is identical to 129415f. The two YAML copies are byte-identical.
- **Weak low evidence:** it can only continue a reported low STOP for 0.3 s and never seed a track (unchanged tracker code).
- **Settle votes:** hits kept by stop-keep count as inside. Near escalation takes precedence over settling.

## What I checked from the raw archives (my own scripts, not the summaries)

- **Ride (11,271 frames):**
  - Base: 130 STOP frames, 30 episodes; low-kind at onset 2668, 2671, 6860, 10484, and on any frame also 4153, 7361.
  - Candidate: 109 / 24; low-kind only 6860 (both counts).
  - 0 STOP frames added; 21 removed (16 became CAUTION, 5 GO). This matches amendment 4.
  - Kept frames: 4 lose extra low detections, the reporting detections are unchanged.
- **Falcon (4,443 frames):**
  - Base 1,372 STOP frames, candidate 1,360; exactly the 12 excluded frames were removed (all now CAUTION); none added.
  - All 1,360 other STOP frames kept with identical distance and lateral; 9 of them drop only the 115 m support as a second detection.
  - First STOP at frame 2972, 124.84 m, in both.
  - `off_129415f` vs base: 0 rows differ outside timing.
- **Gate per-frame, base vs candidate:**
  - `doubleT_obstacle`: 0 differing rows (193 STOP).
  - Set O (`cloud_with_fake_obj`): 447 STOP frames and the detection lists are identical on every frame; the only differences are 43 latency health messages.
  - The roundT recordings are identical; `squareT_platform` has identical STOP frames.
  - Removed STOPs are only on empty recordings: `doubleT_platform` 36–37 and 24 ride-chunk frames.
- **Gate JSONs:** `passed: true`, `allow: []`, no worse or missing rows. Switch-off identity: 0 of 15,269 rows differ and set F is equal.
- **Tests:** in a Python 3.12 venv with the native build, the six requested files gave 152 passed, 1 deselected (it needs `/data/cache/new_data`). The first run skipped 58 because libEGL was missing; I installed it and re-ran.

## Not verified

- No recordings were available, so nothing was re-run on data.
- The full test suite, X3 battery and `small_on_rail` through the node path were not run.
- I did not look at the pictures.
- At what range a fragmented object on a rail head merges into one cluster (this sets how bad B1 is).
