# L16/S3 publication and current-main merge — 20 October 2026

The user requested the complete L16/S3 follow-up, current-main integration,
conflict resolution, backlog update and push.

* Test/protocol registration: `679bca8`.
* Detector repair: `4bf62f3`; only `resense/calibration.py` changes.
* Full paired results/drivers/raw bundles: `2dbaeb1`.
* Current remote main incorporated: `99dab01`, including the F1a author repair,
  its measured ride false-alarm cost, and PR #43's default-off K2 v5c.
* Measured combined-source merge: `afbf9fc949f31e920a4d698df8fdfd058afeb308`.
* Publication merge: `c223195`. Its production/native bytes equal the measured
  combined source; source hashes and a separate Git tree diff both verify this.

One textual conflict occurred in `docs/BACKLOG.md` (the adjacent F1/K2 status
rows). The resolution retains F1a's published repair and unresolved cost/review,
K2's merged-but-off state, and L16 A1/T1's completed author acceptance. There
were no production-code conflicts. Unmerged-path inventory is empty.

Fresh checks on the measured combined source: default full gate PASS without
waivers; standard X3 PASS (40 cases /29,765 rows /260 comparisons); full4,443-row
ordinary Falcon; 489 affected tests passed (one external-path deselection, no
skips); analytic A1/tunnel/positive controls retained. Every non-timing ordinary
gate row and every Set F sequence equal F1a's authenticated published raw run.
Thus its inherited ride-cost finding is preserved, not attributed to L16 or
silently reported as a current-main no-regression PASS.

The full L16-only pytest run's three failures remain in the raw evidence and
README. This is not an all-green-suite, independent P4, final seal or release
claim. Final-bundle independent review/reseal and general unsupported physical
mounts remain explicit separate requirements.

[`verify_publication.py`](verify_publication.py) authenticates the published
source/native bytes, ancestry, exact production delta from remote main, raw
archive digests and local evidence links. Its
[`publication-verification.json`](publication-verification.json) records the
checked publication merge; the following documentation-only commit preserves
the same production tree.
