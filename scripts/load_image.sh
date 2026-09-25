#!/usr/bin/env bash
# Load the image archive made by scripts/export_image.sh and prove that the image runs with no
# network at all (the test stand has no internet, docs/organizers/answers.md §7).
#
#   scripts/load_image.sh dist/resense-image-<version>.tar.gz
#
# 1. checks the archive against <archive>.sha256 next to it (or SHA256=<hex>; NO_VERIFY=1 skips);
# 2. docker load -i <archive> (gzip is read directly);
# 3. checks that $IMAGE (default resense:latest) exists;
# 4. with --network none: the resense package imports (with its C++ kernels) and the ROS 2
#    package resense_ros resolves its executables.
# Needs Docker, not ROS on the host. Exits 2 on a bad argument, 3 without Docker, 4 on a checksum
# mismatch, 5 when the loaded image fails its check.
set -euo pipefail
IMAGE="${IMAGE:-resense:latest}"
if [ $# -ne 1 ]; then
  sed -n '2,13p' "$0" >&2
  exit 2
fi
ARCHIVE="$1"
if [ ! -f "$ARCHIVE" ]; then
  echo "ERROR: archive $ARCHIVE not found" >&2
  exit 2
fi
ARCHIVE_DIR="$(cd "$(dirname "$ARCHIVE")" && pwd)"
ARCHIVE_NAME="$(basename "$ARCHIVE")"
. "$(dirname "${BASH_SOURCE[0]}")/require_docker.sh"

if command -v sha256sum >/dev/null 2>&1; then SHA=(sha256sum); else SHA=(shasum -a 256); fi
if [ "${NO_VERIFY:-0}" = "1" ]; then
  echo "== NO_VERIFY=1: checksum not checked"
else
  if [ -n "${SHA256:-}" ]; then
    EXPECTED="$SHA256"
  elif [ -f "$ARCHIVE_DIR/$ARCHIVE_NAME.sha256" ]; then
    EXPECTED="$(cut -d' ' -f1 "$ARCHIVE_DIR/$ARCHIVE_NAME.sha256")"
  else
    echo "ERROR: no $ARCHIVE_NAME.sha256 next to the archive; copy it along, or pass SHA256=<hex>" >&2
    echo "       (NO_VERIFY=1 loads without the check)" >&2
    exit 2
  fi
  echo "== checking the sha256 of $ARCHIVE_NAME ($(wc -c < "$ARCHIVE_DIR/$ARCHIVE_NAME" | tr -d ' ') bytes)"
  ACTUAL="$(cd "$ARCHIVE_DIR" && "${SHA[@]}" "$ARCHIVE_NAME" | cut -d' ' -f1)"
  if [ "$ACTUAL" != "$EXPECTED" ]; then
    echo "ERROR: checksum mismatch: the archive is damaged or incomplete (copy it again)" >&2
    echo "       expected $EXPECTED" >&2
    echo "       actual   $ACTUAL" >&2
    exit 4
  fi
  echo "   OK $ACTUAL"
fi

require_docker_daemon
echo "== docker load -i $ARCHIVE_NAME"
docker load -i "$ARCHIVE_DIR/$ARCHIVE_NAME"
if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "ERROR: the archive did not provide $IMAGE; loaded tags:" >&2
  docker images --format '{{.Repository}}:{{.Tag}}' | grep -E '^(resense|ros):' >&2 || true
  exit 5
fi
label() {
  docker image inspect -f "{{with .Config.Labels}}{{index . \"$1\"}}{{end}}" "$IMAGE" 2>/dev/null || true
}
echo "   $IMAGE: $(docker image inspect -f '{{.Id}}' "$IMAGE"), version label '$(label org.opencontainers.image.version)'," \
     "commit label '$(label org.opencontainers.image.revision)' (empty when exported with SKIP_BUILD=1)"

echo "== the image with no network (--network none): package import and ROS 2 executables"
# -w /: import the installed package, not the source copy in the image's working directory
if ! docker run --rm --network none -w / "$IMAGE" bash -lc \
    "python3 -c 'import resense, resense._native as n; print(\"resense\", resense.__version__, n.status())' && ros2 pkg executables resense_ros"; then
  echo "ERROR: $IMAGE does not pass its offline check (above)" >&2
  exit 5
fi
echo
echo "PASS: $IMAGE loaded from $ARCHIVE_NAME and runs without network. Next:"
echo "   docker run --rm -it --net=host --ipc=host resense      # the node; then ros2 bag play <bag> --delay 3"
