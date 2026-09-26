#!/usr/bin/env bash
# Load the image archive made by scripts/export_image.sh and prove that the image runs with no
# network at all (the test stand has no internet, docs/organizers/answers.md §7).
#
#   scripts/load_image.sh dist/resense-image-<version>.tar.gz
#
# 1. checks the archive against <archive>.sha256 next to it, or SHA256=<sum> (any case, as
#    Get-FileHash / certutil print it; a '<sum>  <file>' line too); NO_VERIFY=1 skips;
# 2. docker load -i <archive> (gzip is read directly);
# 3. checks that $IMAGE (default resense:latest) exists;
# 4. with --network none: the resense package imports (with its C++ kernels) and the ROS 2
#    package resense_ros resolves its executables.
# Needs Docker, not ROS on the host. Exits 2 on a bad argument, 3 without Docker, 4 on a checksum
# mismatch, 5 when the loaded image fails its check.
set -euo pipefail
IMAGE="${IMAGE:-resense:latest}"
if [ $# -ne 1 ]; then
  sed -n '2,14p' "$0" >&2
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

# sha256_in <text> <archive name>: the sha256 that <text> gives, as 64 lowercase hex digits, or
# nothing. Accepts a bare sum in any case (Windows Get-FileHash and certutil print upper case)
# with spaces, tabs, CR or newlines around or inside it (certutil's "a1 b2 c3 ..."), the
# sha256sum line "<sum>  <name>" / "<sum> *<name>" of a .sha256 file (of several lines, the one
# naming the archive), and the BSD "SHA256 (<name>) = <sum>" line. bash 3.2 compatible (macOS).
sha256_in() {
  local text name squeezed line tok found first="" f
  local -a toks
  text="$(printf '%s\n' "$1" | tr -d '\r' | tr '[:upper:]' '[:lower:]')"
  name="$(printf '%s' "$2" | tr '[:upper:]' '[:lower:]')"
  squeezed="${text//[[:space:]]/}"
  if [[ "$squeezed" =~ ^[0-9a-f]{64}$ ]]; then
    printf '%s' "$squeezed"
    return
  fi
  while IFS= read -r line; do
    found=""
    squeezed="${line//[[:space:]]/}"
    read -r -a toks <<< "$line" || true
    if [[ "$squeezed" =~ ^[0-9a-f]{64}$ ]]; then
      found="$squeezed"
    else
      for tok in ${toks[@]+"${toks[@]}"}; do
        tok="${tok#\\}"                    # sha256sum escapes a line whose name has a backslash
        if [[ "$tok" =~ ^[0-9a-f]{64}$ ]]; then found="$tok"; break; fi
      done
    fi
    [ -n "$found" ] || continue
    [ -n "$first" ] || first="$found"
    for tok in ${toks[@]+"${toks[@]}"}; do
      f="${tok#\*}"; f="${f#(}"; f="${f%)}"
      if [ "$f" = "$name" ]; then printf '%s' "$found"; return; fi
    done
  done <<< "$text"
  printf '%s' "$first"
}

if command -v sha256sum >/dev/null 2>&1; then SHA=(sha256sum); else SHA=(shasum -a 256); fi
if [ "${NO_VERIFY:-0}" = "1" ]; then
  echo "== NO_VERIFY=1: checksum not checked"
else
  if [ -n "${SHA256:-}" ]; then
    SOURCE="SHA256"
    EXPECTED="$(sha256_in "$SHA256" "$ARCHIVE_NAME")"
  elif [ -f "$ARCHIVE_DIR/$ARCHIVE_NAME.sha256" ]; then
    SOURCE="$ARCHIVE_NAME.sha256"
    EXPECTED="$(sha256_in "$(cat "$ARCHIVE_DIR/$ARCHIVE_NAME.sha256")" "$ARCHIVE_NAME")"
  else
    echo "ERROR: no $ARCHIVE_NAME.sha256 next to the archive; copy it along, or pass SHA256=<hex>" >&2
    echo "       (NO_VERIFY=1 loads without the check)" >&2
    exit 2
  fi
  if [ -z "$EXPECTED" ]; then
    echo "ERROR: $SOURCE holds no sha256 (64 hex digits, any case; '<sum>  <file>' lines are fine)" >&2
    exit 2
  fi
  echo "== checking the sha256 of $ARCHIVE_NAME ($(wc -c < "$ARCHIVE_DIR/$ARCHIVE_NAME" | tr -d ' ') bytes)"
  ACTUAL="$(cd "$ARCHIVE_DIR" && "${SHA[@]}" "$ARCHIVE_NAME")"
  ACTUAL="$(sha256_in "$ACTUAL" "$ARCHIVE_NAME")"
  if [ "$ACTUAL" != "$EXPECTED" ]; then
    echo "ERROR: checksum mismatch: the archive is damaged or incomplete (copy it again)" >&2
    echo "       expected $EXPECTED ($SOURCE)" >&2
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
