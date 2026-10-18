# Independent review of the 1.2.0 candidate gate

The completed fresh gate passes independent artifact review on
`e9d8fc649f2dd51dd5cd1e4b04ac8c306cc02569`, with 38-file source digest
`b85a93064e79e932df4f7045af21effdf43f0858963204db5d30fc1de37a5e3a`.
The [checker](review_version_gate.py) and [receipt](version_gate_review.json)
verify the actual immutable source, Git blobs, native binary, producer completion,
input identities, raw captures and archive. This review executes no detector.

All **15,269 ordinary frames** exactly preserve the accepted default0 control's
serialized non-timing fields, including **805 STOP frames in 51 intervals**.
Only the registered timing fields and latency-only health presentation are
normalized; decision health, detections, warnings, ranges, mount state and all
STOP endpoints remain compared. All **3,060 Set F scoring rows**, in the complete
30-sequence inventory, remain exact, including 1,064 recorded hits. All 208 gated
non-latency metrics are unchanged, without overrides, missing rows or waivers.
The Set F artifact contains scoring and placement rows, not every detector
payload, so this does not independently reconstruct its hit assignments.

The 25-member [raw archive](../version_1.2.0_2026-10-18/raw/gate.tar.gz) was
reopened and every member matched both its manifest and the retained source.
Its SHA-256 is
`8f762fdae5c2e62c3397c749ccfcd7bb534b0405ca8fbb547c189a5ffab66941`.
The review also binds the raw hashes recorded by the complete frame comparator
to the exact control and candidate captures read during this review.

This resolves the fresh-gate prerequisite for a reviewable **1.2.0 candidate
integrity manifest**. It is an independent agent evidence review, not final P4
acceptance or publication approval. Earlier X3, Falcon and DDS captures retain
their original source identities and are supported by the separate exact
[version-only continuity proof](source_continuity.json). The selected next J1
source remains sealed main 1.1.0; P4's final 1.2.0 review, P3 acknowledgement,
hosted CI repair and release remain pending.
