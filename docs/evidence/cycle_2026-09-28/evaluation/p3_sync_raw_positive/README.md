# Four-config raw positive result

**PASS for this known recording only.** All four registered comparisons had no
newly missed labelled frame and no new unmatched detection. Fresh onset produced
no measured recall or false-alarm gain/loss here. Keep its broader acceptance open.

| Configuration | Rail, all visible frames | Rail, frames 75–200 | Person | Unmatched detections |
|---|---:|---:|---:|---:|
| Both off | 125/185 | 123/126 | 61/61 | 6 |
| Continuation only | 128/185 | 126/126 | 61/61 | 6 |
| Fresh onset only | 125/185 | 123/126 | 61/61 | 6 |
| Both on | 128/185 | 126/126 | 61/61 | 6 |

Continuation restores rail matches at frames **111, 117 and 197** with either
onset setting. The rail's first STOP remains frame 73; the person's remains frame
8. Earlier rail coverage remains poor: **2/59 visible frames before frame 75** in
every configuration, with misses at frames 1–11 and 27–72. This comparison does
not fix those misses or prove detection at longer range.

The six unmatched detections are the same track (ID 4) at frames 69–74, after its
earlier person matches. There are zero never-matched STOP track IDs, but that
event definition must not hide these six unmatched frame detections. Every
configuration's full detections, coordinates, labels, timing and health are
preserved in the four compressed captures.

With fresh onset toggled, both feature pairs have identical public signals in all
201 frames after excluding `timing_ms` and `health.latency_p95_ms`. Those timing
values are preserved but are diagnostic, not an accepted latency comparison.
The unit tests separately expose the existing P3 risk: fresh onset can veto near
escalation when the current cluster is advisory. This recording does not establish
that the risk is harmless on other data.

## Identity and input

- Measured source: `b84ea8f229be8d11d9db82ebd337198803ce92bf`.
- Source digest: `2fd88d8ba35c62d17a9c5cfa49c73652ba849cbbf36d8691734363d3c062d0eb`.
- Native SHA256: `b5a5c2dc08be8fa1ab00e27dee7662d31413a99f819a760d2d2d4b16b93e8534`.
- Observer: `f121be7`; full runner hash in `acceptance.json` and `summary.json`.
- Original bag: `/data/for_hackathon/doubleT_obstacle`, all 201 frames, one process,
  four sequential detector variants, one numerical thread (804 detector frames).

All variants received independent copies of the same raw float points, channel
IDs, frame IDs and **PointCloud2 header timestamps**, decoded through the selected
committed `replay_node_frames.bag_frames` / `pointcloud2_to_arrays` path. Labels and
reader dependencies matched committed blobs. Source, native, bag, labels and
observer hashes were unchanged after replay. The branch HEAD advanced during the
run for the authorized integration; measured production files stayed identical.

Historical `evaluate_low_height_keep.py` reports used bag receive timestamps and
remain receive-time evidence. This result does not relabel them. The initial
launch stopped before processing because the reproduction bag path included an
extra `/raw`; the corrected path above completed once. No detector result was
discarded or used for tuning.

The actual replay started after the default full gate passed. The archived
runner report retained a planned limitation string referring to a concurrent
gate; no timing acceptance is claimed from this run.

## Artifacts and limits

`summary.json` contains exact effective configurations, source inventory, bag and
label hashes, per-frame input array hashes, complete target timelines and all
paired changes. `acceptance.json` verifies capture/report hashes and public-signal
parity. The four `.jsonl.gz` captures retain all public frame results plus observer
label assignments and unmatched detection indices.

This is one already-known stationary positive recording with existing labels and
matching tolerances. It is not an untouched holdout. The other bags, complete ride,
sets O/F and paired histories are still needed before considering fresh onset for
default use; the comparison supplies no score increase by itself.
