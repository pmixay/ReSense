#!/usr/bin/env bash
# Manual fallback of .github/workflows/release.yml, for a person with Docker and internet: the
# release archive of a tag, proven to load, with SHA256SUMS and the release notes; then the gh
# command that publishes it (PUBLISH=1 runs it).
#
#   scripts/release.sh <tag>              # e.g. v1.0.0-rc1, in a clean checkout of the tag
#   DRY_RUN=1 scripts/release.sh <tag>    # the checks, then print every step; runs and writes nothing
#   PUBLISH=1 scripts/release.sh <tag>    # also create / update the GitHub release (gh, logged in)
#
#   1. the tag is v<version>[-suffix] of the version in pyproject.toml and the three other
#      declarations (scripts/release_meta.py); HEAD is the tag's commit; no tracked file changed;
#   2. VERSION=<tag> scripts/export_image.sh: the runtime image, --no-cache, from `git archive HEAD`
#      -> $OUT_DIR/resense-image-<tag>.tar.gz + .sha256 (gzip -$GZIP_LEVEL, default 6);
#   3. docker rmi resense:<tag> resense:latest, then scripts/load_image.sh on the archive (sha256,
#      docker load, a --network none run): the archive alone gives the image back, same layers;
#   4. SMOKE=1: two synthetic bags (scripts/make_smoke_bag.py, which needs open3d and rosbags on the
#      host: pip install -e ".[dev]") through the loaded image, in the jury's --net=host form with a
#      stock Fast DDS player (scripts/console_test.sh) and on an --internal network
#      (scripts/internal_net_test.sh);
#   5. $OUT_DIR/release-notes-<tag>.md (scripts/release_meta.py notes);
#   6. scripts/publish_release.sh <tag> $OUT_DIR: SHA256SUMS, then the release created (a
#      pre-release for a tag with a suffix) or updated with its assets replaced; printed unless
#      PUBLISH=1. Afterwards scripts/verify_release.sh <tag> downloads the archive and checks it.
#
# Environment: OUT_DIR=dist (relative to the repository root, as in export_image.sh), GZIP_LEVEL=6,
# REPO=pmixay/ReSense, DRY_RUN=1, PUBLISH=1, SMOKE=1, REUSE_ARCHIVE=1 (keep an existing
# $OUT_DIR/resense-image-<tag>.tar.gz made from this commit: steps 3-6 only).
# Exits 2 on a bad tag, argument or checkout, 3 without Docker, else the failing step's code.
set -euo pipefail
cd "$(dirname "$0")/.."
usage() { awk 'NR > 1 && /^#/ { print; next } NR > 1 { exit }' "$0" >&2; }   # the header comment
if [ $# -ne 1 ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
  usage
  exit 2
fi
TAG="$1"
OUT_DIR="${OUT_DIR:-dist}"
GZIP_LEVEL="${GZIP_LEVEL:-6}"
REPO="${REPO:-pmixay/ReSense}"
DRY_RUN="${DRY_RUN:-0}"
PUBLISH="${PUBLISH:-0}"
SMOKE="${SMOKE:-0}"
REUSE_ARCHIVE="${REUSE_ARCHIVE:-0}"
PY="$(command -v python3 || command -v python || true)"
if [ -z "$PY" ]; then echo "ERROR: python3 not found" >&2; exit 2; fi

# ---- 1. tag, version, checkout
META="$("$PY" scripts/release_meta.py check-tag "$TAG")" || exit 2
VERSION="$(sed -n 's/^version=//p' <<<"$META")"
PRERELEASE="$(sed -n 's/^prerelease=//p' <<<"$META")"
problem() {
  if [ "$DRY_RUN" = "1" ]; then echo "WARNING (dry run; a real run stops here): $*" >&2
  else echo "ERROR: $*" >&2; exit 2; fi
}
COMMIT=unknown
if ! git rev-parse --git-dir >/dev/null 2>&1; then
  problem "not a git checkout: the image is built from 'git archive HEAD' of the tag (git clone --branch $TAG ...)"
else
  HEAD_C="$(git rev-parse HEAD)"
  TAG_C="$(git rev-parse -q --verify "refs/tags/$TAG^{commit}" || true)"
  COMMIT="$HEAD_C"
  if [ -z "$TAG_C" ]; then
    problem "no tag $TAG here: git tag -a $TAG -m '...' && git push origin $TAG (or git fetch --tags)"
  elif [ "$TAG_C" != "$HEAD_C" ]; then
    problem "HEAD is $HEAD_C but $TAG is $TAG_C: git checkout $TAG (or a clean clone: git clone --branch $TAG ...)"
  fi
  if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
    problem "uncommitted changes to tracked files (they would not be in the image, which is built from HEAD)"
  fi
fi
ARCHIVE="$OUT_DIR/resense-image-$TAG.tar.gz"
NOTES="$OUT_DIR/release-notes-$TAG.md"
echo "== release $TAG: version $VERSION, $([ "$PRERELEASE" = true ] && echo pre-release || echo full release), commit $COMMIT"

run() {
  echo "+ $*"
  [ "$DRY_RUN" = "1" ] || "$@"
}

if [ "$DRY_RUN" = "1" ]; then
  echo "== DRY_RUN=1: the steps (nothing is run or written)"
  if [ "$REUSE_ARCHIVE" = "1" ]; then echo "+ (REUSE_ARCHIVE=1) use $ARCHIVE"
  else echo "+ VERSION=$TAG OUT_DIR=$OUT_DIR GZIP_LEVEL=$GZIP_LEVEL scripts/export_image.sh"; fi
  echo "+ docker rmi resense:$TAG resense:latest"
  echo "+ scripts/load_image.sh $ARCHIVE      # sha256, docker load, --network none check; same layers as built"
  if [ "$SMOKE" = "1" ]; then
    echo "+ $PY scripts/make_smoke_bag.py <tmp>/smoke_bag; ... <tmp>/smoke_bag2 --topic /sensing/lidar/hesai128/pointcloud --frame-id lidar_livox --distance 45"
    echo "+ IMAGE=resense:$TAG PLAYER_DDS=stock scripts/console_test.sh <tmp>/smoke_bag <tmp>/smoke_bag2"
    echo "+ IMAGE=resense:$TAG scripts/internal_net_test.sh <tmp>/smoke_bag <tmp>/smoke_bag2"
  fi
  echo "+ $PY scripts/release_meta.py notes --tag $TAG --commit $COMMIT --sha256 <sum> --bytes <size> --repo $REPO ... > $NOTES"
  echo "+ REPO=$REPO scripts/publish_release.sh $TAG $OUT_DIR      # $([ "$PUBLISH" = 1 ] && echo run || echo printed only, PUBLISH=1 runs it); it runs:"
  echo "    SHA256SUMS; gh release create $TAG --verify-tag --title \"ReSense $TAG\" --notes-file $NOTES$([ "$PRERELEASE" = true ] && echo ' --prerelease') <archive> <archive>.sha256 SHA256SUMS"
  echo "    or, when the release exists: gh release edit $TAG ... and gh release upload $TAG --clobber <the three assets>"
  echo "+ EXPECT_SHA256=<sum> scripts/verify_release.sh $TAG      # after publishing: download and check"
  exit 0
fi

. scripts/require_docker.sh
require_docker_daemon || exit 3

# ---- 2. build and export
if [ "$REUSE_ARCHIVE" = "1" ]; then
  if [ ! -f "$ARCHIVE" ] || [ ! -f "$ARCHIVE.sha256" ]; then
    echo "ERROR: REUSE_ARCHIVE=1 but $ARCHIVE or its .sha256 is missing" >&2
    exit 2
  fi
  echo "== REUSE_ARCHIVE=1: $ARCHIVE"
else
  run env VERSION="$TAG" OUT_DIR="$OUT_DIR" GZIP_LEVEL="$GZIP_LEVEL" scripts/export_image.sh
fi
LAYERS=""
if docker image inspect "resense:$TAG" >/dev/null 2>&1; then
  LAYERS="$(docker image inspect -f '{{json .RootFS.Layers}}' "resense:$TAG")"
  IMAGE_ID="$(docker image inspect -f '{{.Id}}' "resense:$TAG")"
  if [ -n "$(docker ps -aq --filter "ancestor=$IMAGE_ID")" ]; then
    echo "ERROR: containers of resense:$TAG exist (docker ps -a); remove them, the check needs the image gone" >&2
    exit 2
  fi
fi

# ---- 3. the archive alone gives the image back
RMI=()
for t in "resense:$TAG" resense:latest; do
  if docker image inspect "$t" >/dev/null 2>&1; then RMI+=("$t"); fi
done
if [ ${#RMI[@]} -gt 0 ]; then run docker rmi "${RMI[@]}"; fi
if docker image inspect "resense:$TAG" >/dev/null 2>&1; then
  echo "ERROR: resense:$TAG still present after docker rmi" >&2
  exit 1
fi
run scripts/load_image.sh "$ARCHIVE"
if [ -n "$LAYERS" ] && [ "$(docker image inspect -f '{{json .RootFS.Layers}}' "resense:$TAG")" != "$LAYERS" ]; then
  echo "ERROR: the loaded resense:$TAG has other layers than the image that was built" >&2
  exit 1
fi
LABEL_REV="$(docker image inspect -f '{{with .Config.Labels}}{{index . "org.opencontainers.image.revision"}}{{end}}' "resense:$TAG")"
if [ "$LABEL_REV" != "$COMMIT" ]; then
  echo "ERROR: the archive's image was built from '$LABEL_REV', not from $TAG ($COMMIT)" >&2
  exit 2
fi

# ---- 4. optional: the smoke bags through the loaded image
if [ "$SMOKE" = "1" ]; then
  BAGS="$(mktemp -d)"
  trap 'rm -rf "$BAGS"' EXIT
  chmod 755 "$BAGS"
  run "$PY" scripts/make_smoke_bag.py "$BAGS/smoke_bag"
  run "$PY" scripts/make_smoke_bag.py "$BAGS/smoke_bag2" --topic /sensing/lidar/hesai128/pointcloud \
    --frame-id lidar_livox --distance 45
  chmod -R a+rX "$BAGS"
  run env IMAGE="resense:$TAG" PLAYER_USER=1000:1000 PLAYER_DDS=stock PLAYER_ENV="-e RMW_IMPLEMENTATION=rmw_fastrtps_cpp" \
    OUT=out/release_console scripts/console_test.sh "$BAGS/smoke_bag" "$BAGS/smoke_bag2"
  run env IMAGE="resense:$TAG" OUT=out/release_internal scripts/internal_net_test.sh "$BAGS/smoke_bag" "$BAGS/smoke_bag2"
fi

# ---- 5. notes
SUM="$(cut -d' ' -f1 "$ARCHIVE.sha256")"
BYTES="$(wc -c < "$ARCHIVE" | tr -d ' ')"
BASE_IMAGE="$(sed -n 's/^FROM[[:space:]]\{1,\}\([^[:space:]]\{1,\}\).*/\1/p' docker/Dockerfile | head -n 1)"
BASE_DIGEST="$(docker image inspect -f '{{index .RepoDigests 0}}' "$BASE_IMAGE" 2>/dev/null || true)"
"$PY" scripts/release_meta.py notes --tag "$TAG" --commit "$COMMIT" --sha256 "$SUM" --bytes "$BYTES" \
  --repo "$REPO" --image-id "$(docker image inspect -f '{{.Id}}' "resense:$TAG")" --base-digest "$BASE_DIGEST" \
  --docker "$(docker version -f '{{.Server.Version}}' 2>/dev/null || echo unknown)" > "$NOTES"
echo "== notes: $NOTES"

# ---- 6. publish (or print)
if [ "$PUBLISH" = "1" ]; then
  REPO="$REPO" scripts/publish_release.sh "$TAG" "$OUT_DIR"
  echo
  echo "Check the published archive: EXPECT_SHA256=$SUM scripts/verify_release.sh $TAG"
else
  echo
  echo "Ready: $ARCHIVE ($BYTES bytes), sha256 $SUM"
  echo "Publish (gh CLI, logged in; the tag must be on GitHub; a re-run replaces the assets):"
  echo "   REPO=$REPO scripts/publish_release.sh $TAG $OUT_DIR"
  echo "Then check what was published:"
  echo "   EXPECT_SHA256=$SUM scripts/verify_release.sh $TAG"
fi
