# Rejected actual-interval-only candidate

This candidate used every positive sensor timestamp delta directly for blob speed and chain
duration. The full strict regression gate passed with all 146 gated detector metrics unchanged,
but paired monitoring acceptance failed on the labelled set O recording:

- in-envelope GO overclaims increased from 16 to 36;
- all detector decisions and negative alarm outputs stayed identical;
- monitoring costs on the five empty recordings and ride passed.

The set O recording's timestamp intervals ranged from 53 ms to 140 ms around its nominal 100 ms
scan period. Treating this normal jitter as changing object speed broke sparse-evidence chains and
removed clearance caps. The candidate was rejected and is not the implementation under review.

`gate.json` and `monitoring_acceptance.json` preserve that failed run. Its per-frame captures remain
in the local `/cycle/work/timestamped-persistent-evidence` work directory and are not committed.
