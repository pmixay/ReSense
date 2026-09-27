#!/usr/bin/env bash
# Cold-disk startup check using the organizer's bag. A small rosbag2
# read-ahead queue avoids turning the 20 s recording into a burst while the cold 4.8 GB SQLite
# file is preloaded; storage stalls remain real and the node still gets the original point clouds.
# Requires Docker and runs on the working branch and main; the downloaded raw bag is removed.
# DATASET_ZIP=<path> keeps the verified archive there (CI caches it) and reuses it when its
# sha256 still matches, so that Google Drive is not asked for 3.7 GB on every push.
set -euo pipefail

case "${GITHUB_REF:-}" in
  refs/heads/claude/nifty-pascal-lzgl78|refs/heads/claude/p1-p2-supported-playback-20260927|refs/heads/main) ;;
  *) echo "skip: original-bag cold-disk test runs on the working branch and main"; exit 0 ;;
esac

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${IMAGE:-resense:ci}"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/resense-p1-cold.XXXXXX")"
OUT="${OUT:-$ROOT/out/p1-cold-run}"
ARCHIVE="$(realpath -m "${DATASET_ZIP:-$WORK/dataset.zip}")"   # docker -v needs an absolute path
BAG="$WORK/for_hackathon/doubleT_obstacle"
CLEAR_BAG="$WORK/for_hackathon/roundT_doubleT"
URL="https://drive.usercontent.google.com/download?id=1WTlR2wDSuEHTOARGK_gZeXDTZ9RZpswu&export=download&confirm=t"
# the archive every recorded cold run used (docs/evidence/results/p4_data_intake_2026-09-26.json)
ARCHIVE_SHA256=e23166801794cdeb2dcd77a3cc8b40a906b1d9cefab6f26739e368234e9168be
mkdir -p "$OUT" "$(dirname "$ARCHIVE")"
trap 'rm -rf "$WORK"' EXIT

echo "source: $URL" | tee "$OUT/provenance.txt"
echo "playback: rate=1.0; read_ahead_queue_size=10" | tee -a "$OUT/provenance.txt"
git -C "$ROOT" rev-parse HEAD | sed 's/^/commit: /' | tee -a "$OUT/provenance.txt"
df -h "$WORK" | tee -a "$OUT/provenance.txt"

# Google Drive answers 200 with the file, with its virus-scan page (the file is too large to scan;
# the page's download form carries the token and uuid to send back) or with a page such as its
# download-quota notice; curl --fail cannot tell them apart. Follow the form, wait out any other
# page, and print what the page said. A ZIP whose sha256 is not the recorded one is removed below.
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
    curl --fail --location --retry 3 --retry-delay 2 --cookie-jar "$WORK/cookies" --cookie "$WORK/cookies" \
      --output "$part" "$url"
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
  echo "download is not a ZIP archive" >&2
  return 1
}

if [[ -f "$ARCHIVE" ]]; then
  echo "archive: $ARCHIVE, kept from an earlier run" | tee -a "$OUT/provenance.txt"
else
  fetch_archive
  echo "archive: downloaded to $ARCHIVE" | tee -a "$OUT/provenance.txt"
fi
SUM="$(sha256sum "$ARCHIVE")"
echo "$SUM" | tee -a "$OUT/provenance.txt"
[[ "${SUM%% *}" == "$ARCHIVE_SHA256" ]] || {
  echo "the archive's sha256 is not the recorded $ARCHIVE_SHA256; removed, the next run downloads it again" >&2
  rm -f "$ARCHIVE"
  exit 1
}
chmod 777 "$WORK"
docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -e PYTHONDONTWRITEBYTECODE=1 \
  -v "$WORK:/data" -v "$ARCHIVE:/dataset.zip:ro" "$IMAGE" python3 scripts/unpack_dataset.py \
  /dataset.zip --out /data --only doubleT_obstacle,roundT_doubleT
test -f "$BAG/metadata.yaml"
cmp "$BAG/metadata.yaml" "$ROOT/docs/evidence/bag_metadata/doubleT_obstacle_metadata.yaml"
test -f "$CLEAR_BAG/metadata.yaml"
cmp "$CLEAR_BAG/metadata.yaml" "$ROOT/docs/evidence/bag_metadata/roundT_doubleT_metadata.yaml"
sha256sum "$BAG/metadata.yaml" | tee -a "$OUT/provenance.txt"
find "$BAG" -maxdepth 1 -type f -name '*.db3' -print0 | sort -z | xargs -0 sha256sum \
  | tee -a "$OUT/provenance.txt"
sha256sum "$CLEAR_BAG/metadata.yaml" | tee -a "$OUT/provenance.txt"
find "$CLEAR_BAG" -maxdepth 1 -type f -name '*.db3' -print0 | sort -z | xargs -0 sha256sum \
  | tee -a "$OUT/provenance.txt"
[[ -n "${DATASET_ZIP:-}" ]] || rm -f "$ARCHIVE"
docker tag "$IMAGE" resense:latest

# The archive extraction and hashes warmed the page cache. Evict it before the exact dry-run path.
sudo sh -c 'sync; echo 3 > /proc/sys/vm/drop_caches'
SKIP_BUILD=1 OUT="$OUT/dry_run" scripts/dry_run.sh "$BAG" \
  --expect-obstacle --distance 50:62 --min-frames 20 --max-p95-latency 100 --max-dropped 0
echo "PASS: original doubleT_obstacle cold-disk dry run" | tee -a "$OUT/result.txt"

# Repeat the cold-cache check for the original clear 120-degree recording. The previous replay
# warmed only doubleT_obstacle, so this independently verifies a clear path from cold storage.
sudo sh -c 'sync; echo 3 > /proc/sys/vm/drop_caches'
SKIP_BUILD=1 OUT="$OUT/roundT_doubleT" scripts/dry_run.sh "$CLEAR_BAG" \
  --expect-clear --max-alarm-frames 2 --max-p95-latency 100 --max-dropped 0
echo "PASS: original roundT_doubleT cold-disk dry run" | tee -a "$OUT/result.txt"
