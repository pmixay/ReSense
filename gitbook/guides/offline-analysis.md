# Offline analysis without ROS

The detector is a plain Python library (`resense/`, numpy / scipy / scikit-learn, optional C++
kernels). The `resense` command runs it on a bag directory directly, with no ROS installation.

## Install

```bash
pip install -e ".[dev]"      # numpy scipy scikit-learn pyyaml + rosbags zstandard matplotlib open3d pytest
                             # the C++ kernels (native/) are compiled when a compiler is present
```

Without a compiler, or with `RESENSE_NATIVE=0`, the numpy path runs with the same output, only
slower. `scripts/build_native.sh` builds the kernels without pip.

## Commands

```bash
resense info  /data/for_hackathon/roundT_doubleT                     # bag metadata and first-frame stats
resense run   --bag /data/for_hackathon/doubleT_obstacle --out results.jsonl --render out/   # per-frame JSON + a PNG per frame
resense bench --bag /data/for_hackathon/roundT_doubleT --every 5     # timing per stage
resense summarize results.jsonl                                      # alarm events, per hour / km, latency
```

Useful options of `run`: `--every N` (every N-th frame), `--start`, `--limit`, `--topic`,
`--config <yaml>` (another parameter file), `--ego-speed <m/s>` (a known train speed enables
multi-frame accumulation), `--quiet`. `--npy <dir>` reads cached frames instead of a bag.

The JSONL written by `run --out` is the same per-frame result the node publishes on
`/resense/status`; load it into the [web dashboard](../visualisation/web-dashboard.md) to replay it.

## Synthetic obstacles

Real obstacles exist in only one recording, so positives at other ranges come from objects
ray-cast into real empty frames with the sensor's own beam pattern:

```bash
resense inject --bag /data/for_hackathon/roundT_doubleT --every 10 --out data/synth \
               --distances 10:250 --kinds person,box,plank
resense eval data/synth                  # recall by range on the injected set
```

`inject` also takes `--placement bed|legacy`, `--sequence N --speed <m/s>` (an approaching object
over N frames) and `--augment`. The protocol for the evaluation sets:
[`docs/EVALUATION.md`](https://github.com/pmixay/ReSense/blob/main/docs/EVALUATION.md).

## Evaluate against labels

```bash
resense eval --bag /data/for_hackathon/doubleT_obstacle --gt labels/doubleT_obstacle.json --repeat 1 --text
```

Label format: [`docs/DATASET.md` “Label format”](https://github.com/pmixay/ReSense/blob/main/docs/DATASET.md#label-format-gtjson).
`web/label_tool.html` is the browser tool that makes such labels.

## The real-data report card

Frames are cached once, then the scripts run over every recording:

```bash
for b in /data/for_hackathon/*/; do
  python scripts/cache_frames.py $b /data/cache/$(basename $b) --every 1 --int16 --stamps
done
python scripts/eval_real.py --cache /data/cache --out out/eval       # false alarms, the labelled person / object, latency
```

The single results check for detector changes is the regression gate: [Changing the
detector](../development/detector-changes.md).
