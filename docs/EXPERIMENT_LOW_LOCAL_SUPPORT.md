# Local along/lateral bed support — experimental low-object candidate

**Status: measured and rejected as an improvement; default-off, opt-in only; no acceptance claim.**
This is a bounded follow-up to the cross-ring false-target trace. It is intended for an
offline A/B measurement; it must not be promoted from this document alone.

## Exact hypothesis

Some of the near false ride tracks are not compact foreign objects. They are returns from
the bed or a rail/bed edge whose fitted height is locally biased. The point views repeatedly
show a few low-object returns only **3–12 cm above the fitted bed**. In particular,
`new_data_1.jsonl:292` at 29.9–32.7 m has 6–7 low-object voxels at the bed/rail-head edge;
the observed channels are 60, then 59/60 and 60/61. Its recorded same-band support has
`height_excess_over_same_band` from about −0.05 to −0.01 m on the low rows. This is
consistent with a shallow continuation of a local surface, but the trace does not survey
the physical surface identity.

The experiment tests the narrower geometry hypothesis:

> If a low candidate is on a locally continuous, slightly raised bed/rail surface, current
> returns on both along-track sides and both lateral sides will describe the same surface;
> a compact object will interrupt that surface or rise above it.

The check is therefore a local **surface-continuation rejection**, not a ring threshold,
height threshold applied globally, or a learned classifier.

## Mechanism and flags

The existing `low_candidates` stage already receives the complete current-frame bed band.
When `lowobj.local_support_enabled` is true, each baseline low/near candidate is checked as
follows:

1. Search current-frame bed-band returns within ±`local_support_along` (8.0 m by the
   experiment profile) in the candidate's narrow lateral band. Returns within
   `local_support_guard` (0.3 m) along-track are excluded so the candidate footprint does
   not provide its own support. The lateral band is ±`local_support_lateral` (0.15 m),
   excluding the candidate's immediate 2.5 cm cell.
2. Require returns on both lateral sides on each along-track side. Quantise duplicate returns
   to occupied local cells and calculate one 90th-percentile
   height per one-metre along-track bin, requiring at least two returns per bin. There must
   be at least two qualifying bins on each along-track side. A single scan line, one-sided
   edge, gap, or step does not qualify.
3. The two-sided line must be internally consistent (90th-percentile variation ≤
   `local_support_tolerance`, 2.5 cm), and its height must be 0–15 cm above the existing
   local bed reference. Only a candidate within 2.5 cm of that line is rejected as surface
   continuation.

If any support condition is unavailable or inconsistent, the baseline candidate remains.
This fallback is intentional: ambiguity must retain recall. The work is also capped at 512
candidate returns; busier frames retain baseline evidence.

The profile is [`configs/experimental_low_local_support.yaml`](../configs/experimental_low_local_support.yaml):

```yaml
lowobj:
  local_support_enabled: true
  local_support_along: 8.0
  local_support_guard: 0.3
  local_support_lateral: 0.15
  local_support_tolerance: 0.025
  local_support_max_correction: 0.15
```

The dataclass defaults in `LowObjectConfig` keep `local_support_enabled: false`. No
`detector.py` integration edit is needed: the existing low-object stage calls
`low_candidates`, and the check is inside that owned stage.

## What the trace supports, and what it does not

The source-parity trace contains 11,271 frames, 130 STOP/alarm frames, and 31 STOP episodes
from 32 track identities. There are 17 events nearer than 60 m; 10 involve the low-object
path. Five low-involved events have at least two observed raw channels, so a ring filter is
not a general solution. The trace also contains counterexamples to broad rejection:

* `new_data_5.jsonl:330` is a 40–48 m ordinary edge cluster with 56–69 voxels and three
  strict-gauge rings; it is not a low-object continuation candidate.
* `new_data_6.jsonl:331` has a roughly 1.9 m tall cluster supported by nine strict-gauge
  rings; it must remain on the ordinary path.
* `new_data_7.jsonl:264` has one strict support ring but two or three raw rings; off-gauge
  points cannot be promoted into strict support, and the normal cluster path bypasses
  `far_thin`.

The implementation does not alter ordinary clusters, ring logic, tracking, confirmation,
or the existing straddle thresholds. A low object that is clearly raised above the local
surface remains a candidate. The existing tests also exercise the opt-in 30 × 30 × 10 cm
bed-box policy and objects on the rails; the shipped default is unchanged. The organizer's
policy still says a 30 × 30 × 10 cm object wholly below the clearance floor is not an
obstacle; enabling the separate `near_enabled` policy remains an experimental choice.

## Available-data replay: rejected

Ran the entire audited cache with eight independent ride chunks, four NumPy workers and
single-threaded OpenMP/OpenBLAS/MKL. Opt-in command (PowerShell):

```powershell
& 'C:\Users\alikh\AppData\Local\Temp\opencode\resense-cross-ring-venv\Scripts\python.exe' -m scripts.eval_real --cache 'D:\Datasets\ReSense' --out 'D:\Datasets\ReSense\cross_ring_2026-09-28_measurement\local_support_v1' --bags 'new_data,cloud_with_fake_obj' --jobs 4 --chunks 8 --set 'lowobj.local_support_enabled=true'
```

Ride STOP frames / track events / episodes stayed **130 / 32 / 31**; set O STOP frames /
events stayed **447 / 9**. There were zero STOP-decision differences on either recording.
The candidate removed 109 corridor candidate entries across 27 ride frames and six entries
across two set O frames; none of the 19 fresh low-supported ride STOP track-frames had such
a removal. The costly per-point neighborhood analysis increased ride total p95 from
**116.8 ms** (same-checkout defaults) to **606.7 ms**. The trace's local same-band statistic
does not require the four-quadrant bed-filtered evidence this rule needs.

Validated frame comparisons and hashes of the audited cache inputs are in the local
`D:\Datasets\ReSense\cross_ring_2026-09-28_measurement\quality_local_support_v1.json`.
The isolated implementation can remain opt-in for reproduction, but **must not be enabled**
as a quality improvement. Loosening thresholds to force an effect on this same empty ride
would not establish real-object safety.

## Original expected effect and uncertainty

The expected positive effect is limited to low-object false tracks whose current-frame
support actually forms all four quadrants. Among the 10 near low-involved events, the trace
suggests the best candidates are the shallow edge groups around
`new_data_1.jsonl:286`, `:292`, `new_data_1.jsonl:306`, `new_data_2.jsonl:570`, and
`new_data_4.jsonl:56`/`:58`; this is a hypothesis, not a predicted event count. Events with
missed-track continuation, no fresh low support, or ordinary clusters cannot be removed by
this gate. The likely result is therefore a subset of frames/events, not all 10 low-involved
events or all 17 near events.

False suppression can still occur if a real low object is laid along a continuous raised
surface, especially near a rail edge. Sparse support leaves some false events untouched:
the full available-data replay above confirmed no reduction. The six short bags are absent,
Linux acceptance is unavailable, and set O lacks ring metadata. No default-promotion
recommendation follows from the local synthetic-object tests.

## Further checks before reconsidering the rejected rule

Run the focused tests first:

```text
C:\Users\alikh\AppData\Local\Temp\opencode\resense-cross-ring-venv\Scripts\python.exe -m pytest -q tests/test_low_local_support.py tests/test_lowobj_near.py
```

The available ride and set O A/B above has already been run. If a different mechanism is
proposed, compare defaults versus that new rule on the complete ride and all available
obstacle recordings, and report separately:

* low candidates rejected by the four-quadrant check and the support geometry for each;
* false alarm frames, track identities, STOP events and STOP episodes;
* first/sustained STOP distances for the 30 cm bed box, objects on rails, and other low
  positives;
* changed ordinary/straddle decisions, monitored range and latency.

Trace every changed event back to the local support quadrants. Do not count a lower event
total as an improvement if a real low object or an ambiguous candidate disappeared.
