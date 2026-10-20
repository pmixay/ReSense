# Falcon clear distance: known limit for the 1.2.0 handoff

**Disposition, 20 October 2026:** document the finding as a known limit, the
option recommended in the deadline handoff. This handoff submits documentation,
not a Falcon detector fix. The finding remains unresolved in the reviewed source.

## Registered observation

P4's independent review, merged in [PR #46](https://github.com/pmixay/ReSense/pull/46),
found **38 non-STOP frames** with `clear_distance` **3.0–40.0 m** beyond a
**person-like object 2.5–7 m ahead**. All occur in the 42-frame interval
**4373–4414** of `falcon_test_second_dark` (4,443 frames total).

The review was first made on `cc6226e` and reproduced on `f56ad5e`; this note
does not relabel those measurements as acceptance of a later detector revision.
Immutable sources at review commit `6d5fd4ba`:

- [Review and limitations](https://github.com/pmixay/ReSense/blob/6d5fd4ba/docs/evidence/p4_review_h_mount_falcon_2026-10-20/README.md)
- [Per-frame values and the 38-frame list](https://github.com/pmixay/ReSense/blob/6d5fd4ba/docs/evidence/p4_review_h_mount_falcon_2026-10-20/out/person_clear.txt)
- [Raw-return inspection images](https://github.com/pmixay/ReSense/tree/6d5fd4ba/docs/evidence/p4_review_h_mount_falcon_2026-10-20/out/png)

Affected frame IDs:

```text
4373 4374 4375 4376 4377 4378
4383 4384 4385 4386 4387 4388 4389 4390 4391 4392 4393 4394
4395 4396 4397 4398 4399 4400 4401 4402 4403 4404 4405 4406
4407 4408 4409 4410 4411 4412 4413 4414
```

Examples: frame 4385 reports **21.0 m** clear; 4396 reports **9.7 m**;
4405 reports **37.6 m**; 4414 reports **40.0 m** while 205 near returns
occupy **2.5–2.7 m**. These frames are `CAUTION`, with no STOP detection.
There are 39 non-STOP frames in the full interval, but only 38 meet the
clear-overclaim condition: frame 4379 is not counted. Frames 4380–4382 are STOP.

## Interpretation and release wording

The track model has lost its rail pair and the fitted bed/height reference
wanders. H′ removes ceiling detections but does not recover the missed near
body. The Falcon density cap (48.2 m) is applied only in the node's
`conservative` / `small_candidate` range policies; it cannot correct these
shorter erroneous detector distances. The default `legacy` path does not call
that density model. Switching off the density model would report zero in the
non-legacy Falcon path, but is not a repaired detection or a STOP.

**Release wording:** “Falcon near-range limitation: 38 reviewed non-STOP frames
report clear distance beyond a person-like object 2.5–7 m ahead. Clear distance
is an estimate, not confirmation that the track is obstacle-free.”

The object identity has not been established by independent surveyed Falcon
ground truth; retain the review's **person-like** description. The range-policy
check is the node-faithful offline replay, not a running ROS graph. Neither
qualification removes the observed overclaim.

Any later fix is a separate detector change and needs its exact-source gate,
independent review and P3 disposition before integration. Existing experimental
repair results are not acceptance of this handoff or authorization to ship them.
