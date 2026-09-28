#!/usr/bin/env bash
# The two original organizer bags of the cold-disk check (doubleT_obstacle, roundT_doubleT) in
# <dir>/for_hackathon/, verified against scripts/cold_bags.sha256 and docs/evidence/bag_metadata/.
#
#   scripts/fetch_cold_bags.sh <dir>          # verify; download and unpack only when they are not there
#   NO_DOWNLOAD=1 scripts/fetch_cold_bags.sh <dir>   # verify only
#
# The bags are what CI caches (.github/workflows/ci.yml, job "dataset"): 6.7 GB on disk, about a
# third of the 3.7 GB archive after the cache's own zstd, and no unpacking on a cache hit. Google
# Drive is asked for the archive only when the verified bags are absent, and the archive is deleted
# once they are unpacked and verified.
# Exit codes: 0 verified; 3 Google Drive refused the download (a quota or other page, not the
# archive); 4 not there and NO_DOWNLOAD=1; 1 any other failure (a checksum mismatch included).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIR="$(realpath -m "${1:?usage: fetch_cold_bags.sh <dir>}")"
PINS="$ROOT/scripts/cold_bags.sha256"
URL="https://drive.usercontent.google.com/download?id=1WTlR2wDSuEHTOARGK_gZeXDTZ9RZpswu&export=download&confirm=t"
BAGS=(doubleT_obstacle roundT_doubleT)

verify() {
  local b
  for b in "${BAGS[@]}"; do
    cmp -s "$DIR/for_hackathon/$b/metadata.yaml" "$ROOT/docs/evidence/bag_metadata/${b}_metadata.yaml" || return 1
  done
  (cd "$DIR" && grep ' for_hackathon/' "$PINS" | sha256sum --check --quiet --strict) || return 1
}

if verify 2>/dev/null; then
  echo "cold bags: verified in $DIR (no download)"
  exit 0
fi
if [[ "${NO_DOWNLOAD:-0}" == 1 ]]; then
  echo "cold bags: not in $DIR and NO_DOWNLOAD=1" >&2
  exit 4
fi

mkdir -p "$DIR"
TMP="$(mktemp -d "$DIR/.download.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
ARCHIVE="$TMP/dataset.zip"

# Google Drive answers 200 with the file, with its virus-scan page (the file is too large to scan;
# the page's download form carries the token and uuid to send back) or with a page such as its
# download-quota notice; curl --fail cannot tell them apart. Follow the form, wait out any other
# page, and print what the page said.
drive_page() {
  python3 - "$1" <<'PY'
import html.parser, sys, urllib.parse

class Page(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.action, self.fields, self.text, self.skip, self.form = None, {}, [], 0, False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("style", "script"):
            self.skip += 1
        if tag == "form" and a.get("id") == "download-form":
            self.form, self.action = True, a.get("action")
        elif tag == "input" and self.form and a.get("type") == "hidden" and a.get("name"):
            self.fields[a["name"]] = a.get("value") or ""

    def handle_endtag(self, tag):
        if tag in ("style", "script"):
            self.skip -= 1
        if tag == "form":
            self.form = False

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.text.append(data.strip())

p = Page()
p.feed(open(sys.argv[1], encoding="utf-8", errors="replace").read())
print("Google Drive sent a page, not the archive:", " ".join(p.text)[:500], file=sys.stderr)
if p.action and p.fields:
    print(p.action + "?" + urllib.parse.urlencode(p.fields))
PY
}

fetch_archive() {
  local part="$ARCHIVE.part" url="$URL" attempt next
  for attempt in 1 2 3 4; do
    curl --fail --location --retry 3 --retry-delay 2 --cookie-jar "$TMP/cookies" --cookie "$TMP/cookies" \
      --silent --show-error --output "$part" "$url"
    if [[ "$(head -c 2 "$part")" == "PK" ]]; then
      mv "$part" "$ARCHIVE"
      return 0
    fi
    next="$(drive_page "$part")"
    rm -f "$part"
    if [[ -n "$next" && "$url" == "$URL" ]]; then
      url="$next"         # the virus-scan page: its form is the download
    else
      url="$URL"
      if ((attempt < 4)); then echo "attempt $attempt: retrying in $((attempt * 30)) s" >&2; sleep $((attempt * 30)); fi
    fi
  done
  return 1
}

echo "cold bags: not in $DIR; downloading the organizers' archive once: $URL"
fetch_archive || { echo "cold bags: Google Drive did not send the archive" >&2; exit 3; }
(cd "$TMP" && sed -n '1s/  Датасет\.zip$/  dataset.zip/p' "$PINS" | sha256sum --check --strict) || {
  echo "cold bags: the archive's sha256 is not the pinned one ($PINS)" >&2
  exit 1
}
rm -rf "${BAGS[@]/#/$DIR/for_hackathon/}"
python3 "$ROOT/scripts/unpack_dataset.py" "$ARCHIVE" --out "$DIR" --only "$(IFS=,; echo "${BAGS[*]}")"
rm -f "$ARCHIVE"
verify || { echo "cold bags: unpacked bags do not match $PINS / docs/evidence/bag_metadata" >&2; exit 1; }
echo "cold bags: downloaded, unpacked and verified in $DIR"
