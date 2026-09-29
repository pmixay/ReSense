# Synthetic LiDAR detector fixture v1

This fixture is generated entirely from the repository's round-tunnel mesh and Pandar128
ray grid. It is controlled regression data, **not organizer data, not real LiDAR, and not
evidence of performance on unseen tunnels**.

## Files

- `frames/**/*.npy`: ordinary cache-compatible `COMPACT16_DTYPE` point arrays in sensor
  coordinates (`xyz` in centimetres, intensity and ring as bytes).
- `masks/**/*.bits.npy`: bit-packed per-object masks aligned with the corresponding point rows.
  Decode with `np.unpackbits(mask, bitorder="little")[:point_count].astype(bool)`.
- `manifest.json`: seeds, sensor transform, mesh placements, frame stamps, hashes, point
  counts, masks, and scenario schedules.

The `rail_straddle` scene is a stationary 0.4 x 0.6 x 0.31 m box across one rail at 24 m.
Its 12 frames are all generated with visible object returns. To form a gap variant, load the
matching object mask and remove those point rows from frames `[6, 6 + gap_frames)`, with
`gap_frames` in 0, 1, 2, or 3. This models missing target returns; object rays stay occluded
behind the object. Six visible frames precede the gap and three follow it.

`clear_tunnel` supplies empty-scene frames. `single_frame_transient` references clear frames
with one visible target frame between them. `range_edge_survey` contains individual 0.3 m and
0.5 m box scans at 50/75/100 m, varying center/edge placement, yaw, and seed. Those far samples
are for point-coverage probes; they are not guaranteed detections.

Regenerate from the repository root with:

```sh
python scripts/generate_synthetic_lidar_fixture.py --output tests/fixtures/synthetic_lidar_v1
```

The command only overwrites an existing output when its manifest has this fixture's schema.
The fixture itself can be loaded without Open3D; Open3D is only needed to regenerate it.
