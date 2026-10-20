# Pinned H1 current-source delta check

Target: isolated `/tmp/opencode/h1-reviewed-publication`, commit
`520e7dcd2843a0e7c9055fca6c186c0d1687945f`. Comparison: immutable successful
captures measured at `f56ad5e62d9d051811c804734c7731b6951eae90`.

Only new evidence here and scratch under `/tmp/opencode/h1-final-review/current520`.
The user authorized copying the existing identical native binary after source/hash
checks. No build, detector/config edit, Git write, whole gate/X3/Falcon or G3.

Before execution: confirm source delta is only lowobj.py; current default F1a seal;
copy verified native binary; positive freeze controls only in scratch copies;
hash unchanged original injection tools, cache/baseline/ICP, original captures.

Run plain directed NPZ replay: all 31 sequences / 518 scans, deterministic previous
latency 42 ms (first None), default config, every non-timing FrameResult field and
full tracker state against original captures. Independently recompute target hit,
truth body membership, false core/STOP and no-rail accounting from actual outputs.
Keep every field difference; do not fail early merely because outputs differ.

Run fresh A340 using unchanged range_test injection driver from the pinned tree,
fixed existing baseline/ICP and original caller placement convention. No tracer.
All injected-input fingerprints must equal the original ones. Compare every raw
non-timing output field and every stored target-window tracker field with old
plain captures; independently reconstruct all 177 matching decisions and miss set.
Store full current captures in scratch, compact rows and all differences durably.

Run unchanged tests/test_column_collision_core.py (104 expected tests), justified
by rebinding H1 to a detector source with an intervening low-object code change.
Pytest cache/temporary outputs stay inside the allowed new scopes.

Controls: real positive hit; removed detection; float32 ULP, signed zero and dtype;
miss-set added/removed controls; clean and deliberately tampered freeze copy.
Output completion is separate from H1 acceptance. No new true-axis or elimination
claim is inferred from output equality. Preserve initial f56 review unchanged.
