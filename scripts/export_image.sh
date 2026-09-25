#!/usr/bin/env bash
# Export the runtime image as one gzip archive for the test stand, which has no internet
# (organizers, 25.09, docs/organizers/answers.md §7): `docker build` cannot run there (base image
# from Docker Hub, apt, PyPI), so the jury gets the image itself and runs `docker load`.
#
#   scripts/export_image.sh                     # build from HEAD, tag, save, checksum
#   VERSION=v1.0-rc1 scripts/export_image.sh    # tag / file name (default: pyproject.toml version)
#   SKIP_BUILD=1 SOURCE_IMAGE=resense:ci scripts/export_image.sh   # save an existing image
#
# Writes $OUT_DIR/resense-image-<version>.tar.gz (tags resense:<version> and resense:latest) and
# its .sha256; `docker load -i` reads the .tar.gz directly on any Docker (scripts/load_image.sh
# checks it). gzip, not zstd: zstd -19 is typically ~10-20 % smaller, but not every Docker's
# `docker load` reads it, and pigz (used when installed) makes gzip fast.
#
# The build (no SKIP_BUILD) also makes an offline `docker build` possible after `docker load`
# (best effort, docs/ARCHITECTURE.md "Deployment without internet"): the base image is pulled
# first so that BuildKit resolves it locally, exactly as it will from the archive on the stand;
# the image carries its own layer cache (BUILDKIT_INLINE_CACHE=1); the base image's tag is saved
# into the same archive (its layers are the image's lowest layers, so it costs a few KB); the
# build context is `git archive HEAD` with normalised permissions (they are part of Docker's cache
# key), so the archive matches a clean checkout of the same commit.
#
# Environment:
#   VERSION        image tag and file name suffix (default: the version in pyproject.toml)
#   OUT_DIR=dist   where the archive and its .sha256 go (dist/ is ignored by git and Docker)
#   SKIP_BUILD=1   do not build; tag and save SOURCE_IMAGE (default resense:latest)
#   WITH_BASE      1 = also save the base image's tag (default 1 when building, 0 with SKIP_BUILD:
#                  an image built elsewhere has no matching inline cache)
#   PULL_BASE=0    do not `docker pull` the base image first (it must then exist locally)
#   NO_CACHE=0     allow the local build cache (default: a clean --no-cache build, as dry_run.sh)
#   WITH_TOOLS=1   the CI / test image instead of the runtime one (the jury gets the runtime one)
#   GZIP_LEVEL=6   1 (fast, CI) .. 9 (smallest, a few % smaller)
#   ALLOW_DIRTY=1  build although the working tree has uncommitted changes (they are NOT in the
#                  image either way: the context is `git archive HEAD`)
set -euo pipefail
cd "$(dirname "$0")/.."
. "$(dirname "${BASH_SOURCE[0]}")/require_docker.sh"

SKIP_BUILD="${SKIP_BUILD:-0}"
OUT_DIR="${OUT_DIR:-dist}"
GZIP_LEVEL="${GZIP_LEVEL:-6}"
WITH_TOOLS="${WITH_TOOLS:-0}"
if [ "$SKIP_BUILD" = "1" ]; then WITH_BASE="${WITH_BASE:-0}"; else WITH_BASE="${WITH_BASE:-1}"; fi
BASE_IMAGE="$(sed -n 's/^FROM[[:space:]]\{1,\}\([^[:space:]]\{1,\}\).*/\1/p' docker/Dockerfile | head -n 1)"
VERSION="${VERSION:-$(sed -n 's/^version[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' pyproject.toml | head -n 1)}"

if ! printf '%s' "$VERSION" | grep -Eq '^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$'; then
  echo "ERROR: VERSION '$VERSION' is not a valid Docker tag ([A-Za-z0-9_.-], at most 128 characters)" >&2
  exit 2
fi
if [ -z "$BASE_IMAGE" ]; then
  echo "ERROR: no FROM line found in docker/Dockerfile" >&2
  exit 2
fi
case "$GZIP_LEVEL" in [1-9]) ;; *) echo "ERROR: GZIP_LEVEL must be 1..9" >&2; exit 2 ;; esac
COMMIT="$(git rev-parse HEAD 2>/dev/null || echo unknown)"
if [ "$SKIP_BUILD" != "1" ]; then
  if [ "$COMMIT" = "unknown" ]; then
    echo "ERROR: not a git checkout; the build context is 'git archive HEAD' (or use SKIP_BUILD=1)" >&2
    exit 2
  fi
  if [ -n "$(git status --porcelain --untracked-files=no)" ] && [ "${ALLOW_DIRTY:-0}" != "1" ]; then
    echo "ERROR: uncommitted changes to tracked files; the image is built from HEAD ($COMMIT) and" >&2
    echo "       would not contain them. Commit (or stash) them, or set ALLOW_DIRTY=1." >&2
    git status --short --untracked-files=no >&2
    exit 2
  fi
fi
require_docker_daemon

IMAGE="resense:$VERSION"
ARCHIVE="$OUT_DIR/resense-image-$VERSION.tar.gz"
mkdir -p "$OUT_DIR"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"; rm -f "$ARCHIVE.part"' EXIT
echo "== Docker $(docker version -f '{{.Server.Version}}' 2>/dev/null), storage driver $(docker info -f '{{.Driver}}' 2>/dev/null)"

if [ "$SKIP_BUILD" = "1" ]; then
  SOURCE_IMAGE="${SOURCE_IMAGE:-resense:latest}"
  if ! docker image inspect "$SOURCE_IMAGE" >/dev/null 2>&1; then
    echo "ERROR: SKIP_BUILD=1 but image $SOURCE_IMAGE does not exist (build it: scripts/build.sh)" >&2
    exit 3
  fi
  echo "== SKIP_BUILD=1: exporting the existing $SOURCE_IMAGE as $IMAGE"
  docker tag "$SOURCE_IMAGE" "$IMAGE"
else
  if [ "${PULL_BASE:-1}" = "1" ]; then
    echo "== pulling the base image $BASE_IMAGE (so that the build resolves it locally)"
    docker pull "$BASE_IMAGE"
  elif ! docker image inspect "$BASE_IMAGE" >/dev/null 2>&1; then
    echo "ERROR: PULL_BASE=0 but the base image $BASE_IMAGE is not present locally" >&2
    exit 3
  fi
  echo "== build context: git archive of $COMMIT, permissions normalised (files 644 / 755)"
  git archive --format=tar HEAD | tar -x -C "$WORK" -f -
  chmod -R u+rwX,go+rX,go-w "$WORK"
  args=(-t "$IMAGE" -f docker/Dockerfile
        --build-arg "WITH_TOOLS=$WITH_TOOLS" --build-arg BUILDKIT_INLINE_CACHE=1
        --label "org.opencontainers.image.title=ReSense"
        --label "org.opencontainers.image.version=$VERSION"
        --label "org.opencontainers.image.revision=$COMMIT"
        --label "org.opencontainers.image.source=https://github.com/pmixay/ReSense")
  if [ "${NO_CACHE:-1}" = "1" ]; then args+=(--no-cache); fi
  echo "== building $IMAGE (WITH_TOOLS=$WITH_TOOLS, inline layer cache)"
  (cd "$WORK" && docker build "${args[@]}" .)
  # BuildKit marks its history entries; the legacy builder ignores BUILDKIT_INLINE_CACHE
  HISTORY="$(docker history --no-trunc --format '{{.CreatedBy}}' "$IMAGE")"
  if ! grep -q 'buildkit' <<<"$HISTORY"; then
    echo "WARNING: $IMAGE was built by the legacy builder (no BuildKit / buildx here), so it carries" >&2
    echo "         no layer cache: 'docker load' works, an offline 'docker build --cache-from' will not." >&2
  fi
fi
docker tag "$IMAGE" resense:latest

TAGS=("$IMAGE" resense:latest)
if [ "$WITH_BASE" = "1" ]; then
  if docker image inspect "$BASE_IMAGE" >/dev/null 2>&1; then
    TAGS+=("$BASE_IMAGE")
  else
    echo "WARNING: base image $BASE_IMAGE not present locally; the archive holds only the ReSense" >&2
    echo "         tags (docker load works; an offline docker build would not find the base)" >&2
  fi
fi
if command -v pigz >/dev/null 2>&1; then GZ=(pigz "-$GZIP_LEVEL"); else GZ=(gzip "-$GZIP_LEVEL"); fi
echo "== docker save ${TAGS[*]} | ${GZ[*]} > $ARCHIVE"
docker save "${TAGS[@]}" | "${GZ[@]}" > "$ARCHIVE.part"
mv -f "$ARCHIVE.part" "$ARCHIVE"
if command -v sha256sum >/dev/null 2>&1; then SHA=(sha256sum); else SHA=(shasum -a 256); fi
(cd "$OUT_DIR" && "${SHA[@]}" "$(basename "$ARCHIVE")" > "$(basename "$ARCHIVE").sha256")

IMAGE_BYTES="$(docker image inspect -f '{{.Size}}' "$IMAGE")"
ARCHIVE_BYTES="$(wc -c < "$ARCHIVE" | tr -d ' ')"
echo
echo "== $ARCHIVE"
echo "   archive: $ARCHIVE_BYTES bytes ($(awk -v b="$ARCHIVE_BYTES" 'BEGIN { printf "%.2f GiB", b / 1073741824 }'))"
echo "   image:   $IMAGE_BYTES bytes uncompressed ($(awk -v b="$IMAGE_BYTES" 'BEGIN { printf "%.2f GiB", b / 1073741824 }'))"
echo "   sha256:  $(cut -d' ' -f1 "$ARCHIVE.sha256")"
echo "   tags:    ${TAGS[*]}"
echo "   commit:  $COMMIT"
echo
echo "On the machine without internet:"
echo "   scripts/load_image.sh $(basename "$ARCHIVE")      # or: docker load -i $(basename "$ARCHIVE")"
echo "   docker run --rm -it --net=host --ipc=host resense"
