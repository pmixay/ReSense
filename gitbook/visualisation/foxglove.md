# Foxglove (remote demo)

For an audience that is not at the machine, Foxglove replaces a remote desktop: the image already
contains `foxglove_bridge`, and viewers open the prepared layout in their own Foxglove (desktop app
or [app.foxglove.dev](https://app.foxglove.dev)).

## On the demo machine

With the bags in `$RESENSE_DATA` (default `/data/for_hackathon`):

```bash
docker compose --profile viz up detector foxglove     # the node + the bridge on port 8765
docker compose --profile tools up player              # plays $RESENSE_BAG once
```

For a looping demo, add `--loop` to the player command in `docker-compose.yml`.

## On each viewing laptop

1. Foxglove → **Open connection → Foxglove WebSocket → `ws://<demo host>:8765`**.
2. **Layout → Import from file →** [`web/foxglove_layout.json`](https://github.com/pmixay/ReSense/blob/main/web/foxglove_layout.json).

The layout has a 3D panel (camera behind the sensor looking down the track, both raw-cloud topics,
`/resense/corridor_points`, `/resense/markers`), an indicator of `/resense/decision` (green GO,
orange CAUTION, red STOP, violet FAULT), plots of `nearest_distance`, `clear_distance`,
`latency_ms` and `fps` over the last 30 s, and the raw `/resense/status` JSON.

## Check the wiring before the audience joins

```bash
pip install websockets
python web/demo/check_foxglove_live.py --url ws://127.0.0.1:8765 --require-freshness
```

It checks that every topic of the layout is advertised and that messages arrive;
`--require-freshness` also requires a current `/resense/status`.

## Over a slow link

The raw cloud is 8 MB (120° field of view) to 24 MB (360°) per frame at 10 Hz. Uncheck the two
raw-cloud topics in the 3D panel and keep `/resense/corridor_points` (a few thousand points), the
markers and the plots: that is the whole picture of what the algorithm does at a few hundred kB/s.

## Known limits

* The indicators show the **last received** value and never expire it: after a disconnection a
  cached GO or STOP can stay on screen. Check the connection and the freshness in
  `/resense/status`, or use the [web dashboard](web-dashboard.md), which expires results itself.
* If a panel is empty after import, re-pick its topic in the panel settings. The 3D panel follows
  `resense_lidar`, the node's static transform.
* Port 8765 must be reachable from the viewers; the bridge has no authentication, so expose it only
  on a trusted network.
