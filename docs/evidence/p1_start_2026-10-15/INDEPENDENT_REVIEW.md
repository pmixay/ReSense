# Independent review of new P1 node/tool changes

The authorized reviewer authored none of the reviewed implementation. This is a review
of the new P1 patch relative to `d0d17bb`, **not H4 certification of inherited detector
changes or of the future combined 1.1.0 detector**.

Initial review: `06850e1`. Follow-up snapshots: `0caf5c2`, then **`5e002e5`**.
Read-only code/test/evidence inspection and small isolated import/parser/stubbed-node
reproductions; no heavy tests or Docker workload during the performance matrix.

| Confirmed finding | Resolution verified |
|---|---|
| Standalone backend did not ship/declare its policy dependency | Declared existing ROS Python distribution; real backend/core/ROS wheels installed outside checkout, pure imports without ROS |
| Judge analyzer ran before required metadata existed | Immutable `.meta` written before analysis, separate final cleanup receipt |
| Parser required counters absent from watchdog schema | Nullable watchdog shape accepted; strict frame/tail/drain checks retained |
| Malformed raw health could release STOP / be overwritten by freshness | Raw strict validation before projection and latch release; invalid monitoring, zero range, FAULT or held STOP |
| Active-input skip credits lost across ignored inputs | Bounded active-epoch scalar survives until accounted or epoch reset |
| Historical detector / old ROS overlay shadowed observer policy | Observer source resolved independently; selected detector imports and existing node identity preserved |
| Tools image lacked new test fixtures | Precise context exceptions and COPY inventory, checked in actual image |
| Reproducing E2 collided with retained mutation-image tag | Fresh UUID default, explicit image/output options |
| Decode failure discarded credit before accounting | Account consumes credit explicitly; unused credit banked only in valid accepted epoch |

Final independent reproduction of the last issue: parent **4 dropped / 2 skipped**,
fixed **3 / 2**. Consecutive decode failures: **5 / 3**, with credits consumed afterward.
Decode/detection/publishing failures, genuine later transport loss, topic/frame/loop/large
jump transitions and invalid header/anchor boundaries were exercised. Across 24 mixed
epoch transitions: **48 dropped / 24 skipped**, no residual state, maximum metadata/pending
count 3 within cap 12. No persistent cloud collection was introduced by the fix.

**Final reviewed verdict:** all previously confirmed findings resolved; no remaining
medium-or-higher finding identified in this follow-up's scope. The separate full Linux
suite subsequently covered the fixed source. S1's measured numeric failures and C1 v2's
failed targets remain open; this review does not turn them into accepted results.
