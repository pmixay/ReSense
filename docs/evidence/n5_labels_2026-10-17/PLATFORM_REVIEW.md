# Platform labels: exact reference and reviewed extension

The complete file [labels_synthetic_platform.json](labels_synthetic_platform.json)
contains all **386 frames**, with **696 object rows**. Frames 0–314 retain the
previous exact labels' bounding boxes, distances and point counts. Frames 315–385
add the same person-shaped object (`obj03`) from reviewed raw geometry. These
labels are development evidence; the extension is a team annotation.

The root reviewer examined every extension frame in the nine contact sheets in
[platform_review/](platform_review/): full forward scene, local top view and local
front view. The person silhouette remains identifiable in all 71 frames. Its
forward position approaches from about 11.6 m to 7.8 m, then stays nearly constant.
No additional inserted object was identified in that review. This does not assert
the absence of every possible real obstacle in the source scene.

## Method and independent control

The annotator initialized raw-point tracking at frame 300 from the visible body
shape and followed its geometry over time. Intensity 1 was used only within the
reviewed object region; it was not treated as a scene-wide obstacle label. The
reviewed per-frame bounds are preserved in
[platform_reviewed_boxes.json](platform_reviewed_boxes.json). No detection,
warning, STOP or clear-distance output selected these points.

The extension extraction was also tested on **all 60 frames 255–314**, where the
unaltered source scan exists in Set O. Comparison against exact float32 point
differences recovered **58,638 / 58,638 person points**, with **93 background
points** included: **100% point recall, 99.84165% precision**. This is a control on
the same person and scene, not a general accuracy claim for the other objects.
Sparse background points expanded the control boxes by at most **0.221 m forward**
and **0.269 m vertically**. Extension boxes and counts are therefore approximate;
their point membership must not be described as exact ground truth.

[platform_extension_control.json](platform_extension_control.json) gives every
control frame and the error bounds. A separate rebuild of the original 315-frame
reference check reproduced **119,377 exactly-new points**, **119,346 labeled
points**, and the same **31 non-marker residual points**:
[platform_reference_check_rebuilt.json](platform_reference_check_rebuilt.json).

## Coordinates and gauge uncertainty

Coordinates are Pandar sensor axes mapped to forward = −y, left = +x, up = +z.
The archived observation runs remain in pending/identity mount states; this makes
their detection boxes compatible with the mapped raw axes for these recordings.
The identity check is specific to these archives, not a general sensor assumption.

The old track-relative lateral position and measured gauge flag are retained as
`original_axis_lateral` and `original_gauge_measured`. Matching uses the bounding
box and `lateral_sensor`, rather than mixing sensor and fitted-track coordinates.
Near the sensor, the person is inside, the outer box is outside, and the rail-edge
box stays `boundary_uncertain`. Rows beyond 60 m or previously implausible rows
use `unknown` gauge membership because independent track placement is unresolved.
Unknown membership is `null`, never silently converted to outside. Object identity
and first matched STOP can still be scored on those rows.

## Reproduce the file and control

```bash
python docs/evidence/n5_labels_2026-10-17/build_platform_labels.py \
  /path/to/decoded/synthetic_platform \
  --reference /path/to/decoded/cloud_with_fake_obj
```

Input archive hashes and every decoded frame hash are recorded in the
[data intake manifest](../n5_c2_execution_2026-10-17/data_intake.json).
The script re-extracts the reviewed boxes, checks their point counts, preserves the
exact region, and repeats the reference control. The reviewed boxes are annotation
inputs; reproduction does not substitute for the recorded visual review.
