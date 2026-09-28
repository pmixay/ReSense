# Get the data

The recordings are the organizers' and are never committed to the repository. Everything reads
them from a directory mounted or passed as a path, by default `/data/for_hackathon`.

## The recordings

| set | what | link |
|---|---|---|
| six recordings | 20–88 s each from different parts of the metro, one topic each; real obstacles only in `doubleT_obstacle` (a person crossing ≈ 55–57 m ahead, an object on the right rail) | `Датасет.zip`, 3.7 GB, [Google Drive](https://drive.google.com/file/d/1WTlR2wDSuEHTOARGK_gZeXDTZ9RZpswu/view) |
| `new_data` | a 20-minute, ~13 km ride with no obstacles, 221 split `.db3` files, 90 GB unpacked | `new_data.zst`, 17.1 GB, [Yandex Disk](https://disk.yandex.ru/d/N8IUpAyd7jyvow) |
| `cloud_with_fake_obj` | 151 s with ten objects the organizers ray-cast into a real recording | 1.75 GB, [Yandex Disk](https://disk.yandex.ru/d/KpkG_yKoGk-vHQ) |

Sizes, frame counts, topics and scenes of every bag:
[`docs/DATASET.md`](https://github.com/pmixay/ReSense/blob/main/docs/DATASET.md).

## Unpack only what you need

The download is nested (zip → zip → zstd tar). `scripts/unpack_dataset.py` streams it and writes
only the bags you ask for (needs `zstandard`, part of `pip install -e ".[dev]"`):

```bash
python scripts/unpack_dataset.py Датасет.zip --list
python scripts/unpack_dataset.py Датасет.zip --out /data --only doubleT_obstacle,roundT_doubleT
python scripts/unpack_dataset.py Датасет.zip --out /data                        # all six (~22 GB)
python scripts/unpack_dataset.py https://disk.yandex.ru/d/KpkG_yKoGk-vHQ --out /data   # cloud_with_fake_obj
```

By hand: `tar --zstd -xf for_hackathon.zst -C /data` after the two unzips.

The two recordings the CI cold-start check uses can be fetched and verified against pinned
checksums with `scripts/fetch_cold_bags.sh <dir>` (downloads only when they are not already there).

## Check a new bag

```bash
resense info /data/for_hackathon/<bag>       # metadata + the first frame: topic, frame id, width, points
resense run --bag /data/for_hackathon/<bag> --limit 30
```

The track model must lock in the first frames and an empty tunnel start should raise no alarm. If
`track.center` jumps or `n_corridor` stays 0 in the output, the sensor axis mapping
(`sensor.forward/left/up`, or the node's `sensor_forward/left/up`) does not fit the bag. The full
intake recipe: [`docs/DATASET.md` “How to check a new bag”](https://github.com/pmixay/ReSense/blob/main/docs/DATASET.md#how-to-check-a-new-bag-intake-recipe).

## Mounting data into containers

The scripts mount the parent directory of the bag path at `/data`; `docker compose` mounts
`$RESENSE_DATA` (default `/data/for_hackathon`) and plays `$RESENSE_BAG`; a plain `docker run` takes
`-v <host dir>:/data:ro`.
