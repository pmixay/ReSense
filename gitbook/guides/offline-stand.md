# Stand without internet

The organizers' test machine has no internet. `docker build` cannot run there (the base image,
apt and PyPI all need the network), so the image travels as an archive; nothing at run time needs
the network.

| stage | needs the network? |
|---|---|
| `docker build` | yes: Docker Hub, the ROS and Ubuntu apt archives, PyPI |
| `docker load` of the archive | no |
| the node, launch file, entrypoint, compose services, RViz, `foxglove_bridge` | no (DDS over UDP on the host's interfaces; the loopback alone is enough) |
| the web dashboard | no (fonts and `roslib` are bundled) |
| Foxglove desktop app on a viewer's laptop | no |

## Prepare (on a machine with internet)

```bash
scripts/export_image.sh            # → dist/resense-image-<version>.tar.gz and .sha256
```

or download the CI artifact of the commit ([Get the Docker image](../getting-started/get-the-image.md)).
Copy both files to the stand.

## On the stand

```bash
scripts/load_image.sh resense-image-<version>.tar.gz    # checksum, docker load, a start with --network none
```

then the jury commands of [Run on a bag](../getting-started/run-on-a-bag.md), or
`scripts/play_bag.sh <bag> --archive resense-image-<version>.tar.gz` in one step.

`load_image.sh` exit codes: 2 bad argument, 3 no Docker, 4 checksum mismatch, 5 the loaded image
failed its check.

## Rehearse it

Disconnect the network (cable out, Wi-Fi off), then:

```bash
IMAGE_TAR=dist/resense-image-<version>.tar.gz OFFLINE=1 ./scripts/dry_run.sh <bags>/doubleT_obstacle
SKIP_BUILD=1 OFFLINE=1 ./scripts/dry_run.sh <bags>/roundT_doubleT --expect-clear --max-alarm-frames 2
```

`IMAGE_TAR` loads the archive instead of building; `OFFLINE=1` runs node, player and recorder with
`--network none` and refuses to build. Then play a bag by hand from a normal user's console, still
offline. See [Acceptance test](acceptance-test.md).

The step-by-step offline rehearsal on a cloud VM, with a safety net that restores the network:
[`docs/VM_GUIDE.md` §5](https://github.com/pmixay/ReSense/blob/main/docs/VM_GUIDE.md#5-offline-rehearsal).

## Building offline (best effort)

After `docker load`, in the source tree of the same commit:

```bash
chmod -R u+rwX,go+rX,go-w . && docker build --cache-from resense:<version> -t resense -f docker/Dockerfile .
```

The archive's image carries its own layer cache and the base image's tag, so every step can come
from it. If it does not work, the loaded image is untouched and runs as before.
