# P3 R3 cables and H1 tall-object diagnosis — 19 October 2026

**R3: author acceptance PASS on committed source `b14cfd0`.**
**H1: cause reproduced and new approach proposed; inherited High remains OPEN.**
Independent P4 review and P1 integration/reseal are pending.

Branch `det/r3-h1`, base `6be817abf725f9d6836d53866ff38a8cea1253dc`.
The detached control `76742f3` adds only the registered protocol/tests to that
base; its detector is byte-identical to base main, including published L16/S3.
All38 frozen-source members in the final archive equal the measured Git blobs.
Source fingerprint: `59687366d24d8a81366468c4eaad18918044465f312fa0b0e5670801f28661bc`.
[Machine-readable acceptance](author-acceptance.json).

## 1. R3 cause and implementation

The unchanged judge E6 reproduces59.78 m first STOP /43.37 m held90%,29/59 visible
matched STOPs. The dominant cost is confirmation, not doubt:22 missed visible
rows first fail hits and6 time. At86.25/84.81 m there are3/4 hits, confidence1,
hit fraction1, but only0.300/0.400 s against the generic0.5 s. Long no-return
gaps repeatedly expire a5 cm target's track.

The real Set O hanging search already forms valid groups at49.83/48.19 m;
the two-hit burst expires before generic confirmation. Direct raw-stage examples
show both inside-top support and above-top continuation, not a guessed empty ray.
[Raw examples](r3-raw-examples.png), [registered diagnosis](DIAGNOSIS.md).

The patch changes `resense/tracking.py`, `resense/config.py` and the two matching
YAML files. A **consecutive, current-frame-only** run of clean narrow vertical
evidence may confirm sooner:

* Tall body: X/Y footprint<=0.15 m, height>=1.5 m,>=8 strict voxels, ordinary
  three-hit bar and0.3 s.
* Existing hanging kind: same narrow footprint, span>=0.25 m,>=2 voxels including
  a strict voxel, two hits and0.2 s. Its existing inside/above-top, rail and range
  requirements are retained.
* At most1 ms timestamp slack, also bounded by1% of nominal period and requested
  duration. A miss, ineligible geometry or continuation clears the special run.
  Historical accumulation cannot supply it (`n_raw == len(points_idx)`).
* Generic confidence, vote, column/approach/doubt guards remain effective. The
  ordinary confirmation route is still available. Setting
  `tracking.cable_confirm_time_s=0` disables both shortcuts.

## 2. Checked results

| Check | Same-runtime main control | Final R3 source |
|---|---:|---:|
| Standing5 cm E6, node replica: first /held90% |59.78 /43.37 m|**86.25 /61.28 m**|
| E6 matched visible STOP rows |29/59|**34/59**, five added, none lost|
| Set O hanging, node replica: first /matched rows |30.12 m /15|**48.19 m /19**, four added, none lost|
| Set O hanging, **compact int16 gate**, first /matched rows |30.1 m /15|**35.1 m /18**|
| A-axis control |218.38 m /82 of177|identical|
| C-person control |82.77 m /55 of153|identical|
| Actual Falcon,4443 node-replica rows |1372 STOP|exact same decisions, detections and warnings|

The compact-cache path does **not** meet45 m; do not substitute its numbers for
the float32 node path or claim the two pipelines agree. Quantization sensitivity
remains a limitation. These are offline node-faithful replicas, not new ROS/DDS
or released-image measurements.

* **287 affected tests pass**, zero skips/deselections/failures in the final
 16-file suite; [JUnit](affected-final.xml). New acceptance tests were committed
 before production edits. Initial red witnesses and rejected variants are retained.
* **Final full gate on `b14cfd0`: exit0**, no overrides/waivers/missing gated
 rows, original shell-off baseline. Every serialized row was independently
 revalidated:15269 ordinary +3060 Set F. No previous STOP/detection payload or
 matched Set F hit was lost; the five empty bags and11271-frame ride have zero
 added STOP. Ordinary changes are exactly three matched hanging STOP frames
 786..788. [Final gate](gate-final-candidate.json),
 [full frame review](final-gate-frame-review.json), [raw audit](final-raw-audit.json).
* **X3:40 cases /29765 rows /260 comparisons PASS**, fresh committed final
 source against the exact same-input current-main control. Recounted every row
 and each inside-object matched set: zero lost old STOP or positive matched rows.
 Empty-bag STOP sets are identical. [Final X3](x3-final-candidate.json).
* **An added unmatched alarm is retained, not waived away:** Set O frame779 adds
 one unmatched STOP frame/episode in7 of10 variants (nominal, pitch+2/-2, roll+2,
 dropout seeds1/2, dedup). Each is within the existing X3 allowance of+1 episode.
 All seven new detections explicitly have kind `hanging`, and frame779 has no
 label. On the nominal full trace the firing report assignment has `q=false`,
 `reported_before=true`, `misses=1`, `hold_misses=1`: the original missed-frame
 hold carries the newly confirmed cable. Its46.56 m prediction agrees within5 cm
 with interpolation between visible labels778/781. This explains the nominal
 instance; the original unmatched scorer result remains unchanged. Branch/sample
 audit is1/7 added rows, descriptors and missing labels are checked on7/7.
 [Every added row and nominal full state](unmatched-alarm-audit.json).
* Nine fixed E6 conditions (nominal, three tilts, four30% dropout seeds, dedup)
 retain every baseline matched row, each giving86.25/61.28 m; no new off-object
 STOP decision. A separate340-frame full-payload E6 pair finds every added
 detection matched to the target and none lost. Under perturbations the archived
 range JSON omits full simultaneous detections, so that stronger all-payload
 claim is restricted to nominal. [Supplement audit](final-supplement-audit.json).

Set F's informational cable sustained median decreases34.2->17.8 m because its
population grows: previously sustained sequences remain19.0/49.5 m, while two
newly sustained sequences enter at16.6/16.4 m. There are nine added matched hits,
zero lost. This is not a per-sequence regression; the worse aggregate metric is
preserved explicitly in the gate and raw audit.

## 3. H1 cause and new approach

The archived independent physical slab caster reproduces H4 case45: box at67 m,
lateral+0.68 m, width0.46 m, physical top3.22 m. It returns84 points;80 strict
voxels on20 rings enter the candidate, observed height0.162..2.940 m, four more
returns continue above the search cut to3.062 m. The **height/width column
heuristic demotes an occupied collision volume**, then column history prevents
STOP. [Raw physical points](h1-raw-case45.png).

Proposed **positive collision core with independently bounded axis uncertainty**:
do not ask whether the top looks free. Require an observed vertically resolved,
short-depth footprint to remain wholly inside the collision tube under an
independent rail/axis error bound. Keep edge/merged/unsupported cases advisory.
Missing/dark upper returns supply no safety evidence; a tall object continuing
above the envelope is still a collision. Ordinary positive hits avoid the old
provisional-column re-arm mechanism.

The read-only prototype evaluates64 physical cases, mirrored and at37/67/109/137 m,
including tall/short/opaque and absorbing continuations:17 pass its positive-core
predicate with a **supplied3 cm axis bound**; none of32 outside-envelope controls
pass. Case45 passes the geometric predicate, but its observed lateral clearance
permits only about4 cm of axis error. The other15 positive cases remain unresolved
by this prototype. No independently calibrated runtime bound is implemented here;
therefore this is a **proposal, not an H1 runtime fix or closure**.
[Prototype and all64 rows](h1-prototype.json), [driver](h1_proposal.py).
`column_free_max_top=0` remains in the class and both YAML files.

## 4. Verification, failures and data identity

* Fixed-latency plain/traced controls on both sources agree on every field except
 wall-clock telemetry (340 E6 +791 Set O rows per source). All85 visible non-STOP
 attribution rows are independently checked against full saved states and actual
 tracker branch inputs. The final added-alarm trace separately records the
 report assignment and also equals its plain reference.
* Original trace timing changed diagnostic latency health. The failed raw
 equality result is retained; it was corrected by feeding identical42 ms previous
 latency before health evaluation in both observer modes, not by dropping decision
 fields. The uncontrolled runs also match after the existing latency-only
 normalization. [Trace adapter](run_observed.py).
* Current input arrays were checked against original CDR by direct NumPy field
 views:16 distributed frames, XYZ/intensity/ring exact,3133 receive timestamps
 exact; coordinate mutation is a positive control. [Input check](raw-input-check.json).
 The initial checker incorrectly used square-root range thresholds, assumed a
 ring field in Set O and made an inefficient SQLite blob-sort query; these tool
 failures were corrected before accepting its results.
* Historical1.1.0's40 raw X3 reports were individually hash-verified and their
 summaries recomputed; all260 numerical comparisons pass. Current NPZ-container
 hashes differ. Canonical Windows serialization proves arrays identical for
 **3132/3133 frames**, with the existing Set O332 mismatch retained. The strict
 historical same-container-input comparison is **not PASS**; formal same-input
 X3 above is against the fresh current-main reference.
 [Canonical input check](canonical-inputs.json).
* Variant1 (`154dd9d`) failed hanging45 m acceptance (35.08 m); variant2
 (`1f93141`) passed measurements but lacked the explicit accumulated-point
 exclusion. Both sources/runs and red controls remain available.
 [Timing amendment](AMENDMENT_2.md), [current-frame amendment](AMENDMENT_3.md).

## 5. Commands, sources and handoff

All evidence uses NumPy1.26.4 and the same native binary
`67fa0887e5480e24ca67138ec5271969742917a5c5869d9ab4e634599d8c7394`.
The original commands, start/finish times, imported checkout and source hashes are
in `*-execution.json`. Environment for candidate commands:

```bash
export RESENSE_REPO=/home/aiops/resense PYTHONPATH=/home/aiops/resense
export OPENBLAS_CORETYPE=Haswell OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
export LD_LIBRARY_PATH=/tmp/opencode/resense-b4-libs/usr/lib/x86_64-linux-gnu
PY=/tmp/opencode/resense-b4-venv/bin/python
$PY docs/evidence/r3_h1_2026-10-19/evaluate.py gate --revision final --candidate-only
$PY docs/evidence/r3_h1_2026-10-19/evaluate.py x3 --revision final --candidate-only
$PY docs/evidence/r3_h1_2026-10-19/audit_results.py --revision final
$PY docs/evidence/r3_h1_2026-10-19/audit_followup.py
```

Measurement commands reserve fresh output names; existing results are immutable.
For reproduction use a new scratch root in the evidence drivers and retain the
original cache paths/placement. The only missing C decoded cache was built from
the existing local raw bag; no data were downloaded. Old untracked B4 results
remain in place. G3 was not used.

* [Exact40-member source/test/native archive](final-source.tar.gz),
  [member hashes](final-source-manifest.json).
* [Raw evidence, including failed variants and paired final runs](raw-evidence.tar.gz),
  [member hashes](raw-evidence-manifest.json); additional carry trace has its own
  archive/manifest. Every archive member was reopened and checked.
* [Proposed measured regression baseline](proposed-regression-baseline.json) is
  byte-identical to the final gate; P1 owns adopting it for the accepted bundle.
* The predecessor seal still fails for the inherited L16/S3 files and these four
  new frozen-file changes, plus derived config/validation checks. Its exact
  output is [retained](predecessor-freeze-verification.txt). No new seal is claimed.
* P4: independently review the narrower confirmation rule, all matched/lost sets,
  frame779 carry and the historical-input limitation. P1: integrate the accepted
  R3 scope, select the baseline and reseal. H1 needs a separately registered
  axis-support design and independent physical/ride acceptance before enabling it.
