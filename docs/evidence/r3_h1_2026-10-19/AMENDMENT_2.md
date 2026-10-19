# R3-v1 rejected; timestamp-boundary correction registered before revision2

Source `154dd9d`: E6 improves to84.81/61.28 m (32 matched frames, three added,
none lost), but Set O hanging first STOP is35.08 m, below the45 m acceptance.
All282 affected tests pass; ideal0.1 s unit stamps did not expose the failure.
Retain v1 and its raw runs under `/tmp/opencode/r3-h1/v1/`.

Actual sensor timestamps fluctuate around0.1 s by microseconds. The first
hanging pair's measured span is slightly below0.2 s, so a strict exact0.2 s
comparison still asks for a third hit that does not arrive. Revision2 admits
at most1 ms of timestamp slack **only in the consecutive geometry-qualified
fast run**, bounded by1% of the nominal period and1% of its requested duration.
This does not change generic confirmation, counts, geometric support, survival,
confidence or the gate's acceptance. Add positive jitter and short-duration
negative controls before the algorithm change. Original physical targets and
gate/X3 requirements remain fixed.
