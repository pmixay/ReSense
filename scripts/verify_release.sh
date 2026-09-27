#!/usr/bin/env bash
# Download the image archive of a GitHub release and check its sha256 (no Docker needed).
#
#   scripts/verify_release.sh <tag> [<dir>]      # e.g. scripts/verify_release.sh v1.0.0-rc1
#   EXPECT_SHA256=<hex> scripts/verify_release.sh v1.0.0     # also against the sum in the cover message
#   NO_DOWNLOAD=1 scripts/verify_release.sh v1.0.0 /media/usb   # check a copy already in <dir>
#
# Fetches resense-image-<tag>.tar.gz, its .sha256 and SHA256SUMS from the release <tag> (assets of
# .github/workflows/release.yml or scripts/release.sh) into <dir> (default dist/), then checks that
# the .sha256 names the archive, that SHA256SUMS (when the release has one) gives the same sum, that
# EXPECT_SHA256 (when set) is that sum, and that the downloaded archive has it. Next step on the
# machine without internet: scripts/load_image.sh <dir>/resense-image-<tag>.tar.gz.
#
# Environment:
#   REPO=pmixay/ReSense      GitHub owner/name (public repository: no token needed)
#   BASE_URL                 default https://github.com/$REPO/releases/download; a mirror, or file://
#   EXPECT_SHA256            the sum the archive must have (e.g. from the upload's cover message)
#   NO_DOWNLOAD=1            do not download; verify the files already in <dir>
#   DOWNLOADER=curl|python   default curl, python3 (urllib) where curl is not installed
# Exits 0 when every check passes, 2 on a bad argument, 4 on a checksum mismatch or a malformed
# checksum file, 6 when a download fails.
set -euo pipefail
usage() { awk 'NR > 1 && /^#/ { print; next } NR > 1 { exit }' "$0" >&2; }   # the header comment
if [ $# -lt 1 ] || [ $# -gt 2 ] || [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 2
fi
TAG="$1"
DIR="${2:-dist}"
REPO="${REPO:-pmixay/ReSense}"
BASE_URL="${BASE_URL:-https://github.com/$REPO/releases/download}"
EXPECT_SHA256="${EXPECT_SHA256:-}"
NO_DOWNLOAD="${NO_DOWNLOAD:-0}"
# the tag names a file and a Docker tag: the characters export_image.sh accepts ([[ =~ ]] tests the
# whole string; grep would test line by line)
RE_TAG='^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$'
RE_REPO='^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$'
RE_SUM='^[0-9a-f]{64}$'
if ! [[ "$TAG" =~ $RE_TAG ]]; then
  echo "ERROR: '$TAG' is not a release tag ([A-Za-z0-9_.-], e.g. v1.0.0-rc1)" >&2
  exit 2
fi
if ! [[ "$REPO" =~ $RE_REPO ]]; then
  echo "ERROR: REPO '$REPO' is not owner/name" >&2
  exit 2
fi
EXPECT_SHA256="$(printf '%s' "$EXPECT_SHA256" | tr 'A-F' 'a-f')"
if [ -n "$EXPECT_SHA256" ] && ! [[ "$EXPECT_SHA256" =~ $RE_SUM ]]; then
  echo "ERROR: EXPECT_SHA256 must be 64 hex digits" >&2
  exit 2
fi
if [ -z "${DOWNLOADER:-}" ]; then
  if command -v curl >/dev/null 2>&1; then DOWNLOADER=curl; else DOWNLOADER=python; fi
fi
case "$DOWNLOADER" in
  curl|python) ;;
  *) echo "ERROR: DOWNLOADER must be curl or python" >&2; exit 2 ;;
esac
if command -v sha256sum >/dev/null 2>&1; then SHA=(sha256sum); else SHA=(shasum -a 256); fi

ARCHIVE="resense-image-$TAG.tar.gz"
mkdir -p "$DIR"
DIR="$(cd "$DIR" && pwd)"

# fetch <asset>: $BASE_URL/$TAG/<asset> -> $DIR/<asset> (through a .part file); 1 on any failure
fetch() {
  local url="$BASE_URL/$TAG/$1" out="$DIR/$1"
  rm -f "$out.part"
  echo "== $url"
  if [ "$DOWNLOADER" = curl ]; then
    curl -fL --retry 3 --retry-delay 2 --connect-timeout 20 -sS -o "$out.part" "$url" || { rm -f "$out.part"; return 1; }
  else
    python3 - "$url" "$out.part" <<'PY' || { rm -f "$out.part"; return 1; }
import shutil, sys, urllib.request
try:
    with urllib.request.urlopen(sys.argv[1], timeout=60) as r, open(sys.argv[2], "wb") as f:
        shutil.copyfileobj(r, f, 1 << 20)
except Exception as e:  # HTTPError, URLError, OSError
    print(f"download failed: {e}", file=sys.stderr)
    sys.exit(1)
PY
  fi
  mv -f "$out.part" "$out"
}

if [ "$NO_DOWNLOAD" = "1" ]; then
  echo "== NO_DOWNLOAD=1: verifying the files in $DIR"
  for f in "$ARCHIVE" "$ARCHIVE.sha256"; do
    if [ ! -f "$DIR/$f" ]; then echo "ERROR: $DIR/$f not found" >&2; exit 2; fi
  done
else
  for f in "$ARCHIVE.sha256" "$ARCHIVE"; do
    if ! fetch "$f"; then
      echo "ERROR: could not download $f of release $TAG ($BASE_URL/$TAG/$f)" >&2
      exit 6
    fi
  done
  rm -f "$DIR/SHA256SUMS"
  fetch SHA256SUMS || echo "   (no SHA256SUMS in release $TAG: checked against the .sha256 alone)"
fi

# the .sha256 of export_image.sh: "<64 hex>  <archive name>" (sha256sum's format; "*<name>" too)
read -r SUM NAME _ < "$DIR/$ARCHIVE.sha256" || true
SUM="$(printf '%s' "${SUM:-}" | tr 'A-F' 'a-f')"
NAME="${NAME#\*}"
if ! [[ "$SUM" =~ $RE_SUM ]]; then
  echo "ERROR: $ARCHIVE.sha256 does not start with a sha256 (64 hex digits)" >&2
  exit 4
fi
if [ "$NAME" != "$ARCHIVE" ]; then
  echo "ERROR: $ARCHIVE.sha256 is the sum of '$NAME', not of $ARCHIVE" >&2
  exit 4
fi
if [ -f "$DIR/SHA256SUMS" ]; then
  LISTED="$(awk -v n="$ARCHIVE" '{ f = $2; sub(/^\*/, "", f); if (f == n) { print tolower($1); exit } }' "$DIR/SHA256SUMS")"
  if [ -z "$LISTED" ]; then
    echo "ERROR: SHA256SUMS has no line for $ARCHIVE" >&2
    exit 4
  fi
  if [ "$LISTED" != "$SUM" ]; then
    echo "ERROR: SHA256SUMS ($LISTED) and $ARCHIVE.sha256 ($SUM) disagree" >&2
    exit 4
  fi
fi
if [ -n "$EXPECT_SHA256" ] && [ "$EXPECT_SHA256" != "$SUM" ]; then
  echo "ERROR: the release's sum is not EXPECT_SHA256" >&2
  echo "       release  $SUM" >&2
  echo "       expected $EXPECT_SHA256" >&2
  exit 4
fi
BYTES="$(wc -c < "$DIR/$ARCHIVE" | tr -d ' ')"
echo "== sha256 of $ARCHIVE ($BYTES bytes)"
ACTUAL="$(cd "$DIR" && "${SHA[@]}" "$ARCHIVE" | cut -d' ' -f1)"
if [ "$ACTUAL" != "$SUM" ]; then
  echo "ERROR: checksum mismatch: the archive is damaged or incomplete (download it again)" >&2
  echo "       expected $SUM" >&2
  echo "       actual   $ACTUAL" >&2
  exit 4
fi
echo "   OK $ACTUAL"
echo
echo "PASS: $DIR/$ARCHIVE is release $TAG's archive. Next, on the machine without internet:"
echo "   scripts/load_image.sh $DIR/$ARCHIVE      # or: docker load -i $ARCHIVE"
