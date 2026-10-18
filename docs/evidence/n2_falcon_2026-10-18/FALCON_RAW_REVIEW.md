# Independent Falcon raw-cloud trajectory review

The raw ROS-frame cloud supports a coherent approaching person-body trajectory
at **108 sampled anchors, frames 1725–4400**, plus a separate uncertain early
upright-target episode at five anchors, frames 1200–1300. This review was completed
before reading detector outputs. It supplies observational association anchors,
not exact segmentation, surveyed gauge truth or exhaustive scene labels.

The [frozen atlas ledger](raw_person_review/atlas_proposals.json) and
[eleven manually bounded positive anchors](falcon_reviewed_anchors.json) have
hashes in the [review receipt](raw_person_review/atlas_review_receipt.json).
Every atlas row has `review_status: reviewed_trajectory_body_core`; the early
rows retain `episode: early_uncertain`. All gauge relations remain unknown.

## What was inspected

The selected three-view sheets show forward/left/up geometry with raw frame-0
background context. Ten additional front-view atlases cover every 25th frame of
the two proposed episodes. A second reviewer independently inspected all ten
atlases and confirmed continuity of the main body. Grey points are all raw crop
context; magenta points are more than 0.25 m from the initial raw cloud. Colour
is a discovery aid and never exact object membership.

- The early episode has only about five to seven returns per inspected crop.
  It moves from about 248 m to 245 m, then retreats and moves laterally toward
  raw left −2 m. Its connection to the later episode across the long gap is
  uncertain; it must not be silently merged into the main person's identity.
- The main episode starts near 249 m, pauses near 243.5 m, approaches to about
  97 m, pauses/turns around 100 m, then approaches to about 3.8 m. Constant-speed
  extrapolation across these pauses is invalid. Sampled raw continuity and the
  much denser near shape support the main person's identity; individual far
  five-return shapes alone do not establish it.
- The discovery height band clips some body support. At frame 3000, the broader
  raw crop shows a substantially taller body than the discovery component.
  Manual anchors therefore retain broader observed body bounds. The fixed
  discovery slope is not an independent ground or gauge survey.
- Background context near the left crop edge at frame 2325 and a separate group
  near raw left +1.5 m at frame 2975 remain outside the body reference.
- At frame 4300 the main body has 356 discovery returns and dimensions about
  0.58 × 0.79 × 1.27 m. A separate nine-return patch at approximately
  [14.60, +0.82, −1.03] m has dimensions only 0.20 × 0.11 × 0.07 m. It may be a
  held appendage or another small return group; its identity and attachment are
  unresolved. It is not an alternative person-body center. The main component
  near forward 15.75 m is the body association reference.
- At final frame 4442 the inspected near volume (forward 0–6 m, left −1.8–1.4 m,
  raw up approximately −2.90–1.10 m) contains no returns. This does not certify
  whole-frame absence: the 2.5 m radial cache minimum and sensor field of view
  limit near-pass support.

## Use and limits

For association, use the reviewed discovery **body-core** bounds with the manual
anchor overrides and explicit matching sensitivity. `raw_crop_bbox` contains
context and must not be treated as an object box. Do not interpolate across the
large gap between episodes; preserve sparse-support uncertainty and report
observation counts separately from claims about in-gauge true/false alarms.

The broad selected sheets initially included a constant-speed *discovery crop*
near frame 1950 that missed the paused target. That crop was corrected using the
full-volume discovery trajectory; the final sheets and frozen ledger use the
observed pause. No first-visible frame is claimed from that extrapolation.

The raw archive/cache remains the provenance source. Every reviewed anchor records
its input NPZ hash; selected manual body bounds additionally record the index-set
hash. The point subsets are assisted observations, not organizer-supplied truth.

A supplementary [top/front/side context sheet](raw_person_review/appendage_context_4250_4325.png)
for frames 4250, 4275, 4300 and 4325 confirms the same dense upright body core
approaching from about 22 m to 13 m. At frame 4300 the separate nine-return patch
is about 1.1 m forward and 0.9 m left of the body centre; its exact identity
remains uncertain. It is retained as context and does not replace or enlarge the
body-core association box. This additional review does not change the frozen
anchor files or their hashes.
