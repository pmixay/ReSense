# Independent L16 harness review

Reviewed read-only on **18 October 2026 at 12:53 UTC**, before the completed
measurement verdict. No blocking issue was found in the registered experiment's
source or interpretation. This is an independent review by the acceptance-audit
agent, which did not write this experiment; it is not P4's final candidate approval.

| Reviewed input | SHA-256 |
|---|---|
| [PROTOCOL.md](PROTOCOL.md) | `e265b9f7398b1bc4e61e91c941eb2d06e31bcdcbee33a1d00082dba5fac8facb` |
| [run_mapping.py](run_mapping.py) | `20058577b0a5518a4d3d1218eb9a6aea500b06c7cb65f0aa50e2ce4b9682aceb` |
| [execute_mapping.py](execute_mapping.py) | `dc0ba8509c2b0d6108bf4d9fa69d8ec17397588cf6721fbbe46316e4741cd4b7` |
| [registration.json](registration.json) | `aec0db665d105e447335872957ca51bc37772e734ba612ac57224526801b7748` |

P4's archived `rotations()` and the pinned detector's
`orientation_candidates(False)` enumerate the same proper signed permutations
in the same order. The row-vector input transform and inverse configuration
`C = RᵀB` are correct. The harness asserts equality of corrected vehicle XYZ
bytes on every frame before processing; intensity, ring, point order, stamps,
input identities and raw/near counts remain unchanged. Independent fresh replicas
keep calibration enabled, the up-axis restriction enabled and startup replay zero.

The comparison retains all captured operational fields. It removes only the
registered latency values/messages and restores a latency-only warning to its
explicit decision-health level. It applies no tolerance to geometry or decisions,
and missing required fields fail rather than silently compare equal. Full STOP
indices and interval endpoints are retained. Source/native/cache/registration
hashes and the fixed **2,984-row** budget are checked. The wrong-mapping case is
diagnostic and cannot pass the explicit-mapping acceptance criterion.

This design can establish a workaround for the two **known** side rotations in
the offline replica. It cannot establish automatic orientation recovery, actual
DDS behavior, physical remount behavior, or generality across all 24 rotations.
Wrong geometry that has already passed the internal confirmation test must stay
distinct from merely pending calibration. A pending-only STOP block would not
address confirmed wrong geometry; no such suppression is applied here.

No detector was executed during this review. Completed raw counts, comparisons
and STOP intervals require their own result review after the producer finishes.
