# Exact false-target evidence

The frozen replay reproduced all 11,271 ride frames with zero detection differences and traced
all 45 false-event identities. See [diagnosis](../../../P4_FALSE_TARGET_DIAGNOSIS.md).

- `trace.json.gz`: every live state of each identity, exact cluster geometry, detector model,
  history, current support statistics and passive association observations after mount reseed.
- `inventory.json`: all 45 reviewed geometry labels and per-event quantitative summaries.
- `provenance.json`: SHA-256 hashes of detector sources, tracing/rendering scripts and input
  archives at the diagnostic run, plus result hashes.
- `targets_01.png` through `targets_09.png`: all events in the same stable order as the earlier
  ride scene inventory, five per page. Red points are exact current target indices; other points
  show context at the actual target range. The right column shows physical Y/Z bounding-box
  midpoints through the track lifetime. Those midpoints are display summaries; association
  calculations use the exact centroids/predictions in the trace.

Review labels: 21 low cross-section fragments, six vertically continuing structures clipped by
the corridor, four continuous side-profile fragments, and 14 sparse targets with unresolved cause.
These describe observed geometry, not surveyed semantic object labels or true envelope membership.
The low family includes small returns at the base of side structures as well as rail-bed slivers.
Fifteen identities emit 45 low-stage alarm memberships, with fitted tops 0.030–0.120 m above the
detector rail plane. One alarm frame can contain multiple identities.

The fitted height and lateral coordinates are not independent ground truth. Gray context in the
cross-section is within 3 m along X of the target; visual overlap alone does not prove physical
contact. Same-band statistics use nearby longitudinal returns as a diagnostic reference and were
not used as an evaluated rejection rule. No uncertain event is excluded.

Original `.npz` target/context snapshots are retained under the local validation directory and
can be reconstructed with the documented script and exact frozen input caches. They are omitted
from Git to avoid another copy of the point-cloud data. All snapshots are selected from the
baseline before candidate evaluation; no candidate output informed the review labels.
