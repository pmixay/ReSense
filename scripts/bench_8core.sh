#!/usr/bin/env bash
# One-command bench kit for the team's 8-core machine: captain action 7, criteria C7 / C8 in
# docs/CAPTAIN.md. The organizers' stand (i7-9700E) is not available to teams before the upload
# (organizers, 25.09), so this machine stands in for it.
#
#   scripts/bench_8core.sh [<doubleT_obstacle bag> [<roundT_doubleT bag>]]    # default: $RESENSE_DATA/<name>
#   RESENSE_DATA=/data/for_hackathon RESENSE_CACHE=/data/cache scripts/bench_8core.sh
#   OFFLINE_ONLY=1 RESENSE_CACHE=/data/cache scripts/bench_8core.sh          # host timing only: no Docker, no bags
#
# Everything goes to docs/evidence/bench_<YYYY-MM-DD>/ (a new _2, _3 ... folder if it exists):
#   system.txt, facts.txt  lscpu, nproc, RAM, kernel, CPU governor, UDP buffer limits, docker version / info,
#                          python / numpy, git commit; the image's kernel path
#   build/                 scripts/build.sh, timed (SKIP_BUILD=1 reuses resense:latest)
#   dry_<bag>_<kernels>/   scripts/dry_run.sh (reusing the image) with the node on the native kernels and on
#                          numpy (RESENSE_NATIVE=0): doubleT_obstacle with the SUBMISSION criteria,
#                          roundT_doubleT with --expect-clear --max-alarm-frames 2
#   ct_<image|stock>/      scripts/console_test.sh roundT_doubleT then doubleT_obstacle into one node, the
#                          player as uid 1000 with the image's Fast DDS profile and with stock Fast DDS
#                          (PLAYER_DDS=stock: the organizers' console)
#                          each Docker run: run.txt (output and check), status.jsonl.gz, node_log.txt, and
#                          docker_stats.tsv (docker stats every 2 s: CPU % of one core, memory)
#   offline/               host python on the frame cache, RESENSE_NATIVE=1 and =0, single-threaded BLAS:
#                          scripts/bench_node_path.py (decode + detect, as the node) and `resense bench`
#                          (per stage), with the peak RSS; the cache is $RESENSE_CACHE/<bag> or, when
#                          missing, made from the bag by scripts/cache_frames.py into out/bench_cache/
#   runs.tsv, summary.txt, summary.json   scripts/bench_summary.py: frames, fps, latency mean / p95 / max,
#                          dropped frames, CPU %, memory, kernel path per run
#
# Environment: RESENSE_DATA (/data/for_hackathon), RESENSE_CACHE (/data/cache), BENCH_OUT (the folder),
#   SKIP_BUILD=1, OFFLINE_ONLY=1 (no Docker part), SKIP_OFFLINE=1 (no host part), NODE_KERNELS ("native
#   numpy"), CONSOLE_MODES ("image stock"), PLAYER_USER (1000:1000), RATE (1.0, dry runs), BENCH_LIMIT
#   (frames per offline run), BENCH_CPU (taskset CPU list for the offline runs), PYTHON (python3).
# Exit: 0 every run passed; 1 a run or check failed (all numbers are still recorded); 2 a recording or
#   frame cache is missing; 3 no Docker daemon; 4 the host python lacks numpy / scipy / scikit-learn / pyyaml.
# Takes ~10-25 min, most of it the build. Keep the machine otherwise idle; the bags must be readable by
# uid 1000 (the console-test player). Commit the folder as it is:
#   git add docs/evidence/bench_<date>   (no *.log / *.jsonl inside, so .gitignore does not hide anything)
set -uo pipefail
cd "$(dirname "$0")/.." || exit 2
ROOT="$(pwd)"
# shellcheck source=scripts/require_docker.sh
. "$ROOT/scripts/require_docker.sh"

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  sed -n '2,37p' "$0"
  exit 0
fi

PY="${PYTHON:-python3}"
RESENSE_DATA="${RESENSE_DATA:-/data/for_hackathon}"
RESENSE_CACHE="${RESENSE_CACHE:-/data/cache}"
OFFLINE_ONLY="${OFFLINE_ONLY:-0}"
SKIP_OFFLINE="${SKIP_OFFLINE:-0}"
SKIP_BUILD="${SKIP_BUILD:-0}"
BENCH_LIMIT="${BENCH_LIMIT:-}"
BENCH_CPU="${BENCH_CPU:-}"
PLAYER_USER="${PLAYER_USER:-1000:1000}"
NODE_KERNELS="${NODE_KERNELS:-native numpy}"
CONSOLE_MODES="${CONSOLE_MODES:-image stock}"
BAG_OBS="${1:-$RESENSE_DATA/doubleT_obstacle}"
BAG_CLR="${2:-$RESENSE_DATA/roundT_doubleT}"
NAME_OBS="$(basename "$BAG_OBS")"
NAME_CLR="$(basename "$BAG_CLR")"

die() { local code="$1"; shift; echo "ERROR: $*" >&2; exit "$code"; }
is_bag() { [ -d "$1" ] && [ -f "$1/metadata.yaml" ]; }
has_npy() { compgen -G "$1/*.npy" >/dev/null 2>&1; }
pyenv() { env PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 "$@"; }

# ---- preflight: fail fast, before anything is built or written ----------------------------------
if [ "$OFFLINE_ONLY" = 1 ] && [ "$SKIP_OFFLINE" = 1 ]; then
  die 2 "OFFLINE_ONLY=1 and SKIP_OFFLINE=1 leave nothing to run"
fi
for kern in $NODE_KERNELS; do
  case "$kern" in native|numpy) ;; *) die 2 "NODE_KERNELS takes native and/or numpy, not '$kern'" ;; esac
done
for mode in $CONSOLE_MODES; do
  case "$mode" in image|stock) ;; *) die 2 "CONSOLE_MODES takes image and/or stock, not '$mode'" ;; esac
done
if [ "$OFFLINE_ONLY" != 1 ]; then
  for b in "$BAG_OBS" "$BAG_CLR"; do
    is_bag "$b" || die 2 "$b is not a ROS 2 bag directory (no metadata.yaml). Give the two recordings as arguments
       (doubleT_obstacle, then roundT_doubleT) or set RESENSE_DATA to their directory (now: $RESENSE_DATA)."
  done
  [ "$(cd "$(dirname "$BAG_OBS")" && pwd)" = "$(cd "$(dirname "$BAG_CLR")" && pwd)" ] \
    || die 2 "scripts/console_test.sh plays both recordings from one directory: put $NAME_OBS and $NAME_CLR side by side"
  [ "$NAME_OBS" = doubleT_obstacle ] || echo "WARNING: first recording is $NAME_OBS; the criteria are those of doubleT_obstacle" >&2
  [ "$NAME_CLR" = roundT_doubleT ] || echo "WARNING: second recording is $NAME_CLR; the criteria are those of roundT_doubleT" >&2
  if [ -n "$(find "$BAG_OBS" "$BAG_CLR" \( -type f ! -perm -o=r \) -o \( -type d ! -perm -o=rx \) 2>/dev/null | head -n 1)" ]; then
    echo "WARNING: some bag files are not world-readable; the console test plays them as uid ${PLAYER_USER%%:*}" \
         "(chmod -R a+rX $(dirname "$BAG_OBS"))" >&2
  fi
fi
CACHE_OBS=""; CACHE_CLR=""
if [ "$SKIP_OFFLINE" != 1 ]; then
  pyenv "$PY" -c "import numpy, scipy, sklearn, yaml" 2>/dev/null \
    || die 4 "the host $PY lacks numpy / scipy / scikit-learn / pyyaml for the offline bench: pip install -e \".[dev]\", or SKIP_OFFLINE=1"
  for which in OBS CLR; do
    if [ "$which" = OBS ]; then bag="$BAG_OBS"; name="$NAME_OBS"; else bag="$BAG_CLR"; name="$NAME_CLR"; fi
    if has_npy "$RESENSE_CACHE/$name"; then
      src="$RESENSE_CACHE/$name"
    elif has_npy "$ROOT/out/bench_cache/$name"; then
      src="$ROOT/out/bench_cache/$name"
    elif is_bag "$bag" && pyenv "$PY" -c "import rosbags" 2>/dev/null; then
      src="make"
    else
      die 2 "no frame cache for $name: neither $RESENSE_CACHE/$name/*.npy nor the bag with the rosbags package
       (to make one). Set RESENSE_CACHE, pip install rosbags, or SKIP_OFFLINE=1."
    fi
    if [ "$which" = OBS ]; then CACHE_OBS="$src"; else CACHE_CLR="$src"; fi
  done
fi
if [ "$OFFLINE_ONLY" != 1 ]; then
  require_docker_daemon || exit 3
fi

# ---- the evidence folder -----------------------------------------------------------------------
EV="${BENCH_OUT:-docs/evidence/bench_$(date +%F)}"
if [ -e "$EV" ] && [ -n "$(ls -A "$EV" 2>/dev/null)" ]; then
  i=2
  while [ -e "${EV}_$i" ]; do i=$((i + 1)); done
  EV="${EV}_$i"
fi
mkdir -p "$EV/offline" || die 2 "cannot create $EV"
EV="$(cd "$EV" && pwd)"
printf 'name\tkind\tkernels\texit\twall_s\tbags\tnote\n' > "$EV/runs.tsv"
FAILED=()
record() {   # <name> <kind> <kernels> <exit> <wall s> <bags csv> [note]
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$4" "$5" "$6" "${7:-}" >> "$EV/runs.tsv"
  [ "$4" = 0 ] || FAILED+=("$1 (exit $4)")
}
SAMPLER=""
on_exit() {
  if [ -n "$SAMPLER" ]; then kill "$SAMPLER" 2>/dev/null; fi
  if [ "$OFFLINE_ONLY" != 1 ]; then docker rm -f resense_bench_dry >/dev/null 2>&1 || true; fi
}
trap on_exit EXIT
echo "== ReSense bench kit -> $EV"

# ---- 1. the machine ----------------------------------------------------------------------------
lscpu_field() { LC_ALL=C lscpu 2>/dev/null | sed -n "s/^$1:[[:space:]]*//p" | head -n 1; }
CORES_PER_SOCKET="$(lscpu_field 'Core(s) per socket')"
SOCKETS="$(lscpu_field 'Socket(s)')"
fact() {   # <key> <command ...>: key=<first output line of the command, or n/a>
  local v
  v="$("${@:2}" 2>/dev/null | head -n 1)"
  echo "$1=${v:-n/a}"
}
{
  fact date date -Is
  fact host hostname
  fact commit git rev-parse --short HEAD
  fact describe git describe --always --dirty --tags
  if [ -n "$(git status --porcelain --untracked-files=no 2>/dev/null)" ]; then echo "dirty=1"; else echo "dirty=0"; fi
  fact cpu_model lscpu_field 'Model name'
  fact nproc nproc
  echo "sockets=${SOCKETS:-?}"
  if [[ "$CORES_PER_SOCKET" =~ ^[0-9]+$ && "$SOCKETS" =~ ^[0-9]+$ ]]; then
    echo "cores=$(( CORES_PER_SOCKET * SOCKETS ))"
  else
    echo "cores=?"
  fi
  fact threads_per_core lscpu_field 'Thread(s) per core'
  # shellcheck disable=SC2016  # awk program
  fact ram_gib awk '/^MemTotal/ {printf "%.1f\n", $2 / 1048576}' /proc/meminfo
  fact governor cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
  fact docker docker version --format '{{.Server.Version}}'
  fact python "$PY" -c 'import platform; print(platform.python_version())'
  fact numpy pyenv "$PY" -c 'import numpy; print(numpy.__version__)'
  echo "offline_only=$OFFLINE_ONLY"
  echo "bench_limit=${BENCH_LIMIT:-all}"
} > "$EV/facts.txt"
{
  echo "## date";            date -Is
  echo "## uname -a";        uname -a
  echo "## os-release";      cat /etc/os-release 2>/dev/null
  echo "## lscpu";           lscpu 2>&1
  echo "## nproc";           nproc
  echo "## free -m";         free -m 2>&1
  echo "## /proc/meminfo (head)"; head -n 5 /proc/meminfo
  echo "## uptime (load before the runs)"; uptime
  echo "## cpufreq governor / boost"
  cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor 2>/dev/null | sort | uniq -c
  cat /sys/devices/system/cpu/cpufreq/boost /sys/devices/system/cpu/intel_pstate/no_turbo 2>/dev/null
  echo "## UDP buffer limits (DDS; the image asks for 8 MB)"
  sysctl net.core.rmem_max net.core.wmem_max net.core.rmem_default net.core.wmem_default 2>&1
  echo "## /dev/shm (and Fast DDS files left in it: root-owned ones are what a uid-1000 client cannot open)"
  df -h /dev/shm 2>&1
  find /dev/shm -maxdepth 1 \( -name '*fastrtps*' -o -name '*fastdds*' \) -printf '%u %m %f\n' 2>/dev/null | head -n 20
  echo "## docker version";  docker version 2>&1 || true
  echo "## docker info";     docker info 2>&1 || true
  echo "## git";             git log -1 --format='%H %cI %s' 2>&1; git status --short --untracked-files=no 2>&1
  echo "## host python";     pyenv "$PY" -c 'import sys, numpy, scipy, sklearn; print(sys.version); print("numpy", numpy.__version__, "scipy", scipy.__version__, "scikit-learn", sklearn.__version__)' 2>&1
} > "$EV/system.txt" 2>&1
echo "   $(sed -n 's/^cpu_model=//p' "$EV/facts.txt"); $(nproc) CPUs; $(sed -n 's/^ram_gib=//p' "$EV/facts.txt") GiB; docker $(sed -n 's/^docker=//p' "$EV/facts.txt")"

# docker stats of the running resense_* containers every 2 s: epoch, name, CPU % (of one core), memory
sample_stats() {
  local out="$1" t0 names
  while :; do
    t0="$(date +%s.%N)"
    names="$(docker ps --filter name=resense_ --format '{{.Names}}' 2>/dev/null | tr '\n' ' ')"
    if [ -n "${names// /}" ]; then
      # shellcheck disable=SC2086  # one argument per container name
      docker stats --no-stream --format '{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}' $names 2>/dev/null \
        | sed "s/^/${t0%.*}\t/" >> "$out"
    fi
    sleep "$(awk -v a="$t0" -v b="$(date +%s.%N)" 'BEGIN { d = 2 - (b - a); print (d > 0.05 ? d : 0.05) }')"
  done
}

run_docker() {   # <name> <kind> <kernels> <bags csv> <command ...>: one Docker run with docker stats
  local name="$1" kind="$2" kern="$3" bags="$4"; shift 4
  local dir="$EV/$name" t0 rc f
  mkdir -p "$dir"
  echo
  echo "== [$name] $*"
  docker rm -f resense_bench_dry >/dev/null 2>&1 || true
  sample_stats "$dir/docker_stats.tsv" &
  SAMPLER=$!
  t0=$(date +%s)
  env OUT="$dir" "$@" 2>&1 | tee "$dir/run.txt"
  rc=${PIPESTATUS[0]}
  kill "$SAMPLER" 2>/dev/null; wait "$SAMPLER" 2>/dev/null; SAMPLER=""
  [ -f "$dir/status.jsonl" ] && gzip -f "$dir/status.jsonl"
  for f in "$dir"/*.log; do [ -e "$f" ] && mv -f "$f" "${f%.log}_log.txt"; done
  record "$name" "$kind" "$kern" "$rc" "$(( $(date +%s) - t0 ))" "$bags"
}

# ---- 2.-5. the Docker chain --------------------------------------------------------------------
if [ "$OFFLINE_ONLY" != 1 ]; then
  mkdir -p "$EV/build"
  t0=$(date +%s)
  if [ "$SKIP_BUILD" = 1 ]; then
    echo "SKIP_BUILD=1: reusing resense:latest" > "$EV/build/run.txt"
    record build build - 0 0 "" "SKIP_BUILD=1, image reused"
  else
    echo
    echo "== [build] scripts/build.sh"
    scripts/build.sh 2>&1 | tee "$EV/build/run.txt"
    rc=${PIPESTATUS[0]}
    record build build - "$rc" "$(( $(date +%s) - t0 ))" "" "scripts/build.sh (docker layer cache as found)"
  fi
  if docker image inspect resense:latest >/dev/null 2>&1; then
    {
      echo "image_id=$(docker image inspect resense:latest --format '{{.Id}}' | cut -c8-19)"
      echo "image_size_mb=$(( $(docker image inspect resense:latest --format '{{.Size}}') / 1000000 ))"
      # -w /: from /opt/resense python would import the source tree, which has no compiled kernels
      echo "image_kernels=$(docker run --rm -w / resense:latest python3 -c 'import resense._native as n; print(n.status())' 2>/dev/null | tail -n 1)"
    } >> "$EV/facts.txt"
    for kern in $NODE_KERNELS; do
      nat=1; [ "$kern" = numpy ] && nat=0
      run_docker "dry_obstacle_$kern" dry "$kern" "$BAG_OBS" \
        env SKIP_BUILD=1 DOCKER_ARGS="--name resense_bench_dry -e RESENSE_NATIVE=$nat" scripts/dry_run.sh "$BAG_OBS"
      run_docker "dry_clear_$kern" dry "$kern" "$BAG_CLR" \
        env SKIP_BUILD=1 DOCKER_ARGS="--name resense_bench_dry -e RESENSE_NATIVE=$nat" scripts/dry_run.sh "$BAG_CLR" \
        --expect-clear --max-alarm-frames 2
    done
    for mode in $CONSOLE_MODES; do
      run_docker "ct_$mode" ct native "$BAG_CLR,$BAG_OBS" \
        env PLAYER_DDS="$mode" PLAYER_USER="$PLAYER_USER" scripts/console_test.sh "$BAG_CLR" "$BAG_OBS" -- \
        --expect-obstacle --obstacle-in 2 --expect-inputs 2 --min-frames 20 --max-p95-latency 1000 --max-dropped 100000
    done
  else
    echo "ERROR: no resense:latest image (the build failed): the Docker runs are skipped" >&2
    FAILED+=("docker runs skipped: no image")
  fi
fi

# ---- 6. offline, host python, native and numpy -----------------------------------------------------
# shellcheck disable=SC2016  # python source
PEAK_RSS='import resource, subprocess, sys
rc = subprocess.call(sys.argv[1:])
print(f"peak RSS {resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024:.0f} MB", flush=True)
sys.exit(rc)'
TASKSET=()
if [ -n "$BENCH_CPU" ] && command -v taskset >/dev/null 2>&1; then TASKSET=(taskset -c "$BENCH_CPU"); fi
LIMIT=()
[ -n "$BENCH_LIMIT" ] && LIMIT=(--limit "$BENCH_LIMIT")

run_offline() {   # <name> <kind> <kernels> <cache dir> <command ...>
  local name="$1" kind="$2" kern="$3" src="$4"; shift 4
  local out="$EV/offline/$name.txt" nat=1 t0 rc
  [ "$kern" = numpy ] && nat=0
  echo
  echo "== [$name] RESENSE_NATIVE=$nat $*"
  t0=$(date +%s)
  {
    echo "\$ RESENSE_NATIVE=$nat ${TASKSET[*]:-} $*"
    pyenv RESENSE_NATIVE="$nat" "$PY" -c "from resense import _native; print('kernels:', _native.status())"
    pyenv RESENSE_NATIVE="$nat" ${TASKSET[@]+"${TASKSET[@]}"} "$PY" -c "$PEAK_RSS" "$@"
  } 2>&1 | tee "$out"
  rc=${PIPESTATUS[0]}
  record "$name" "$kind" "$kern" "$rc" "$(( $(date +%s) - t0 ))" "$src"
}

if [ "$SKIP_OFFLINE" != 1 ]; then
  if ! pyenv "$PY" -c "import sys; from resense import _native; sys.exit(0 if _native.AVAILABLE else 1)" 2>/dev/null; then
    echo "== building the native kernels in place for the host (scripts/build_native.sh)"
    scripts/build_native.sh > "$EV/offline/build_native.txt" 2>&1 \
      || echo "WARNING: scripts/build_native.sh failed ($EV/offline/build_native.txt): the host runs numpy only" >&2
  fi
  for which in OBS CLR; do
    if [ "$which" = OBS ]; then bag="$BAG_OBS"; name="$NAME_OBS"; src="$CACHE_OBS"
    else bag="$BAG_CLR"; name="$NAME_CLR"; src="$CACHE_CLR"; fi
    if [ "$src" = make ]; then
      src="$ROOT/out/bench_cache/$name"
      echo "== caching $name into $src (scripts/cache_frames.py)"
      pyenv "$PY" scripts/cache_frames.py "$bag" "$src" --every 1 --int16 --stamps > "$EV/offline/cache_$name.txt" 2>&1 \
        || { echo "ERROR: caching $name failed ($EV/offline/cache_$name.txt)" >&2; FAILED+=("cache $name"); continue; }
    fi
    for kern in native numpy; do
      run_offline "node_${name}_$kern" offline_node "$kern" "$src" \
        "$PY" scripts/bench_node_path.py --npy "$src" ${LIMIT[@]+"${LIMIT[@]}"}
    done
    for kern in native numpy; do
      run_offline "stages_${name}_$kern" offline_stages "$kern" "$src" \
        "$PY" -m resense.cli bench --npy "$src" ${LIMIT[@]+"${LIMIT[@]}"}
    done
  done
fi

# ---- 7. summary --------------------------------------------------------------------------------
echo "## uptime (load after the runs)" >> "$EV/system.txt"; uptime >> "$EV/system.txt"
echo
echo "== summary ($EV/summary.txt)"
"$PY" scripts/bench_summary.py "$EV" --write || FAILED+=("bench_summary.py")
if [ ${#FAILED[@]} -gt 0 ]; then
  echo "NOT PASSED: ${FAILED[*]}"
  echo "(the numbers are recorded all the same; commit $EV as it is)"
  exit 1
fi
echo "ALL PASSED; commit $EV as it is"
