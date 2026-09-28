# Detector evaluation protocol — 28 September 2026

`protocol.json` fixes development and reserved evaluation seeds, geometry, placements,
metrics and acceptance before this cycle's detector candidates are measured. It supplements
the existing real recordings. Synthetic results cannot establish real-world transfer.

The production concern is sustained output: a single STOP somewhere in a sequence does not
count as reliable detection. The protocol reports target-matched STOP frames, visible-frame
recall, confirmation delay, consecutive STOPs, missed intervals, false STOPs and differences
between float clouds and the same clouds quantized to centimetres.

The reserved split must be run only after candidate source/config hashes are fixed. Its
results may reject a candidate. If those results inform another change, the split has been
used for development and a later report must say so.

The existing `tests/fixtures/synthetic_lidar_v1` is development data. Automated tests consume
its arrays and masks without Open3D. The broader generated protocol uses the existing round
tunnel raycaster and varies only parameters that it models consistently. Grade is fixed at
zero because its rail and bench meshes do not follow a nonzero floor grade; geometry stops
returning points at 210 m. New point clouds stay outside Git; reports retain compact per-frame
metrics, seeds, code/config hashes and input digests.
