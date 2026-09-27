#!/usr/bin/env bash
# Create or update the GitHub release of a tag with the image archive (gh CLI). Used by
# .github/workflows/release.yml and by scripts/release.sh (PUBLISH=1); a person can run it too.
#
#   scripts/publish_release.sh <tag> [<dir>]         # <dir> default dist
#   DRY_RUN=1 scripts/publish_release.sh <tag> [<dir>]   # the checks, then print the gh commands
#
# <dir> holds resense-image-<tag>.tar.gz and its .sha256 (scripts/export_image.sh) and the notes
# release-notes-<tag>.md (scripts/release_meta.py notes). The archive's sum is computed again and
# must be the .sha256's; <dir>/SHA256SUMS is written from it. Then, with the tag already on GitHub:
#   no release yet:  gh release create <tag> --verify-tag --title "ReSense <tag>" --notes-file ...
#                    [--prerelease] <archive> <archive>.sha256 SHA256SUMS
#   a release:       gh release edit <tag> (title, notes, pre-release flag), then
#                    gh release upload <tag> --clobber <the three assets>   (a re-run replaces them)
# and the release's assets are listed and compared with the local sizes. Pre-release: a tag with a
# suffix (v1.0.0-rc1); v1.0.0 is a full release. The tag must be v<version>[-suffix] of the version
# in pyproject.toml (scripts/release_meta.py check-tag).
#
# Environment: REPO (default $GITHUB_REPOSITORY, else pmixay/ReSense); GH_TOKEN or `gh auth login`
# (contents: write); DRY_RUN=1. Exits 2 on a bad argument or missing file, 3 without gh, 4 on a
# checksum mismatch, 5 when the published assets do not match, else gh's code.
set -euo pipefail
usage() { awk 'NR > 1 && /^#/ { print; next } NR > 1 { exit }' "$0" >&2; }   # the header comment
if [ $# -lt 1 ] || [ $# -gt 2 ] || [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 2
fi
TAG="$1"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ $# -eq 2 ]; then
  if [ ! -d "$2" ]; then echo "ERROR: directory $2 not found" >&2; exit 2; fi
  DIR="$(cd "$2" && pwd)"
else
  DIR="$ROOT/dist"
fi
cd "$ROOT"
REPO="${REPO:-${GITHUB_REPOSITORY:-pmixay/ReSense}}"
DRY_RUN="${DRY_RUN:-0}"
PY="$(command -v python3 || command -v python || true)"
if [ -z "$PY" ]; then echo "ERROR: python3 not found (scripts/release_meta.py)" >&2; exit 2; fi
META="$("$PY" scripts/release_meta.py check-tag "$TAG")" || exit 2
PRERELEASE="$(sed -n 's/^prerelease=//p' <<<"$META")"
RE_REPO='^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$'
RE_SUM='^[0-9a-f]{64}$'
if ! [[ "$REPO" =~ $RE_REPO ]]; then
  echo "ERROR: REPO '$REPO' is not owner/name" >&2
  exit 2
fi

NAME="resense-image-$TAG.tar.gz"
ARCHIVE="$DIR/$NAME"
NOTES="$DIR/release-notes-$TAG.md"
for f in "$ARCHIVE" "$ARCHIVE.sha256" "$NOTES"; do
  if [ ! -f "$f" ]; then
    echo "ERROR: $f not found (scripts/export_image.sh writes the archive and its .sha256," >&2
    echo "       scripts/release_meta.py notes the notes; scripts/release.sh does both)" >&2
    exit 2
  fi
done
if command -v sha256sum >/dev/null 2>&1; then SHA=(sha256sum); else SHA=(shasum -a 256); fi
read -r SUM LISTED _ < "$ARCHIVE.sha256" || true
LISTED="${LISTED#\*}"
if ! [[ "${SUM:-}" =~ $RE_SUM ]] || [ "${LISTED:-}" != "$NAME" ]; then
  echo "ERROR: $ARCHIVE.sha256 is not '<sha256>  $NAME'" >&2
  exit 4
fi
echo "== sha256 of $ARCHIVE"
ACTUAL="$(cd "$DIR" && "${SHA[@]}" "$NAME" | cut -d' ' -f1)"
if [ "$ACTUAL" != "$SUM" ]; then
  echo "ERROR: checksum mismatch: $ARCHIVE is $ACTUAL, its .sha256 says $SUM" >&2
  exit 4
fi
echo "   OK $ACTUAL"
ASSETS=("$ARCHIVE" "$ARCHIVE.sha256" "$DIR/SHA256SUMS")
PRE=()
if [ "$PRERELEASE" = true ]; then PRE=(--prerelease); fi
TITLE="ReSense $TAG"

if [ "$DRY_RUN" = "1" ]; then
  echo "== DRY_RUN=1: would write $DIR/SHA256SUMS ($SUM  $NAME) and run, for $REPO:"
  echo "gh release view $TAG --repo $REPO     # exists?"
  echo "  no:  gh release create $TAG --repo $REPO --verify-tag --title \"$TITLE\" --notes-file $NOTES ${PRE[*]:-} ${ASSETS[*]}"
  echo "  yes: gh release edit $TAG --repo $REPO --title \"$TITLE\" --notes-file $NOTES --prerelease=$PRERELEASE --draft=false"
  echo "       gh release upload $TAG --repo $REPO --clobber ${ASSETS[*]}"
  echo "gh release view $TAG --repo $REPO --json assets     # the three assets, local sizes"
  exit 0
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: the GitHub CLI (gh) is not installed: https://cli.github.com, then gh auth login" >&2
  exit 3
fi
(cd "$DIR" && "${SHA[@]}" "$NAME") > "$DIR/SHA256SUMS"
if gh release view "$TAG" --repo "$REPO" >/dev/null 2>&1; then
  echo "== release $TAG exists in $REPO: updating it and replacing its assets"
  gh release edit "$TAG" --repo "$REPO" --title "$TITLE" --notes-file "$NOTES" \
    --prerelease="$PRERELEASE" --draft=false >/dev/null
  gh release upload "$TAG" --repo "$REPO" --clobber "${ASSETS[@]}"
else
  echo "== creating release $TAG in $REPO ($([ "$PRERELEASE" = true ] && echo pre-release || echo release))"
  gh release create "$TAG" --repo "$REPO" --verify-tag --title "$TITLE" --notes-file "$NOTES" \
    ${PRE[@]+"${PRE[@]}"} "${ASSETS[@]}"
fi

echo "== the release's assets"
LIST="$(gh release view "$TAG" --repo "$REPO" --json assets --jq '.assets[] | "\(.name) \(.size)"')"
echo "$LIST" | sed 's/^/   /'
BAD=0
for f in "${ASSETS[@]}"; do
  want="$(wc -c < "$f" | tr -d ' ')"
  got="$(awk -v n="$(basename "$f")" '$1 == n { print $2 }' <<<"$LIST")"
  if [ "$got" != "$want" ]; then
    echo "ERROR: asset $(basename "$f"): ${got:-missing} bytes on GitHub, $want bytes here" >&2
    BAD=1
  fi
done
[ "$BAD" = 0 ] || exit 5
URL="$(gh release view "$TAG" --repo "$REPO" --json url --jq .url)"
echo
echo "PUBLISHED: $URL"
echo "   check a download: EXPECT_SHA256=$SUM scripts/verify_release.sh $TAG"
