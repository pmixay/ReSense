# P1 E2: offline source rebuild and uid-1000 playback (15 October 2026)

**Result: local Docker checks PASS.** Implemented on
`p1/offline-rebuild-2026-10-15`, based on `origin/final/silent-misses`
`d0d17bb5dcc2b5b23f9ddd96744a8fd0424e0b5d`. The release workflow has been updated;
its tagged GitHub Actions run remains an integration check for the next release.

## Measured checks

Docker Desktop became available during this task: Engine 29.2.0, Linux containers,
WSL2 x86-64, 12 logical CPUs and about 6.7 GiB Docker memory. See `docker-version.log`.
The runtime image was built from this worktree with `WITH_TOOLS=0`.

| Check | Result / evidence |
|---|---|
| Runtime build | PASS, `runtime-build.log` (the final recorded build reused earlier online build layers; its 6.828 s is **not a cold build time**) |
| Archive save/load | PASS, `archive-save.log`, `archive-load.log`; same original image ID and RootFS layers before and after loading |
| Actual offline compilation | PASS, `offline-build.log`: `--network none --pull=false --no-cache`, **18.609 s** locally, exact loaded `resense:p1-e2-check` as FROM |
| Installed Python and native imports outside source | PASS on runtime and offline images, `runtime-installed.log`, `offline-installed.log`; package in `/usr/local/lib/python3.10/dist-packages/resense`, native enabled |
| ROS overlay and data | PASS: import the new symlink-installed node, identical installed/source launch and authoritative config bytes, no broken install symlinks |
| uid 1000:1000, no HOME override | PASS on both images, `runtime-nonroot.log`, `offline-nonroot.log`; actual `HOME=/`, `ROS_HOME=/tmp/.ros`, `ROS_LOG_DIR=/tmp/.ros/log` |
| Synthetic player | PASS: each uid-1000 check writes a three-message ROS sqlite3 bag with the runtime's `rosbag2_py`, resolves launch arguments, then runs `ros2 bag play ... --read-ahead-queue-size 10 --disable-keyboard-controls` with network none |
| Host-network player | PASS on both images with `--net=host --user 1000:1000`, no HOME override; `runtime-nonroot-hostnet.log`, `offline-nonroot-hostnet.log` |
| Entrypoint / default command / environment | Runtime and rebuilt image configurations identical; original runtime tag/ID unchanged (`result.json`) |
| Changed-source stale-cache regression | PASS, `mutation/result.json`, `mutation/build.log`, `mutation/probe.log`: new native symbol, detector Python module, ROS Python module, launch and config markers all present; 17.219 s offline build |
| Release tooling unit tests | **53 passed**, `release-unit-linux.log` |
| Rebuilt native kernels vs numpy | **26 passed, 2 deselected** (the two Open3D detector/tunnel cases), `native-unit-linux.log` |
| Static checks | PASS: focused Ruff, Python AST, release YAML parse and new workflow run-block Bash syntax; `lint.log`, `workflow-bash-syntax.log`, `supplemental.json` |

`result.json` records exact commands, exit codes, timings and image IDs. The temporary
uncompressed archive was removed by the verifier; all test containers used `--rm`.
No user images, containers or build caches were removed. The two unmodified reusable tags are:

* `resense:p1-e2-check` — original runtime, ID
  `sha256:91c36b2fdbc39a70e0f3a53dd8a3c84ef6fb1ae28d97ef37bcb3377c3153fd5e`
* `resense:p1-e2-offline-check` — unmodified source rebuilt offline, ID
  `sha256:37292b1370f15a344fd43986b85cb76c170dd22a61b8bd15b57d6f42cdd2b381`

`resense:p1-e2-mutation-check` is retained solely for the changed-source test. Its extra
probe modules/symbol/comments live only in a temporary build context and that test image.

## Why the rebuild clears inherited artifacts

`inherited-caches.log` records the trap in the original runtime image: both
`/opt/resense/build/lib.linux-x86_64-cpython-310/resense/_resense_native*.so` and
`build/temp.linux-x86_64-cpython-310/native/resense_native.o` exist. The entrypoint's
`PYTHONPATH` also includes the ROS build and install trees. Simply copying newer code and
calling pip/colcon can therefore appear successful while reusing old binaries or overlay data.

The offline Dockerfile uninstalls the wheel **from `/`** (so local `resense.egg-info`
cannot shadow installed metadata), checks that the old installed package is gone, and removes
the inherited source, setuptools build tree and complete ROS workspace before COPY. It
discards accidentally copied native/bytecode artifacts, uses `PIP_NO_INDEX=1` and
`pip3 install --no-deps --no-build-isolation .`, and requires the new native library.
Colcon starts from a clean workspace and a freshly sourced Humble underlay, with inherited
overlay path variables unset. The mutation regression deliberately backdates changed C++
source to 1970, older than the inherited `.o`; a new exported symbol proves recompilation.

The online runtime build explicitly installs setuptools 75.6.0, wheel 0.45.1 and packaging
24.2. The first attempted build exposed Jammy packaging 21.3's incompatible
`canonicalize_version` API; adding the compatible packaging pin fixed it. These build tools
are now in the archive, so the offline PEP 517 backend never needs an isolated download.

Windows checkout CRLF shell scripts caused the first container start to fail despite a
successful build. The runtime Dockerfile now normalizes those shell scripts inside the image.
Entrypoint content/transport behavior is otherwise preserved. The offline build also removes
its root-owned launch-check logs before export, leaving uid 1000 free to create `/tmp/.ros`.

## Commands for the parent / next release

After loading the **new E2-capable** release archive, use its exact tag (substitute the actual
release version). Archives predating this change do not carry the new pinned build backend.

```sh
TAG=v1.2.0  # substitute the actual E2-capable release tag
docker load -i "resense-image-$TAG.tar.gz"
docker build --network none --pull=false --build-arg "RELEASE_IMAGE=resense:$TAG" -f docker/Dockerfile.offline -t resense:offline .
docker run --rm --network none -w / resense:offline python3 /opt/resense/scripts/check_offline_image.py
docker run --rm --network none --user 1000:1000 -w / resense:offline python3 /opt/resense/scripts/check_nonroot_player.py
```

`RELEASE_IMAGE` defaults concretely to the archive's `resense:latest` alias. The release
workflow explicitly passes `resense:$TAG` immediately after reload, records the offline
duration, runs the changed-source regression and non-root checks, and retains their logs.
Its existing original-release acceptance steps continue to use `resense:$TAG`.

Reproduce the complete local evidence with
`python docs/evidence/offline_rebuild_2026-10-15/verify.py` in this exclusive worktree.
The verifier owns the two `p1-e2-*-check` tags above; the mutation test refuses to overwrite an
existing mutation tag, so choose a new `--image` when rerunning that test independently.
Run `python docs/evidence/offline_rebuild_2026-10-15/verify.py --supplemental` for the
additional lint, host-network player and Linux unit checks.

The Windows host's complete release unit run initially reported 19 passed / 34 failed because
its `bash` resolves to WSL without `/bin/bash`. All 53 passed in a disposable Linux runtime
container. That supplementary container installs pytest 8.4.2 online, disables unrelated
ROS pytest plugin autoload (which otherwise skips collection), and is removed afterward;
it does not alter either image tag. The native-kernel subset uses the same method. These
supplementary pytest installs are separate from the network-none build/run evidence above.

## Remaining integration

* Parent: merge E2 together with S1/C1; update shared README/ARCHITECTURE/DECISIONS and the jury
  rebuild command. Quote a tagged CI measurement only after the updated release job runs;
  the local times above are not CI measurements.
* Parent: original organizer-bag S1 timing/acceptance. This evidence checks E2's runtime CLI
  and a tiny synthetic player, not detector timing or real-bag decision counts.
* Next release: publish/reload the new archive and run the updated release workflow. Local
  save/load did not remove unrelated daemon images or caches; the offline build used
  `--no-cache` instead. The release runner retains its existing archive/cache-removal check.
