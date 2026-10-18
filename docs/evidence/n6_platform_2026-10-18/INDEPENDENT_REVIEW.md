# Independent review of N6 revision 3

Reviewed candidate `745096f`, including `track._extend_axis_from_rails`, the
separate supplied-ring path in `Detector._fit_track`, the low-bed range boundary,
and the new optional pairing limits in `farrails.py`. Recommendation at this
checkpoint: **retain the default-off candidate**. The measured platform gain is
useful, but the 60 m first-STOP target is unmet and the full gate has not accepted
this candidate.

The implementation preserves the existing axis shape and requires fresh paired
rail evidence. It bounds longitudinal head separation to 5 m, places a station
at the nearer head, requires a connected chain and multiple distinct stations,
and checks every consensus-selected station against the existing axis. The
previous axis range is restored before the next fit, including failed-floor
paths. Missing rings cannot enable this extension. The V3 low-bed change keeps
low/straddle/central-near admissions at the pre-extension boundary. The earlier
review findings concerning original-zero restoration and distant same-ring
pairing have been fixed and covered by tests. No new source-code blocker was
found in this review.

Completed frame-level controls preserve all detection and warning payloads in
the five empty recordings (2,287 frames), the real obstacle recording (201),
Set O (1,510), synthetic switch (736) and synthetic tunnels (545). Their known
object matches are unchanged, with no new unmatched or explicitly outside-object
STOP rows. Latency health changes under concurrent load are not timing acceptance
evidence. The captures omit persistent track IDs and cannot independently prove
event-count parity; the full gate remains required.

On synthetic platform the person first STOP improves **44.01 to 51.12 m**
(frame 239 to 228), retaining all 147 baseline matched rows and adding 11. Nine
additional marginal-box STOP rows have unknown physical gauge membership. Their
possible false-STOP upper bound rises **38 to 47**; zero known outside-object
additions does not make this uncertainty disappear. The scorer's 62.24 m
sustained-range statistic permits initial misses and is not first STOP at 62 m.
At frame 229 fresh axis support returns to 45 m while the existing tracker keeps
the previous STOP: this is retained detection history, not retained rail range.

## Independent source-removal diagnostic

The full-precision diagnostic replays the same immutable candidate and confirms
all non-timing outputs against its prior capture before comparing point subsets.
Removing every non-source XYZ return and removing independently frozen label
boxes give the same effect on all 84 supported frames. All **655 selected rail
stations have both head returns in the exact original source geometry**, as
confirmed by the production-pairing provenance reproduction. Synthetic points
are therefore not directly furnishing the accepted head pairs.

At frames 145 and 146, removing inserted-object returns leaves all seven original
selected stations exactly unchanged, but exposes farther stations around 43 m
and 51.5 m. The farthest station disagrees with the current axis by approximately
−0.152 and −0.144 m. The existing 0.10 m all-station check then rejects the entire
extension. This is **occlusion of conflicting farther evidence**, not disappearance
of the near supporting rail observations. Frames 140 and 143 gain farther support
after removal; the person first-STOP frame 228 remains unchanged.

Set O metadata has no ring channel. Its zero-valued cache placeholders must not
be treated as real scan-line IDs; the unmodified full-source comparison is not a
positive rail-support control. The useful subtraction retains actual synthetic
ring IDs only for returns that exactly match the original source, without
inferring ring IDs for missing data. A separately recomputed source near fit
helps distinguish near-model dependence from far-return dependence.

A narrower rail-height window was explored and rejected as a remedy. Removing
points is not automatically conservative: discarding a conflicting station can
enable more range. The diagnostic of a ±0.15 m height window confirms this:
it removes the contradictory farther source station and allows both variants to
pass, rather than resolving the original sensitivity. It also loses 32 of the
84 previously supported frames. No runtime revision or acceptance claim follows
from this exploratory filter. Recomputing the near fit on source geometry adds
frame 167 to the lost-extension cases; the first-person frame remains supported.
Preserve the all-selected-stations check; do not simply trim a chain at the first
disagreement to regain the desired extension. A future height model needs a
physical error budget supported across complete independent controls.

Evidence: [full-precision source removal](exact_source_rail_support.json),
[station provenance](rail_station_provenance.json),
[platform comparison](synthetic_platform_v3_comparison.json),
[range invariants](v3_range_invariants.json), and the four positive-control
comparison files linked in the main evidence folder. Any revised candidate needs
its own registered hypothesis, tests, immutable replay and acceptance decision.
