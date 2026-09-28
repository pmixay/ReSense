#!/usr/bin/env bash
# Cold-disk startup check using the organizer's bag. A small rosbag2
# read-ahead queue avoids turning the 20 s recording into a burst while the cold 4.8 GB SQLite
# file is preloaded; storage stalls remain real and the node still gets the original point clouds.
# Requires Docker and runs on the score/P3 branches, retained working branches and main.
# The two bags come from scripts/fetch_cold_bags.sh: DATASET_DIR=<dir> keeps them there (CI
# restores that directory from its cache, job "docker") and reuses them while their sha256 still
# match scripts/cold_bags.sha256, so that Google Drive is asked for the 3.7 GB archive only when
# they are absent. NO_DOWNLOAD=1 (CI): never download, fail when they are not there.
set -euo pipefail

case "${GITHUB_REF:-}" in
  refs/heads/gpt-score-push-20260928|refs/heads/integration/p3-score-sync-20260928|refs/heads/experiment/cross-ring-sparse-evidence|refs/heads/testovaya-gpt|refs/heads/claude/nifty-pascal-lzgl78|refs/heads/claude/p1-p2-supported-playback-20260927|refs/heads/claude/amazing-fermi-t67v8g|refs/heads/main) ;;
  *) echo "skip: original-bag cold-disk test runs on the score/P3 branches, retained working branches and main"; exit 0 ;;
esac

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${IMAGE:-resense:ci}"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/resense-p1-cold.XXXXXX")"
OUT="${OUT:-$ROOT/out/p1-cold-run}"
BAGS_DIR="$(realpath -m "${DATASET_DIR:-$WORK}")"   # docker -v needs an absolute path
BAG="$BAGS_DIR/for_hackathon/doubleT_obstacle"
CLEAR_BAG="$BAGS_DIR/for_hackathon/roundT_doubleT"
mkdir -p "$OUT"
trap 'rm -rf "$WORK"' EXIT

echo "source: scripts/fetch_cold_bags.sh (pins: scripts/cold_bags.sha256)" | tee "$OUT/provenance.txt"
echo "playback: rate=1.0; read_ahead_queue_size=10" | tee -a "$OUT/provenance.txt"
git -C "$ROOT" rev-parse HEAD | sed 's/^/commit: /' | tee -a "$OUT/provenance.txt"
df -h "$BAGS_DIR" | tee -a "$OUT/provenance.txt"
"$ROOT/scripts/fetch_cold_bags.sh" "$BAGS_DIR" | tee -a "$OUT/provenance.txt"
chmod -R a+rX "$BAGS_DIR/for_hackathon"
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
docker tag "$IMAGE" resense:latest

# The cache restore or unpacking and the hashes warmed the page cache. Evict it before the exact dry-run path.
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

# The node's fast input path (28.09, ros2_ws/src/resense_ros/resense_ros/fastcloud.py) against rclpy's
# message conversion and resense.pointcloud, byte for byte, on every frame of both recordings.
docker run --rm -v "$BAGS_DIR/for_hackathon":/data:ro -v "$OUT":/out "$IMAGE" \
  python3 /opt/resense/scripts/check_fast_input.py /data/doubleT_obstacle /data/roundT_doubleT \
  --json /out/fast_input.json | tee "$OUT/fast_input.txt"
echo "PASS: fast input path identical on every frame of both original recordings" | tee -a "$OUT/result.txt"
