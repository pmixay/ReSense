#!/usr/bin/env bash
# Fetch the organizers' data onto the VM and build the full-rate frame caches (docs/DATASET.md):
#   six    the six recordings of Датасет.zip (Google Drive, 3.7 GB) -> $DATA_DIR/for_hackathon/<bag>
#   fake   cloud_with_fake_obj (Yandex Disk, 1.75 GB -> 7.4 GB bag)  -> $DATA_DIR/cloud_with_fake_obj
#   ride   the 20-minute new_data ride (Yandex Disk, 17 GB -> 90 GB) -> $DATA_DIR/new_data (if kept)
# and caches every frame of each with scripts/cache_frames.py --every 1 --int16 --stamps into
# $CACHE_DIR/<recording> (what scripts/eval_real.py and scripts/regression_gate.py read).
#
#   scripts/vm/fetch_data.sh --plan              # what fits on this disk, nothing downloaded
#   scripts/vm/fetch_data.sh                     # everything that fits (idempotent: re-run to resume)
#   scripts/vm/fetch_data.sh --only six,fake     # skip the ride
#   DATASET_ZIP=~/Датасет.zip scripts/vm/fetch_data.sh   # the zip copied over by hand (scp)
#
# Disk policy (checked first, and again before every step; sizes in DATASET.md, caches measured):
#   always   doubleT_obstacle + roundT_doubleT as original .db3 bags (the dry run plays them),
#            the caches of the six recordings and of cloud_with_fake_obj (the regression gate)
#   then, in this order, what still fits: the ride's cache (streamed split file by split file,
#            the 90 GB bag never on disk), the four other bags kept, the cloud_with_fake_obj bag
#            kept, the whole ride bag kept (for a 20-minute `ros2 bag play /data/new_data`)
#   what does not fit is skipped with the size it would need. Datasets.zip is deleted after
#   unpacking unless it was given with DATASET_ZIP or --keep-zip.
#
# Options:
#   --plan                    print the plan and exit
#   --only LIST               any of six,fake,ride (default all three)
#   --ride MODE               auto (default) | cache (stream, cache only) | keep (bag + cache) | skip
#   --keep-other-bags MODE    auto (default) | yes | no   (the four bags besides the dry-run pair)
#   --keep-fake-bag MODE      auto (default) | yes | no
#   --keep-zip                keep the downloaded Датасет.zip
#   --reserve-gb N            left free for Docker images, the image archive and results (default:
#                             8 when $DATA_DIR shares the disk with /var/lib/docker, else 2)
#   --jobs N                  parallel cache_frames.py runs (default: by vCPU, at most 4)
#   --assume-free-gb N        with --plan / --dry-run: plan as if N GiB were free (size a data disk)
#   --data-dir D --cache-dir D
#   -n, --dry-run             print the commands (DRY_RUN=1)
#   -h, --help
# Environment: DATASET_ZIP (a local Датасет.zip), GDRIVE_ID (default the organizers' file id).
# Exit: 0 everything planned is in place; 1 a step failed or something planned did not fit;
#   2 bad arguments / missing tools (run scripts/vm/setup_vm.sh first); 3 not even the minimum fits.
# Log: ~/resense_results/<date>/fetch/fetch_log.txt (+ inventory.txt, one cache_<name>.txt per cache)
set -Eeuo pipefail
SELF="${BASH_SOURCE[0]}"
# shellcheck source=scripts/vm/lib.sh
. "$(cd "$(dirname "$SELF")" && pwd)/lib.sh"

usage() { header_help "$SELF"; }
PLAN_ONLY=0; ONLY="six,fake,ride"; RIDE_MODE=auto; KEEP_OTHERS=auto; KEEP_FAKE=auto; KEEP_ZIP=0
RESERVE_GB=""; JOBS=""; ASSUME_FREE_GB=""
while [ $# -gt 0 ]; do
  case "$1" in
    --plan) PLAN_ONLY=1; shift ;;
    --only) ONLY="${2:?}"; shift 2 ;;
    --ride) RIDE_MODE="${2:?}"; shift 2 ;;
    --keep-other-bags) KEEP_OTHERS="${2:?}"; shift 2 ;;
    --keep-fake-bag) KEEP_FAKE="${2:?}"; shift 2 ;;
    --keep-zip) KEEP_ZIP=1; shift ;;
    --reserve-gb) RESERVE_GB="${2:?}"; shift 2 ;;
    --jobs) JOBS="${2:?}"; shift 2 ;;
    --assume-free-gb) ASSUME_FREE_GB="${2:?}"; shift 2 ;;
    --data-dir) DATA_DIR="${2:?}"; CACHE_DIR="$DATA_DIR/cache"; shift 2 ;;
    --cache-dir) CACHE_DIR="${2:?}"; shift 2 ;;
    -n|--dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; die 2 "unknown argument: $1" ;;
  esac
done
case "$RIDE_MODE" in auto|cache|keep|skip) ;; *) die 2 "--ride takes auto|cache|keep|skip" ;; esac
case "$KEEP_OTHERS" in auto|yes|no) ;; *) die 2 "--keep-other-bags takes auto|yes|no" ;; esac
case "$KEEP_FAKE" in auto|yes|no) ;; *) die 2 "--keep-fake-bag takes auto|yes|no" ;; esac
want() { [[ ",$ONLY," == *",$1,"* ]]; }
for w in ${ONLY//,/ }; do case "$w" in six|fake|ride) ;; *) die 2 "--only takes six,fake,ride" ;; esac; done

GDRIVE_ID="${GDRIVE_ID:-1WTlR2wDSuEHTOARGK_gZeXDTZ9RZpswu}"
FAKE_URL="https://disk.yandex.ru/d/KpkG_yKoGk-vHQ"
RIDE_URL="https://disk.yandex.ru/d/N8IUpAyd7jyvow"
PY="$(venv_python)"
SIX=(doubleT_obstacle doubleT_platform roundT_doubleT roundT_pressureGate_roundT
     roundT_squareT_pressureGate_squareT squareT_platform_squareT_switch)
PAIR=(doubleT_obstacle roundT_doubleT)
OTHERS=(doubleT_platform roundT_pressureGate_roundT roundT_squareT_pressureGate_squareT squareT_platform_squareT_switch)
# MiB: bags from DATASET.md (its sizes are GiB: doubleT_obstacle_0.db3 is 4 820 MB = 4.49 GiB, measured
# 25.09) + 3 %, caches measured on 24.09 (+5 %)
declare -A BAG_MB=([doubleT_obstacle]=4650 [doubleT_platform]=2750 [roundT_doubleT]=1990
  [roundT_pressureGate_roundT]=2120 [roundT_squareT_pressureGate_squareT]=4330 [squareT_platform_squareT_switch]=6960)
declare -A CACHE_MB=([doubleT_obstacle]=560 [doubleT_platform]=460 [roundT_doubleT]=385
  [roundT_pressureGate_roundT]=405 [roundT_squareT_pressureGate_squareT]=820 [squareT_platform_squareT_switch]=1180)
declare -A FRAMES=([doubleT_obstacle]=201 [doubleT_platform]=345 [roundT_doubleT]=252 [roundT_pressureGate_roundT]=268
  [roundT_squareT_pressureGate_squareT]=545 [squareT_platform_squareT_switch]=877 [cloud_with_fake_obj]=1510)
ZIP_MB=3800; FAKE_BAG_MB=7700; FAKE_CACHE_MB=2200; RIDE_BAG_MB=90100; RIDE_CACHE_MB=16600; RIDE_FILE_MB=408; RIDE_FILES=221
SIXDIR="$DATA_DIR/for_hackathon"
ZIP_DL="$DATA_DIR/downloads/dataset.zip"

detect_resources
if [ -z "$JOBS" ]; then JOBS=$(( NPROC / 2 )); [ "$JOBS" -ge 1 ] || JOBS=1; [ "$JOBS" -le 4 ] || JOBS=4; fi
if [ -z "$RESERVE_GB" ]; then
  if same_fs "$DATA_DIR" /var/lib/docker; then RESERVE_GB=8; else RESERVE_GB=2; fi
fi
RESERVE_MB=$(( RESERVE_GB * 1024 ))

# ---- what is already there -----------------------------------------------------------------------
cache_ok() {   # <dir> [expected frames]: complete when its stamps file (written last) is there
  compgen -G "$1/*_stamps.json" >/dev/null 2>&1 && [ "$(npy_count "$1")" -gt 0 ]
}
ride_cached_files() { { find "$CACHE_DIR/new_data" -maxdepth 1 -name 'new_data_*_stamps.json' 2>/dev/null || true; } | wc -l | tr -d ' '; }
six_bag_ok() { bag_ok "$SIXDIR/$1"; }
zip_path() {
  if [ -n "${DATASET_ZIP:-}" ]; then printf '%s\n' "$DATASET_ZIP"; else printf '%s\n' "$ZIP_DL"; fi
}
zip_ok() { local z; z="$(zip_path)"; [ -s "$z" ] && [ "$(head -c 2 "$z" 2>/dev/null)" = PK ]; }

# ---- the plan ----------------------------------------------------------------------------------
FREE_MB="$(free_mb "$DATA_DIR")"
if [ -n "$ASSUME_FREE_GB" ]; then
  [ "$PLAN_ONLY" = 1 ] || [ "$DRY_RUN" = 1 ] || die 2 "--assume-free-gb only previews a plan (with --plan or --dry-run)"
  FREE_MB=$(( ASSUME_FREE_GB * 1024 ))
fi
AVAIL=$(( FREE_MB - RESERVE_MB ))
PLAN=()            # printable lines
plan() { PLAN+=("$(printf '  %-44s %9s  %s' "$1" "$2" "$3")"); }
mb() { printf '%s GiB' "$(gb "$1")"; }
USED=0             # MiB this run adds and keeps

NEED_PAIR=(); NEED_OTHERS_CACHE=(); NEED_SIX_CACHE=()
if want six; then
  for b in "${PAIR[@]}"; do six_bag_ok "$b" || { NEED_PAIR+=("$b"); USED=$(( USED + BAG_MB[$b] )); }; done
  for b in "${SIX[@]}"; do cache_ok "$CACHE_DIR/$b" || { NEED_SIX_CACHE+=("$b"); USED=$(( USED + CACHE_MB[$b] )); }; done
  for b in "${OTHERS[@]}"; do cache_ok "$CACHE_DIR/$b" || six_bag_ok "$b" || NEED_OTHERS_CACHE+=("$b"); done
fi
FAKE_CACHE_NEEDED=0; FAKE_BAG_PRESENT=0
bag_ok "$DATA_DIR/cloud_with_fake_obj" && FAKE_BAG_PRESENT=1
if want fake && ! cache_ok "$CACHE_DIR/cloud_with_fake_obj"; then FAKE_CACHE_NEEDED=1; USED=$(( USED + FAKE_CACHE_MB )); fi

# transient peaks: the zip plus the largest other bag unpacked for caching only; the fake bag
ZIP_T=0
if want six && { [ ${#NEED_PAIR[@]} -gt 0 ] || [ ${#NEED_SIX_CACHE[@]} -gt 0 ]; } && ! zip_ok; then ZIP_T=$ZIP_MB; fi
largest_other() { local m=0 b; for b in "${NEED_OTHERS_CACHE[@]}"; do [ "${BAG_MB[$b]}" -gt "$m" ] && m=${BAG_MB[$b]}; done; echo "$m"; }
T_SIX=$(( ZIP_T + $(largest_other) ))
T_FAKE=0; [ "$FAKE_CACHE_NEEDED" = 1 ] && [ "$FAKE_BAG_PRESENT" = 0 ] && T_FAKE=$FAKE_BAG_MB
T_CORE=$T_SIX; [ "$T_FAKE" -gt "$T_CORE" ] && T_CORE=$T_FAKE
CORE=$USED
MIN_OK=1
if [ $(( CORE + T_CORE )) -gt "$AVAIL" ]; then MIN_OK=0; fi

# optional items in priority order
RIDE_DONE_FILES="$(ride_cached_files)"
RIDE_BAG_OK=0; bag_ok "$DATA_DIR/new_data" && RIDE_BAG_OK=1
RIDE_CACHE_MISSING_MB=$(( RIDE_CACHE_MB * (RIDE_FILES - RIDE_DONE_FILES) / RIDE_FILES ))
[ "$RIDE_CACHE_MISSING_MB" -ge 0 ] || RIDE_CACHE_MISSING_MB=0
RIDE_T=$(( 4 * RIDE_FILE_MB ))
DO_RIDE=skip; RIDE_WHY=""
[ "$MIN_OK" = 1 ] || RIDE_WHY="not even the minimum fits"
[ "$RIDE_MODE" != skip ] || RIDE_WHY="--ride skip"
if want ride && [ "$MIN_OK" = 1 ] && [ "$RIDE_MODE" != skip ]; then
  if [ "$RIDE_DONE_FILES" -ge "$RIDE_FILES" ] && { [ "$RIDE_MODE" != keep ] || [ "$RIDE_BAG_OK" = 1 ]; }; then
    DO_RIDE=complete
  elif [ $(( USED + RIDE_CACHE_MISSING_MB + RIDE_T )) -le "$AVAIL" ] || [ "$RIDE_MODE" = cache ]; then
    DO_RIDE=cache; USED=$(( USED + RIDE_CACHE_MISSING_MB ))
  else
    RIDE_WHY="needs $(mb $(( RIDE_CACHE_MISSING_MB + RIDE_T ))) more (a bigger data disk gives the gate the ride)"
  fi
fi
DO_KEEP_OTHERS=no
if want six && [ "$MIN_OK" = 1 ]; then
  S_O=0; for b in "${OTHERS[@]}"; do six_bag_ok "$b" || S_O=$(( S_O + BAG_MB[$b] )); done
  if [ "$KEEP_OTHERS" = yes ] || { [ "$KEEP_OTHERS" = auto ] && [ $(( USED + S_O + ZIP_T )) -le "$AVAIL" ]; }; then
    DO_KEEP_OTHERS=yes; USED=$(( USED + S_O ))
  fi
fi
DO_KEEP_FAKE=no
if want fake && [ "$MIN_OK" = 1 ]; then
  if [ "$FAKE_BAG_PRESENT" = 1 ] && [ "$KEEP_FAKE" != no ]; then
    DO_KEEP_FAKE=yes
  elif [ "$KEEP_FAKE" = yes ] || { [ "$KEEP_FAKE" = auto ] && [ $(( USED + FAKE_BAG_MB )) -le "$AVAIL" ]; }; then
    DO_KEEP_FAKE=yes; USED=$(( USED + FAKE_BAG_MB ))
  fi
fi
if [ "$DO_RIDE" = cache ] || [ "$DO_RIDE" = complete ]; then
  if [ "$RIDE_BAG_OK" = 1 ]; then
    [ "$DO_RIDE" = complete ] || DO_RIDE=keep
  elif [ "$RIDE_MODE" = keep ] || { [ "$RIDE_MODE" = auto ] && [ $(( USED + RIDE_BAG_MB )) -le "$AVAIL" ]; }; then
    DO_RIDE=keep; USED=$(( USED + RIDE_BAG_MB ))
  fi
fi

print_plan() {
  echo "disk: $DATA_DIR on $(fs_of "$DATA_DIR"): $(mb "$FREE_MB") free; $(mb "$RESERVE_MB") kept in reserve" \
       "(Docker images, the image archive, results), $(mb "$AVAIL") usable"
  echo "      ($(if same_fs "$DATA_DIR" /var/lib/docker; then echo "same disk as /var/lib/docker"; else echo "Docker is on another disk"; fi);" \
       "cache jobs $JOBS)"
  PLAN=()
  if want six; then
    for b in "${PAIR[@]}"; do
      if six_bag_ok "$b"; then plan "bag $b" "present" "kept (dry run)"; else plan "bag $b" "$(mb "${BAG_MB[$b]}")" "fetch, keep (dry run)"; fi
    done
    for b in "${OTHERS[@]}"; do
      if six_bag_ok "$b"; then plan "bag $b" "present" "kept"
      elif [ "$DO_KEEP_OTHERS" = yes ]; then plan "bag $b" "$(mb "${BAG_MB[$b]}")" "fetch, keep"
      elif cache_ok "$CACHE_DIR/$b"; then plan "bag $b" "$(mb "${BAG_MB[$b]}")" "not fetched (cache present; does not fit to keep)"
      else plan "bag $b" "$(mb "${BAG_MB[$b]}")" "unpack for caching, then delete (does not fit to keep)"; fi
    done
    for b in "${SIX[@]}"; do
      if cache_ok "$CACHE_DIR/$b"; then plan "cache $b" "present" "$(npy_count "$CACHE_DIR/$b") frames"
      else plan "cache $b" "$(mb "${CACHE_MB[$b]}")" "build (${FRAMES[$b]} frames)"; fi
    done
    if [ "$ZIP_T" -gt 0 ]; then plan "dataset zip (Google Drive)" "$(mb "$ZIP_MB")" "download to $ZIP_DL$([ "$KEEP_ZIP" = 1 ] || echo ', deleted after unpacking')"
    elif zip_ok; then plan "dataset zip" "present" "$(zip_path)"; fi
  fi
  if want fake; then
    if [ "$FAKE_BAG_PRESENT" = 1 ]; then plan "bag cloud_with_fake_obj" "present" "$([ "$DO_KEEP_FAKE" = yes ] && echo kept || echo 'deleted after caching')"
    elif [ "$DO_KEEP_FAKE" = yes ]; then plan "bag cloud_with_fake_obj" "$(mb "$FAKE_BAG_MB")" "stream from Yandex Disk, keep"
    elif [ "$FAKE_CACHE_NEEDED" = 1 ]; then plan "bag cloud_with_fake_obj" "$(mb "$FAKE_BAG_MB")" "stream, cache, then delete (does not fit to keep)"; fi
    if cache_ok "$CACHE_DIR/cloud_with_fake_obj"; then plan "cache cloud_with_fake_obj" "present" "$(npy_count "$CACHE_DIR/cloud_with_fake_obj") frames"
    else plan "cache cloud_with_fake_obj" "$(mb "$FAKE_CACHE_MB")" "build (1510 frames)"; fi
  fi
  if want ride; then
    case "$DO_RIDE" in
      complete) plan "ride new_data" "present" "cache complete ($RIDE_DONE_FILES of $RIDE_FILES split files)$([ "$RIDE_BAG_OK" = 1 ] && echo ', bag kept')" ;;
      keep) plan "ride new_data: bag + cache" "$(mb $(( (RIDE_BAG_OK == 1 ? 0 : RIDE_BAG_MB) + RIDE_CACHE_MISSING_MB )))" \
                 "$([ "$RIDE_BAG_OK" = 1 ] && echo 'bag present, cache from it' || echo 'stream 17 GB, keep the 90 GB bag')" ;;
      cache) plan "ride new_data: cache only" "$(mb "$RIDE_CACHE_MISSING_MB")" \
                  "stream 17 GB, cache split file by split file ($RIDE_DONE_FILES of $RIDE_FILES done); the bag is not kept" ;;
      skip) plan "ride new_data" "$(mb "$RIDE_CACHE_MB")" "SKIPPED: ${RIDE_WHY:-$RIDE_MODE}" ;;
    esac
  fi
  printf '%s\n' "${PLAN[@]}"
  echo "  this run adds and keeps about $(mb "$USED"); peak while unpacking about $(mb $(( CORE + T_CORE )))"
  [ "$MIN_OK" = 1 ] || echo "  NOT ENOUGH DISK for the minimum (dry-run pair + caches): needs $(mb $(( CORE + T_CORE ))), usable $(mb "$AVAIL")"
}

if [ "$PLAN_ONLY" = 1 ]; then
  print_plan
  if [ "$MIN_OK" = 1 ]; then exit 0; else exit 3; fi
fi

# ---- run -----------------------------------------------------------------------------------------
if [ "$DRY_RUN" = 1 ]; then OUT="$RESULTS_ROOT/$RUN_DATE/fetch"; mkdir -p "$OUT"; else OUT="$(results_dir fetch)"; fi
start_log "$OUT/fetch_log.txt"
log "== ReSense data fetch: $DATA_DIR (caches $CACHE_DIR), repo $REPO_DIR, only $ONLY, dry run $DRY_RUN"
print_plan | tee "$OUT/plan.txt"
[ "$MIN_OK" = 1 ] || die 3 "not even the dry-run pair and the caches fit: free space on $DATA_DIR (or mount a data disk there, scripts/vm/setup_vm.sh prints how)"
if [ "$DRY_RUN" != 1 ]; then
  [ -x "$PY" ] || die 2 "no venv python at $PY: run scripts/vm/setup_vm.sh first"
  "$PY" -c "import rosbags, zstandard, numpy, yaml" 2>/dev/null || die 2 "$PY lacks rosbags / zstandard / numpy / pyyaml: run scripts/vm/setup_vm.sh"
  [ -f "$REPO_DIR/scripts/unpack_dataset.py" ] || die 2 "no ReSense checkout at $REPO_DIR"
  mkdir -p "$DATA_DIR" "$CACHE_DIR" 2>/dev/null || die 2 "cannot write $DATA_DIR (setup_vm.sh gives it to the user)"
  [ -w "$DATA_DIR" ] || die 2 "cannot write $DATA_DIR"
fi
FAILED=()
fits() {   # fits <MiB> <what>: enough free space right now for a step (keeps the reserve)
  [ "$DRY_RUN" = 1 ] && return 0
  local f; f="$(free_mb "$DATA_DIR")"
  if [ $(( f - RESERVE_MB )) -lt "$1" ]; then
    warn "skipping $2: needs $(mb "$1"), $(mb $(( f - RESERVE_MB ))) usable now"
    FAILED+=("$2 (no space)")
    return 1
  fi
}
cache_one() {   # cache_one <bag dir or .db3> <name>
  local src="$1" name="$2" dst="$CACHE_DIR/$2"
  log "caching $name -> $dst"
  run rm -f "$dst"/*_stamps.json
  if [ "$DRY_RUN" = 1 ]; then
    pyenv "$PY" "$REPO_DIR/scripts/cache_frames.py" "$src" "$dst" --every 1 --int16 --stamps; return 0
  fi
  pyenv env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 "$PY" "$REPO_DIR/scripts/cache_frames.py" "$src" "$dst" \
    --every 1 --int16 --stamps > "$OUT/cache_$name.txt" 2>&1
}
cache_many() {  # cache_many <name>... (bags under $SIXDIR), $JOBS at a time
  local pids=() names=() b i rc=0
  for b in "$@"; do
    if [ "$DRY_RUN" = 1 ]; then cache_one "$SIXDIR/$b" "$b"; continue; fi
    cache_one "$SIXDIR/$b" "$b" & pids+=($!); names+=("$b")
    if [ ${#pids[@]} -ge "$JOBS" ]; then wait "${pids[0]}" || rc=1; pids=("${pids[@]:1}"); fi
  done
  for i in "${pids[@]}"; do wait "$i" || rc=1; done
  for b in "$@"; do
    if [ "$DRY_RUN" != 1 ] && ! cache_ok "$CACHE_DIR/$b"; then FAILED+=("cache $b (see $OUT/cache_$b.txt)"); rc=1; fi
  done
  return "$rc"
}
unpack_six() {  # unpack_six <bag>...
  local csv; csv="$(IFS=,; echo "$*")"
  log "unpacking $csv from $(zip_path) (streamed: zip -> zip -> zstd -> tar)"
  pyenv "$PY" "$REPO_DIR/scripts/unpack_dataset.py" "$(zip_path)" --out "$DATA_DIR" --only "$csv"
}

gdrive_download() {   # Google Drive's large-file endpoint; resumes; gdown as the fallback
  local out="$1" url="https://drive.usercontent.google.com/download?id=${GDRIVE_ID}&export=download&confirm=t" rc=0
  run mkdir -p "$(dirname "$out")"
  if [ "$DRY_RUN" = 1 ]; then run curl -fL --retry 5 -C - -o "$out.part" "$url"; run mv "$out.part" "$out"; return 0; fi
  if [ -s "$out.part" ] && [ "$(head -c 2 "$out.part")" != PK ]; then rm -f "$out.part"; fi
  log "downloading Датасет.zip from Google Drive ($(mb "$ZIP_MB")) -> $out"
  curl -fL --retry 5 --retry-delay 10 --connect-timeout 30 -C - -o "$out.part" "$url" || rc=$?
  if [ "$rc" = 33 ]; then rm -f "$out.part"; rc=0; curl -fL --retry 5 --retry-delay 10 -o "$out.part" "$url" || rc=$?; fi
  if [ "$rc" = 0 ] && [ "$(head -c 2 "$out.part" 2>/dev/null)" = PK ]; then mv -f "$out.part" "$out"; return 0; fi
  warn "curl did not get the zip (exit $rc; Google may have answered with a page instead of the file)"
  rm -f "$out.part"
  if [ -x "$VENV/bin/gdown" ] && "$VENV/bin/gdown" "$GDRIVE_ID" -O "$out" && [ "$(head -c 2 "$out")" = PK ]; then return 0; fi
  rm -f "$out"
  die 1 "could not download Датасет.zip. Download it in a browser (docs/DATASET.md link), copy it over with
       scp Датасет.zip <vm>:~/ and re-run with DATASET_ZIP=~/Датасет.zip scripts/vm/fetch_data.sh"
}

# ---- 1. the six recordings --------------------------------------------------------------------------
OTHER_BAGS_MISSING=0
for b in "${OTHERS[@]}"; do six_bag_ok "$b" || OTHER_BAGS_MISSING=1; done
if want six && { [ ${#NEED_PAIR[@]} -gt 0 ] || [ ${#NEED_SIX_CACHE[@]} -gt 0 ] \
                 || { [ "$DO_KEEP_OTHERS" = yes ] && [ "$OTHER_BAGS_MISSING" = 1 ]; }; }; then
  hr; log "== six recordings (Google Drive)"
  if ! zip_ok; then
    if [ -n "${DATASET_ZIP:-}" ] && [ "$DRY_RUN" != 1 ]; then die 2 "DATASET_ZIP=$DATASET_ZIP is not a zip file"; fi
    if fits "$ZIP_MB" "Датасет.zip"; then gdrive_download "$ZIP_DL"; fi
  fi
  if zip_ok || [ "$DRY_RUN" = 1 ]; then
    FIRST=("${NEED_PAIR[@]}")
    if [ "$DO_KEEP_OTHERS" = yes ]; then
      for b in "${OTHERS[@]}"; do six_bag_ok "$b" || FIRST+=("$b"); done
    fi
    if [ ${#FIRST[@]} -gt 0 ]; then
      need=0; for b in "${FIRST[@]}"; do need=$(( need + BAG_MB[$b] )); done
      if fits "$need" "bags ${FIRST[*]}"; then
        unpack_six "${FIRST[@]}" || FAILED+=("unpack ${FIRST[*]}")
      fi
    fi
    todo=()
    for b in "${SIX[@]}"; do
      cache_ok "$CACHE_DIR/$b" && continue
      if six_bag_ok "$b" || { [ "$DRY_RUN" = 1 ] && [[ " ${FIRST[*]} " == *" $b "* ]]; }; then todo+=("$b"); fi
    done
    if [ ${#todo[@]} -gt 0 ]; then cache_many "${todo[@]}" || true; fi
    # the other bags that are not kept: unpack one, cache it, delete it
    for b in "${OTHERS[@]}"; do
      if cache_ok "$CACHE_DIR/$b" || six_bag_ok "$b" || [ "$DO_KEEP_OTHERS" = yes ]; then continue; fi
      if fits "$(( BAG_MB[$b] + CACHE_MB[$b] ))" "bag $b (for caching)"; then
        if unpack_six "$b"; then cache_many "$b" || true; else FAILED+=("unpack $b"); fi
        log "deleting the bag $b (cached; not kept, the disk is short)"
        run rm -rf "${SIXDIR:?}/$b"
      fi
    done
    if [ "$KEEP_ZIP" != 1 ] && [ -z "${DATASET_ZIP:-}" ] && [ -f "$ZIP_DL" ]; then
      missing=0; for b in "${SIX[@]}"; do cache_ok "$CACHE_DIR/$b" || missing=1; done
      for b in "${PAIR[@]}"; do six_bag_ok "$b" || missing=1; done
      if [ "$missing" = 0 ]; then log "deleting $ZIP_DL (--keep-zip keeps it)"; run rm -f "$ZIP_DL"; fi
    fi
  fi
fi

# ---- 2. cloud_with_fake_obj -----------------------------------------------------------------------
if want fake && { [ "$FAKE_CACHE_NEEDED" = 1 ] || { [ "$DO_KEEP_FAKE" = yes ] && [ "$FAKE_BAG_PRESENT" = 0 ]; }; }; then
  hr; log "== cloud_with_fake_obj (Yandex Disk)"
  if [ "$FAKE_BAG_PRESENT" = 1 ] || { fits "$(( FAKE_BAG_MB + FAKE_CACHE_MB ))" "cloud_with_fake_obj" \
       && pyenv "$PY" "$REPO_DIR/scripts/unpack_dataset.py" "$FAKE_URL" --out "$DATA_DIR"; }; then
    if [ "$FAKE_CACHE_NEEDED" = 1 ]; then
      cache_one "$DATA_DIR/cloud_with_fake_obj" cloud_with_fake_obj || true
      [ "$DRY_RUN" = 1 ] || cache_ok "$CACHE_DIR/cloud_with_fake_obj" || FAILED+=("cache cloud_with_fake_obj (see $OUT/cache_cloud_with_fake_obj.txt)")
    fi
    if [ "$DO_KEEP_FAKE" != yes ]; then
      log "deleting the bag cloud_with_fake_obj (cached; not kept, the disk is short)"
      run rm -rf "${DATA_DIR:?}/cloud_with_fake_obj"
    fi
  else
    FAILED+=("cloud_with_fake_obj")
  fi
fi

# ---- 3. the ride ----------------------------------------------------------------------------------
if want ride; then
  hr
  case "$DO_RIDE" in
    complete) log "== ride: cache complete ($RIDE_DONE_FILES split files), nothing to do" ;;
    skip) log "== ride: SKIPPED (${RIDE_WHY:-$RIDE_MODE}); the regression gate runs without it and says so"
          [ "$RIDE_MODE" = skip ] || FAILED+=("ride (no space: ${RIDE_WHY})") ;;
    cache|keep)
      args=(--cache "$CACHE_DIR/new_data" --jobs "$JOBS" --python "$PY")
      if [ "$DO_RIDE" = keep ] && [ "$RIDE_BAG_OK" = 1 ]; then args+=(--from-dir "$DATA_DIR/new_data")
      elif [ "$DO_RIDE" = keep ]; then args+=(--source "$RIDE_URL" --keep "$DATA_DIR/new_data")
      else args+=(--source "$RIDE_URL" --tmp "$DATA_DIR/.new_data_stream"); fi
      log "== ride ($DO_RIDE): streaming 17 GB from Yandex Disk, ~20-40 min at 10-20 MB/s"
      pyenv "$PY" "$VM_KIT_DIR/stream_cache.py" "${args[@]}" || FAILED+=("ride cache (resume: re-run this script)")
      ;;
  esac
fi

# ---- 4. permissions (the console test plays as uid 1000), inventory --------------------------------
for d in "$SIXDIR" "$DATA_DIR/cloud_with_fake_obj" "$DATA_DIR/new_data" "$CACHE_DIR"; do
  if [ -d "$d" ]; then run chmod -R a+rX "$d"; fi
done
hr
{
  echo "inventory of $DATA_DIR, $(date -Is)"
  for b in "${SIX[@]}"; do
    printf '  %-42s bag %-8s cache %s\n' "$b" "$(six_bag_ok "$b" && echo yes || echo no)" \
      "$(cache_ok "$CACHE_DIR/$b" && echo "$(npy_count "$CACHE_DIR/$b") frames" || echo no)"
  done
  printf '  %-42s bag %-8s cache %s\n' cloud_with_fake_obj "$(bag_ok "$DATA_DIR/cloud_with_fake_obj" && echo yes || echo no)" \
    "$(cache_ok "$CACHE_DIR/cloud_with_fake_obj" && echo "$(npy_count "$CACHE_DIR/cloud_with_fake_obj") frames" || echo no)"
  printf '  %-42s bag %-8s cache %s of %s split files\n' new_data "$(bag_ok "$DATA_DIR/new_data" && echo yes || echo no)" \
    "$(ride_cached_files)" "$RIDE_FILES"
  echo "  free on $DATA_DIR: $(mb "$(free_mb "$DATA_DIR")")"
} | tee "$OUT/inventory.txt"
if [ ${#FAILED[@]} -gt 0 ]; then
  echo "NOT COMPLETE: ${FAILED[*]}"
  echo "(re-run scripts/vm/fetch_data.sh to resume: finished items are skipped)"
  exit 1
fi
if [ "$DRY_RUN" = 1 ]; then echo "DRY RUN: nothing was downloaded or written (log $OUT/fetch_log.txt)"; exit 0; fi
echo "DATA READY (log $OUT/fetch_log.txt)"
