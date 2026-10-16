# H4 object-safety status: BLOCKED

Independent reviewer; no authorship of reviewed production code. Target
`7cc640fb39698b1fe45bc6ab069eab68ad4ac6ae`, measured H3 core
`f8c088dc4f3243fbd15a3aae9be0459e8a0aa941`, all 36 sealed-scope files identical.

This status was recorded before any author fix. No production fix is part of this review.

## High — inherited tall in-envelope pole miss

`resense/clustering.py:1007–1019, 575–588, 663–665` and
`resense/tracking.py:118–140`: a pole continuing above the corridor cut remains
`reason=column`; the shipped tall-following option is off, and column history
keeps the track advisory even with abundant physical strict-gauge evidence.

Independent physical-ray case 45: sensor height 1.83 m, ceiling 4.12 m,
0.46 m square pole, physical top 3.22 m, center (67 m, +0.68 m), known straight
axis y=0, highest-first Pandar IDs, no point dropout. The pole is entirely within
the physical envelope laterally (y=0.45..0.91 m). There are 84 pole returns,
80 strict-gauge voxels / 20 rings, observed candidate top 2.939613 m.
Neither source produces a matched STOP in any of 20 updates (object absent only
on frames 9 and 10); column warnings persist when confirmed. The 2.72 m top
control is detected by the candidate. The seal has the same tall miss; inheritance
does not make the physical collision object safe under the registered protocol.

Reproduce: `python docs/evidence/integration_2026-10-16/h4_safety/launch.py components candidate --run NEW_ID`.
Inspect case 45 / highest / dropout 0 in external `physical.jsonl`, using actual
`track.reported && track.zone == gauge` (see ADDENDUM_03 adapter audit).
Compact corrected witness: `results/tall_miss_witness.json`; the larger scene
witness collection is retained externally under `run-001/exports/physical_witnesses.json`.

## Medium — dark-continuation false-STOP sensitivity persists

`resense/clustering.py:574–592` accepts absent continuation plus neighboring /
empty-ring evidence; `resense/tracking.py:656–667` only delays repeated spare
acceptance. The initial registered observation-only mask produces ride STOP
counts **14 -> 23** and **2 -> 12**, with 9 and 10 excess frames, respectively.
This is an artificial observer sensitivity experiment, not an unedited real-scene
or physical-ray false-positive claim. It changes no fitted model, candidate
points or input frames. The excess is on known obstacle-free development ride
pieces and is not waived. The separate exact inherited-mask replay is in progress
at this status checkpoint; its final counts belong in README/results.

Reproduce initial mask: `python docs/evidence/integration_2026-10-16/h4_safety/launch.py replay candidate --mode dark --run NEW_ID`.
Exact published-mask reproduction: same command with `--mode dark-inherited`.
Controls use `replay sealed --mode all` and `replay candidate --mode all`.

H4 is a safety review, not release approval. The conditional merge/branch-retirement
workflow cannot treat this review as a passed check.

## Completed inherited-mask confirmation

The separately registered exact inherited mask finished: **14 -> 23** and
**2 -> 7** STOP frames, exactly **9 + 5** excess, zero removed STOP frames.
All 14 extra STOP detections geometrically match plain sealed warnings with
exactly identical serialized centers (distance 0.0 m), independently of track IDs.
Complete histories are in `results/dark_inherited_track_matches.json` and full
paired frames externally in `run-001/exports/dark_inherited_witnesses.json`. This confirms the
medium blocker; it is not waived because the ordinary gate is unchanged.

## Medium — a confirmed free pole remains advisory on its first returning hit

The registered hold/release experiment also confirms an object-safety gap in the
new free-top path. `resense/tracking.py:664–667` makes the first spared hit a
column; its explanation persists in history. After two missing object frames,
`resense/tracking.py:436–448` applies the old explanation to a previously earned
STOP and withholds its first clean returning hit.

Physical case 44 has the same 67 m / +0.68 m / 0.46 m geometry as case 45, with
top 2.72 m. STOP frames are **5–9 and 12–19**. Frame 9 is the configured one-miss
hold, frame 10 releases, but frame **11** has all 72 strict-gauge voxels / 18 rings
back, `reason=''`, `spared=true`, confidence 0.85, 9/10 gauge votes and no column
hold. Nevertheless `fresh_blocked=true` makes its reported zone `warning` because
the initial artificial column explanation is still in `explained_hist`. It is
STOP again at frame 12, after that history entry ages out. The extra 0.1 s of
advisory after strong evidence returns is distinct from the configured missing-hit
release, and is a remaining safety defect in the newly detected-object path.

Across the physical variants, 712 objects were STOP before dropout, all held the
first missing frame and released the second; **268** failed to regain STOP on the
first returning frame, all regained it on the second. The seal never detects
these newly recovered cases as STOP, so this is not represented as a lost sealed
STOP frame. The finding is the independently observed re-arm gap itself.

Reproduction is the same `components candidate` command; select case 44 / highest /
dropout 0. Exact full state: `results/rearm_witness.json`; complete variant list:
`results/rearm_delays.json`; counts: `results/hold_release.json`.
