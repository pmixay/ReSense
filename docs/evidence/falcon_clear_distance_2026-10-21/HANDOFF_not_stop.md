# Finding for the detector owner: why the object 2.5-7 m ahead is not STOP in Falcon frames 4373-4414

Finding only. No decision logic was changed in this lane (the lane's switches only lower `clear_distance`).
Source: the v1.2.0 control run (`6ee469c`, detector bytes = v1.2.0) of the whole Falcon recording, state dumped from the
detector itself for frames 4360-4430 (`scripts/run_falcon.py --dump`: corridor indices `res.corridor_idx`, cluster
membership of every return and the owning track, the model rail head `track.rail_z`, the mount plane), analysed by
`scripts/person_trace.py`. Table: `results/falcon/person_trace.tsv.xz` (every frame); pictures: `results/png/person_trace_f*.png`
(side and top view; the P4 pictures are `p4_review_h_mount_falcon_2026-10-20/out/png/person_f43xx.png`).

"Person-like set" = returns with X >= 2.4 m, |Y| < 0.9 m, 0.2-1.6 m above the mount plane (z = -1.77 m, from the
calibration, constant), up to 8 m behind the nearest one. It is defined without the track model; the detector's own
membership of these returns is what the table counts. Its size is 205-1,159 returns per frame in 4373-4414 (P4's numbers).

## What decides in each frame (traced, not reconstructed)

| frames | decision | what the detector did with the returns |
|---|---|---|
| 4366-4371 | STOP | track 652 (1,460+ hits, reported) on a cluster of 86-294 returns in the gauge: only the lower part of the object (cluster 0.41 x 0.51 x 0.30 m) |
| 4372 | STOP | held detection (confidence 0.75, predicted position), **0 of 905 returns in the corridor**: the bed model jumped 2.9 m above the mount plane |
| 4373-4375 | CAUTION | **0 returns in the corridor**: all 949 / 959 / 930 returns are below the model gauge floor (model bed 2.0 / 1.6 / 1.6 m above the plane); track 652 gone |
| 4376-4379 | CAUTION | bed 1.4-1.25 m over the plane; 16-205 returns reach the strict gauge and 66-205 are in a cluster of a **new track 1100** (clusters of 29-65 returns): hits 1, 2, 3, 4 of the 5 needed |
| 4380-4381 | STOP | track 1100 at 5 and 6 hits (clusters of 72 / 67 returns, 0.35 x 0.53 x 0.25 m) |
| 4382 | STOP | held detection again, 0 of 983 returns in the corridor (bed 2.9 m over the plane) |
| 4383-4398 | CAUTION | **0 returns in the corridor**: the model rail head is 3.7-4.2 m over the mount plane (at the tunnel ceiling, picture `person_trace_f4396.png`), every return of the object is 1.9-3.2 m below the model's gauge floor; from 4395 the nearest returns are also closer than `gauge.range_min` 3.0 m (1 -> 21 returns) |
| 4399-4409 | CAUTION | **0 returns in the corridor**: bed 2.0 m over the plane (model h of the object -0.8 .. -0.6 m); 3-564 returns closer than 3.0 m |
| 4410 | CAUTION | bed 1.1 m over the plane: 47 corridor returns, 23 in the strict gauge, track 1119 with cluster of 15 returns, hit 1 |
| 4411-4416 | CAUTION | the bed model is back (0.6 .. 0.25 m over the plane), the object is above the gauge floor, but **all** of its 671 / 623 / 531 / 205 / 88 / 11 returns are nearer than `gauge.range_min` = 3.0 m: outside the corridor by the range gate |

So the rules that decide are, in order of how many frames they cover: (1) the corridor is cut against a bed model that
has left the mount plane by 1.3-4.2 m (no rail pair in all 42 frames, rail lock 0 % of the last 20; `track.rail_score`
-1.0 but frame 4384 with 0.008) and the whole object lies below the model's gauge floor; (2) in 4411-4416 the
3.0 m range gate (`gauge.range_min`), the object is simply too near; (3) in 4376-4381 the object is partially in the
gauge but the confirmation needs 5 hits (a new track after the old one is lost). Gauge width, the speed-based rules and the **H' mount
cross-check are not what decides for this object**: H' (`cluster.mount_cross_tol`) acts in frames 4394-4401 on a *different*
cluster at 9.4-9.7 m (and 11.1-11.2 m): 140-550 returns, 0.12-0.33 m over the model bed, reason `height_conflict` in 4394-4398, `elevated` in 4400-4401;
this is the cluster that caps `clear_distance` at 9.4-9.7 m; with H' off P4 found these 8 frames to be STOP, a false STOP on the tunnel ceiling) and the
person-like returns of those frames are not in a cluster at all.

## Is it a person inside the gauge? (raw points)

* Inside the gauge by the detector's own corridor coordinates: lateral offset from the model axis -0.2 .. -0.3 m (median) against the
  strict half-width 1.05 m, and in the sensor frame Y -0.21 .. +0.89 m; in the frames where the bed model is usable (4366-4371, 4376-4381,
  4410) 16-754 of its returns are in the strict gauge membership.
* Shape: a compact vertical object, 0.5-0.9 m wide, whose top is 1.53-1.61 m above the mount plane in every frame (constant while its
  nearest return approaches from 5.8 m to 2.5 m in 42 frames, i.e. about 0.08 m per frame), consistent with the upper body of a standing person
  (pictures). **Only its upper part is seen**: the lowest scan line of the Falcon is -9.5 .. -11.5 degrees, so at 2.5-3 m nothing below
  1.2 m above the plane is visible, at 4.3 m nothing below 0.86 m (checked on the cloud: lowest return of all objects in the frame at X 2.4-3.2 m: 1.19-1.22 m above
  the plane in frames 4396 / 4413). The visible part is 0.3-0.7 m of height. A hanging or elevated object of the same section cannot be
  excluded from the returns alone; there is no surveyed ground truth for the object (P4's wording "person-like" is kept).
* By the organizers' rule (everything inside the gauge is an obstacle) it is an obstacle inside the gauge, 2.5-7 m ahead, that the detector
  reports as STOP only in 4366-4372 and 4380-4382 (10 of the 49 frames from 4366 to 4414), and in 4383-4416 not at all.

## Handoff

* The loss is upstream of every decision rule: when the track model has no rail pair and its bed leaves the mount plane
  (the calibrated sensor height is constant here, -1.77 m), the corridor is cut against the wrong bed. A cross-check of the bed against the
  mount plane exists (H', `cluster.mount_cross_tol`) but is applied only to clusters; the missing piece is a use of the same disagreement
  for the corridor itself (or a hold of the last good bed) in the near field. Not designed or measured here.
* `gauge.range_min` = 3.0 m leaves frames 4411-4416 (object at 2.5-3.0 m) without any candidate regardless of the bed; at a closing
  speed of 1 m/s that is 2-3 s, at the 0.8 m/s of this recording an object that was not STOP at 3 m is simply not seen again.
* Until then the clear distance must not claim range in these frames: `health.clear_lost_model` (this lane) reports 0 while the model is on
  its prior, which covers all 39 frames; it does not make any of them a STOP.
