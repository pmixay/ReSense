# Conditional range-metric evidence

**No STOP gain demonstrated; production unchanged.** These 138 frames use rounded track
geometry from the 26 September P3d trace with the current default corridor selection.
They are not a baseline replay, candidate detector run, or unseen validation.

The observer matches the original organizer fixture to set O caches by exact quantized
XYZ/intensity multiplicity. Every source return matched, with zero extra indistinguishable
copies. Full source, cache, historical geometry and code hashes are in each compressed
case. The input fixture covers only 15–80 m. The observer omits low-object processing,
accumulation, shape filters and tracking; neighbor connectivity precedes DBSCAN core tests.

| Organizer object | Frames | Frames with excessive source/background links | Frames with less connected background after edge filter | Frames gaining source voxels after radial subdivision |
|---|---:|---:|---:|---:|
| Small center | 39 | 4 | 4 | 3 |
| Small on rail | 37 | 16 | 3 | 4 |
| Large above | 34 | 0 | 0 | 8 |
| Thin hanging | 28 | 0 | 0 | 0 |

No source/background mixed voxel occurs in any measured frame. Counts are correlated
frames from four inspected source approaches, not independent detection trials.

For the cube, frames 323/324/325/327 at 78.79/77.19/75.56/72.30 m contain one excessive
source/background edge each. Their physical lengths are 1.48/1.45/1.35/1.20 m against
linear-radius bounds of 1.04/1.03/1.01/0.99 m. Removing those edges reduces connected
background returns from 20/23/17/38 to zero. All four retain **only two strict source
voxels**, below the existing gauge minimum of three. Neither graph filtering nor radial
subdivision changes that count. Do not lower the gauge threshold on this evidence.

The cube's three source-voxel gains occur only at 25.5, 22.1 and 15.3 m. The available
measurements therefore support long neighbor links as a cause of background merging,
but do not support radial voxel collapse as the cause of missing far-cube support.

The 39 cube rows were recomputed with the native library built: every per-frame field
matches the NumPy run. `summary.json` records that comparison and the library hash.
Four diagnostic tests and Ruff passed. Runtime from instrumentation is not scored.

## Reproduce

From base `786a5fb` plus this observer, run the following command for each object named
in the table, changing `--object` and the output filename:

```bash
python scripts/diagnose_range_metric.py \
  --cache /cycle/cache/cloud_with_fake_obj --object small_center --limit 40 \
  --out out/range_metric/small_center.json
```

The supplied trace and fixture paths default to the committed evidence files. The raw
JSON output was compressed with deterministic gzip (`mtime=0`) for storage. The artifact
manifest hashes the four outputs and summary. Native parity compares `rows` before and
after `scripts/build_native.sh`; metadata correctly reports the differing runtime mode.

The [diagnostic protocol](../../../RANGE_METRIC_DIAGNOSTIC_2026-09-28.md) records the
factorial comparison, false-alarm controls, and next motion-supplied upper-bound study.
That study remains proposed; no accumulated candidate or STOP result has been measured.
