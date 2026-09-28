# Failed onset candidate: bounded observer diagnosis

The proposed default remains **rejected** by the full native gate. This observer work explains known failures; it is not a new holdout or an acceptance run. No production source was changed.

## Source and parity

- Candidate observed at clean `ff1b8bd63ef4c51532d44e422b854847e72220fb`; detector digest `15f67a0b1739716ab2e5aa182198f95f6e68a8ad9c5d08f147b3c7106c7f2a82`, config `8c25720bfbe082bcef41a6f69ea5916068221dec79adc628e5b4543533f065b1`.
- Baseline observed at clean `5fa978f59d4e787bce04da3ab9b4257f5474d772`; detector digest `c0273a13a67ab4872dab00154caa75f6b30f50416775062c591fbb47906a0fa4`, config `22a30ff265035e06358a21696cfb8bc61b598d16e5a64aa3536abfefbc4bd5fb`.
- Both load their local enabled native library with SHA256 `b5a5c2dc08be8fa1ab00e27dee7662d31413a99f819a760d2d2d4b16b93e8534`.
- Four Set F sequences, 400 frames per variant: **all complete returned sequence dictionaries exactly equal the original archived gate outputs**. No fields excluded. Candidate 94.48 s, baseline 85.04 s; diagnostic timing only.
- Two ride prefixes, 589 frames: **all rows equal the archived candidate outputs** after the existing strict, validated latency-only normalization. Every decision, detection, warning, monitoring and non-latency field is retained. 42.76 s; diagnostic timing only.
- All three runs verified source/config/native/clean HEAD before and after. Protocols were registered before execution; observer wrappers delegate to unchanged original functions and do not modify their inputs or returns.

## Set F losses: factual branches

| Lost frame | Fresh predicate cause |
| --- | --- |
| trolley `46_0037`, `46_0038` | Current ordinary cluster is warning, reason `beyond_height_ref` |
| box1.0 `140_0038` | Same current off-gauge rejection |
| person `168_0028` | Same current off-gauge rejection |
| trolley `46_0039`, box1.0 `140_0043`, trolley `172_0038`, `173_0003` | Current ordinary gauge cluster, but history is `off_gauge, off_gauge, ordinary`: only one eligible hit |
| trolley `172_0039` | One missed frame after the suppressed onset; baseline earned STOP at `172_0038` and holds it, candidate never earned it |

Every directly rejected target track has `clean_gauge=True`, `far_evidence=False`, no near escalation, column hold, approach block or opinion withholding. These are ordinary corridor tracks; none of the five affected track IDs has a low-kind note anywhere in its full traced lifetime.

The removed false Set F detection at `173_0001` uses the same track17 later affected at `173_0003`. It is rejected for current `beyond_height_ref` advisory evidence despite `clean_gauge=True`. Therefore a blanket clean-vote advisory bypass would also restore this known false detection.

Reducing the recent-hit minimum alone does not address the four off-gauge losses. Requiring approach for every exception also misses the box onset (four observations before the existing five-observation requirement) and the later trolley clean hit (fit RMS 2.0104 m).

## Ride benefits: saved captures and exact observer

Saved captures show five removed events and 13 removed STOP frames, with no new STOP frame. The public reason is empty on all 13 removed frames; those captures alone cannot establish current provenance or a fresh predicate branch. `ride_saved_analysis.json` preserves all payloads and nearby reports.

The two authorized representative events were replayed from the original chunk start:

- Chunk4 track210: three low-kind gauge notes at261/263/264, then a normal corridor cluster at266 with only two gauge voxels and current zone warning. The `current_off_gauge` branch rejects the onset.267 is missed.
- Chunk5 track146: low-kind gauge notes310–312, normal corridor gauge313, off-gauge314 and316 (one gauge voxel at316). `current_off_gauge` rejects316;317 is missed. A low-kind gauge match at319 then fails the two-hit recent minimum after two off-gauge notes;320 is missed.

Neither event is blocked by `keep_thin`, `keep_low` or `far_thin` provenance. The actual issue is combining low-object and corridor evidence, followed by insufficient current gauge support or the first low match after advisory hits.

## Bounded next mechanism for parent review

A narrower research candidate could apply fresh onset checks to tracks whose **existing bounded gauge-vote history contains low-kind gauge evidence**, while retaining inherited confirmation for ordinary corridor-only tracks. This targets the demonstrated mixed low/corridor association mechanism and does not tune a distance threshold or extend a lifetime sticky state. Existing confirmation, near, column, approach, earned-STOP hold and final opinion precedence must remain intact.

This has not been implemented or evaluated. It may retain fewer false-alarm improvements, restore the known Set F false detection, or fail other recall/history checks. It requires a new protocol and full acceptance work before any promotion.

## Artifacts

`protocol.json` and `ride_protocol.json` are the preregistered scopes. `trace.py.txt` and `trace_ride.py.txt` are external observer runners, not production code. Each run directory includes pre/post identities, exact input manifests, outputs, compressed full traces and parity summaries. `lost_hit_trace_summary.json`, `ride_target_trace_summary.json` and `diagnosis.json` provide focused derived records. `execution_notes.json` records the pause before baseline during root's quiet runtime.

Archived observer scripts keep their original bytes under `.py.txt`; run logs use `.txt`.
The [import map](../import_manifest.json) records the original commit and filenames. Protocol
and source identities retain the paths used during the original experiment.
