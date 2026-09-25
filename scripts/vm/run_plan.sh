#!/usr/bin/env bash
# The runs the team cannot do in the dev sandbox or on the organizers' stand, as one command on
# the temporary VM (after scripts/vm/setup_vm.sh and scripts/vm/fetch_data.sh; AGENT_BRIEF.md):
#
#   scripts/vm/run_plan.sh status                  what is installed, fetched, built, measured
#   scripts/vm/run_plan.sh bench                   8-core bench, native and numpy (CAPTAIN action 7, C8)
#   scripts/vm/run_plan.sh dryrun                  clean build + dry_run.sh on the ORIGINAL doubleT_obstacle and
#                                                  roundT_doubleT + console_test.sh + a host `ros2 bag play`
#                                                  with stock Fast DDS / CycloneDDS (action 15, C7, C4)
#   scripts/vm/run_plan.sh gate [--ref R]          regression gate over every cache incl. the ride (action 11, P3/P4
#                                                  go / no-go); --ref runs a candidate branch in its own worktree
#   scripts/vm/run_plan.sh export [--ref TAG]      image archive + sha256 (actions 14b / 16); --ref: from a clean
#                                                  clone of that tag, VERSION defaults to the tag
#   scripts/vm/run_plan.sh offline [--minutes N]   the offline rehearsal (C25, action 15): outbound internet blocked
#                                                  (SSH, loopback, DDS multicast kept), restored automatically after
#                                                  N minutes (default 30) by a systemd timer, and at the end
#   scripts/vm/run_plan.sh restore-network         undo the offline block now (also: sudo sh /var/lib/resense-offline/restore.sh)
#   scripts/vm/run_plan.sh all                     dryrun, bench, gate, export, offline, collect
#   scripts/vm/run_plan.sh collect [--to-repo]     ~/resense_results_<date>.tar.gz with summary.md; --to-repo also
#                                                  copies each run to docs/evidence/<name>_<date>/ (not committed)
#
# Every subcommand writes ~/resense_results/<date>/<subcommand>/: run_log.txt (everything printed),
# meta.txt (commit, machine), steps.tsv, result.txt (PASS / FAIL per step), highlights.txt, and one
# <step>.txt per step. A second run on the same day moves the first to <subcommand>_<HHMMSS>/.
# Uses scripts/bench_8core.sh and scripts/regression_gate.py when the branch has them, otherwise
# falls back to dry_run.sh / console_test.sh / bench_node_path.py / eval_real.py / score_fake_objects.py
# and says so in result.txt.
#
# Options: --ref R, --version V (export), --minutes N, --image-tar F, --allow-host H (offline: keep
#   DNS and HTTPS to H open, e.g. api.anthropic.com for an agent session; recorded in the evidence),
#   --date YYYY-MM-DD, --to-repo (collect), -n / --dry-run (print the commands), -h / --help.
# Environment: DATA_DIR (/data), CACHE_DIR, VENV, RESULTS_ROOT, DIST_DIR, GATE_JOBS, GATE_PATHS
#   ("native", or "native numpy"), GATE_ARGS (extra regression_gate.py arguments), GATE_BASELINE,
#   RIDE_REPLAY (1 = also play the whole 20-minute ride in dryrun when its bag is kept), KEEP_IMAGE=1
#   (offline: do not remove the resense images before loading the archive), OFFLINE_CONFIRM=0 (no
#   "open a second SSH session" question), GZIP_LEVEL (export).
# Exit: 0 PASS; 1 a step failed (result.txt says which); 2 bad arguments or missing data / archive;
#   3 no Docker / no sudo.
set -Eeuo pipefail
SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
ORIG_ARGS=("$@")
# shellcheck source=scripts/vm/lib.sh
. "$(dirname "$SELF")/lib.sh"
# shellcheck disable=SC2329  # the ERR trap calls it
on_err() { warn "run_plan.sh: command failed at line $1: $2"; }
trap 'on_err "$LINENO" "$BASH_COMMAND"' ERR

usage() { header_help "$SELF"; }
SUB="${1:-}"
[ $# -gt 0 ] && shift
REF=""; VERSION_ARG=""; MINUTES="${OFFLINE_MINUTES:-30}"; IMAGE_TAR_ARG="${IMAGE_TAR:-}"
ALLOW_HOSTS="${OFFLINE_ALLOW:-}"; COLLECT_DATE=""; TO_REPO=0
while [ $# -gt 0 ]; do
  case "$1" in
    --ref) REF="${2:?--ref needs a value}"; shift 2 ;;
    --version) VERSION_ARG="${2:?}"; shift 2 ;;
    --minutes) MINUTES="${2:?}"; shift 2 ;;
    --image-tar) IMAGE_TAR_ARG="${2:?}"; shift 2 ;;
    --allow-host) ALLOW_HOSTS="${ALLOW_HOSTS:+$ALLOW_HOSTS }${2:?}"; shift 2 ;;
    --date) COLLECT_DATE="${2:?}"; shift 2 ;;
    --to-repo) TO_REPO=1; shift ;;
    -n|--dry-run) DRY_RUN=1; export DRY_RUN; shift ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; die 2 "unknown argument: $1" ;;
  esac
done
case "$SUB" in
  status|bench|dryrun|gate|export|offline|restore-network|all|collect) ;;
  -h|--help|help|"") usage; exit 0 ;;
  *) usage >&2; die 2 "unknown subcommand: $SUB" ;;
esac
[[ "$MINUTES" =~ ^[0-9]+$ ]] && [ "$MINUTES" -ge 5 ] && [ "$MINUTES" -le 180 ] || die 2 "--minutes takes 5..180"

[ -f "$REPO_DIR/pyproject.toml" ] || die 2 "no ReSense checkout at $REPO_DIR (REPO_DIR, or run scripts/vm/setup_vm.sh)"
cd "$REPO_DIR"
PY="$(venv_python)"
[ -x "$PY" ] || PY="$(command -v python3)"
BAGS="$DATA_DIR/for_hackathon"
BAG_OBS="$BAGS/doubleT_obstacle"
BAG_CLR="$BAGS/roundT_doubleT"
[ -n "$ROS_MODE" ] || { if has_host_ros; then ROS_MODE=host; else ROS_MODE=docker-only; fi; }
CT_CHECK=(--expect-obstacle --obstacle-in 2 --expect-inputs 2 --min-frames 20 --max-p95-latency 1000 --max-dropped 100000)
detect_resources

# ---- preconditions ----------------------------------------------------------------------------------
docker_version() {
  local v
  v="$(docker version --format '{{.Server.Version}}' 2>/dev/null | tr -d '[:space:]' || true)"
  printf '%s\n' "${v:-not reachable}"
}
ensure_docker() {   # a working docker CLI for this user; re-exec under `sg docker` right after setup
  [ "$DRY_RUN" = 1 ] && return 0
  have docker || die 3 "Docker is not installed: run scripts/vm/setup_vm.sh"
  docker info >/dev/null 2>&1 && return 0
  if [ -z "${RESENSE_SG:-}" ] && getent group docker | cut -d: -f4 | tr ',' '\n' | grep -qx "$(id -un)"; then
    export RESENSE_SG=1
    log "re-running under 'sg docker' (the docker group is not active in this login yet)"
    exec sg docker -c "$(printf '%q ' "$SELF" "$SUB" "${ORIG_ARGS[@]:1}")"
  fi
  die 3 "cannot reach the Docker daemon ('docker info' failed): sudo systemctl start docker; is $(id -un) in the docker group?"
}
ensure_sudo() {
  [ "$DRY_RUN" = 1 ] && return 0
  [ "$(id -u)" -eq 0 ] || sudo -n true 2>/dev/null || die 3 "this step needs passwordless sudo (iptables)"
}
need_bags() {
  local b
  for b in "$BAG_OBS" "$BAG_CLR"; do
    bag_ok "$b" || { [ "$DRY_RUN" = 1 ] && { warn "(dry run) $b missing"; continue; }; \
      die 2 "$b is not a complete ROS 2 bag: run scripts/vm/fetch_data.sh (it keeps doubleT_obstacle and roundT_doubleT)"; }
  done
}
need_image() {
  [ "$DRY_RUN" = 1 ] && return 0
  docker image inspect resense:latest >/dev/null 2>&1
}

# ---- results, steps ------------------------------------------------------------------------------
RES=""; T_BEGIN=0
begin() {
  RES="$(results_dir "$SUB")"
  start_log "$RES/run_log.txt"
  T_BEGIN=$(date +%s)
  : > "$RES/steps.tsv"
  rm -f "$RES/notes.txt"
  {
    echo "subcommand: $SUB"
    echo "command:    $SELF $SUB ${ORIG_ARGS[*]:1}"
    echo "date:       $(date -Is)"
    git_facts
    print_resources
    echo "docker:     $(docker_version)"
    echo "ros mode:   $ROS_MODE (host ROS 2 Humble: $(has_host_ros && echo yes || echo no))"
    echo "kit:        scripts/bench_8core.sh $([ -x scripts/bench_8core.sh ] && echo present || echo absent);" \
         "scripts/regression_gate.py $([ -f scripts/regression_gate.py ] && echo present || echo absent)"
    echo "dry run:    $DRY_RUN"
  } > "$RES/meta.txt"
  log "== run_plan $SUB -> $RES"
  sed 's/^/   /' "$RES/meta.txt"
}
note() { log "NOTE: $*"; echo "$*" >> "$RES/notes.txt"; }
record_step() { printf '%s\t%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$4" "${5:-}" >> "$RES/steps.tsv"; }
step_skip() { log "[$1] SKIPPED: $2"; record_step "$1" - SKIPPED 0 "$2"; }
LAST_RC=0
step_run() {   # step_run <name> <command...>: output to <name>.txt and run_log.txt; never aborts
  local name="$1" t0 rc; shift
  t0=$(date +%s)
  hr; log "== [$SUB/$name] $(printf '%q ' "$@")"
  if [ "$DRY_RUN" = 1 ]; then
    run "$@"; rc=0
  else
    trap - ERR                     # a failing step is recorded below, not reported as a stop
    set +e
    "$@" 2>&1 | tee "$RES/$name.txt"
    rc=${PIPESTATUS[0]}
    set -e
    trap 'on_err "$LINENO" "$BASH_COMMAND"' ERR
  fi
  LAST_RC=$rc
  if [ "$DRY_RUN" = 1 ]; then record_step "$name" - DRY 0
  elif [ "$rc" = 0 ]; then record_step "$name" 0 PASS $(( $(date +%s) - t0 ))
  else record_step "$name" "$rc" FAIL $(( $(date +%s) - t0 )); fi
  log "[$name] exit $rc"
  return 0
}
HIGHLIGHT_RE='^(status messages|alarm frames|obstacle distance|latency decode|detector stage|dropped input|fps \(last|recordings seen|start of the input|PASS|FAIL|NOT PASSED|ALL PASSED|decisions seen|  decode \+ detect|   (archive|image|sha256|tags|commit):|== summary|five empty bags|gate:|ride cache|(doubleT|roundT|squareT|new_data)[A-Za-z_0-9]* +[0-9]+ |   labelled:|\| [0-9]+ \| `|Background|GATE (PASS|FAIL)|note: (ride|set F))'
finish() {
  local overall=PASS nfail f
  nfail="$(awk -F'\t' '$3 == "FAIL"' "$RES/steps.tsv" | wc -l | tr -d ' ')"
  [ "$nfail" = 0 ] || overall=FAIL
  [ -s "$RES/steps.tsv" ] || overall="NOTHING RUN"
  [ "$DRY_RUN" = 1 ] && overall="DRY RUN"
  {
    for f in "$RES"/*.txt; do
      case "$(basename "$f")" in run_log.txt|meta.txt|result.txt|highlights.txt|notes.txt) continue ;; esac
      if grep -Eq "$HIGHLIGHT_RE" "$f" 2>/dev/null; then
        echo "## $(basename "$f" .txt)"; grep -E "$HIGHLIGHT_RE" "$f" | head -n 40
      fi
    done
  } > "$RES/highlights.txt"
  hr
  {
    echo "$SUB: $overall  ($(date -Is), $(( $(date +%s) - T_BEGIN )) s, commit $(git rev-parse --short HEAD 2>/dev/null || echo '?'), $NPROC vCPU)"
    awk -F'\t' '{ printf "  %-36s %-7s exit %-4s %6s s  %s\n", $1, $3, $2, $4, $5 }' "$RES/steps.tsv"
    if [ -f "$RES/notes.txt" ]; then sed 's/^/  note: /' "$RES/notes.txt"; fi
    echo "  results: $RES"
  } | tee "$RES/result.txt"
  if [ "$overall" = PASS ] || [ "$overall" = "DRY RUN" ]; then RC_FINAL=0; else RC_FINAL=1; fi
  return 0
}
RC_FINAL=0

# docker stats of the ReSense containers every 2 s: epoch, name, CPU % of one core, memory
SAMPLER=""
# shellcheck disable=SC2329  # used by with_stats / host_console, which step_run calls
stats_start() {
  [ "$DRY_RUN" = 1 ] && return 0
  (
    while :; do
      t="$(date +%s)"
      names="$(docker ps --filter ancestor=resense:latest --format '{{.Names}}' 2>/dev/null | tr '\n' ' ')"
      if [ -n "${names// /}" ]; then
        # shellcheck disable=SC2086  # one argument per container
        docker stats --no-stream --format '{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}' $names 2>/dev/null | sed "s/^/$t\t/" >> "$1"
      fi
      sleep 2
    done
  ) &
  SAMPLER=$!
}
# shellcheck disable=SC2329  # see stats_start
stats_stop() {
  if [ -n "$SAMPLER" ]; then kill "$SAMPLER" 2>/dev/null || true; wait "$SAMPLER" 2>/dev/null || true; SAMPLER=""; fi
}
# shellcheck disable=SC2329  # called through step_run "$@"
in_dir() {   # in_dir <dir> <command...>: relative paths in the scripts (labels/, docs/) resolve there
  local d="$1"; shift
  (cd "$d" && "$@")
}
# shellcheck disable=SC2329  # called through step_run "$@"
with_stats() {   # with_stats <stats file> <command...>
  local f="$1" rc; shift
  mkdir -p "$(dirname "$f")"
  stats_start "$f"
  set +e; "$@"; rc=$?; set -e
  stats_stop
  return "$rc"
}

# The organizers' console: the node container on its default command, `ros2 bag play` and
# `ros2 topic echo` from THIS host as this (normal) user with the stock RMW and no XML profile.
# shellcheck disable=SC2329  # called through step_run "$@"
host_console() {   # host_console <outdir> <rmw> <bag>... -- <check_dry_run.py args>
  local out="$1" rmw="$2" b; shift 2
  local bags=()
  while [ $# -gt 0 ] && [ "$1" != -- ]; do bags+=("$1"); shift; done
  [ "${1:-}" = -- ] && shift
  mkdir -p "$out"
  docker rm -f resense_vm_node >/dev/null 2>&1 || true
  docker run -d --name resense_vm_node --net=host --ipc=host resense:latest >/dev/null || return 3
  local ready=0 i
  for i in $(seq 1 60); do
    if docker logs resense_vm_node 2>&1 | grep -q "ReSense detector listening"; then ready=1; break; fi
    sleep 1
  done
  if [ "$ready" != 1 ]; then
    docker logs resense_vm_node > "$out/node_log.txt" 2>&1 || true
    docker rm -f resense_vm_node >/dev/null 2>&1 || true
    echo "FAIL: the node container was not ready within 60 s (node_log.txt)"; return 3
  fi
  stats_start "$out/docker_stats.tsv"
  local prc=0
  (
    set +e
    ros_env || { echo "no /opt/ros/humble"; exit 3; }
    unset FASTRTPS_DEFAULT_PROFILES_FILE FASTDDS_DEFAULT_PROFILES_FILE RMW_FASTRTPS_USE_QOS_FROM_XML
    export RMW_IMPLEMENTATION="$rmw"
    cd "$(mktemp -d)" || exit 3                  # no DEFAULT_FASTRTPS_PROFILES.xml can be picked up
    echo "player: $(id -un) (uid $(id -u)), RMW_IMPLEMENTATION=$rmw, no Fast DDS XML profile"
    ros2 topic echo /resense/status --field data > "$out/status.jsonl" 2>/dev/null & e1=$!
    ros2 topic echo /resense/decision --field data > "$out/decision.txt" 2>/dev/null & e2=$!
    ros2 topic echo /resense/nearest_distance --field data > "$out/nearest_distance.txt" 2>/dev/null & e3=$!
    sleep 4
    rc=0
    for b in "${bags[@]}"; do
      echo "$(date +%T) ros2 bag play $b --delay 3"
      timeout $(( $(bag_seconds "$b") + 180 )) ros2 bag play "$b" --delay 3 --disable-keyboard-controls \
        >> "$out/player_log.txt" 2>&1 || rc=$?
      sleep 5
    done
    sleep 3
    kill "$e1" "$e2" "$e3" 2>/dev/null
    wait 2>/dev/null
    exit "$rc"
  ) || prc=$?
  stats_stop
  docker logs resense_vm_node > "$out/node_log.txt" 2>&1 || true
  docker rm -f resense_vm_node >/dev/null 2>&1 || true
  echo "decisions seen: $(grep -v '^---$' "$out/decision.txt" 2>/dev/null | sort | uniq -c | tr -s ' \n' ' ')"
  local crc=0
  python3 scripts/check_dry_run.py "$out/status.jsonl" "$@" | tee "$out/check.txt" || crc=${PIPESTATUS[0]}
  if [ "$prc" != 0 ]; then echo "FAIL: ros2 bag play exited $prc (player_log.txt)"; return "$prc"; fi
  return "$crc"
}

# shellcheck disable=SC2329  # called through step_run "$@"
compare_metadata() {   # the bags are the organizers' originals: metadata.yaml as committed in docs/evidence
  local b n rc=0
  for b in "$BAG_OBS" "$BAG_CLR"; do
    n="$(basename "$b")"
    if cmp -s "$b/metadata.yaml" "docs/evidence/bag_metadata/${n}_metadata.yaml"; then
      echo "$n: metadata.yaml identical to docs/evidence/bag_metadata/${n}_metadata.yaml (original recording)"
    else
      echo "$n: metadata.yaml DIFFERS from docs/evidence/bag_metadata/${n}_metadata.yaml"; rc=1
    fi
    ls -l "$b"
  done
  return "$rc"
}

# ---- status ------------------------------------------------------------------------------------------
cmd_status() {
  print_resources
  git_facts
  echo "venv:      $PY ($("$PY" -c 'import numpy, rosbags; print("numpy", numpy.__version__, "+ rosbags")' 2>/dev/null || echo 'missing packages'))"
  echo "native:    $(PYTHONPATH="$REPO_DIR" "$PY" -c 'from resense import _native; print(_native.status())' 2>/dev/null || echo '?')"
  echo "docker:    $(docker_version); images:" \
       "$(docker images --format '{{.Repository}}:{{.Tag}} {{.Size}}' 2>/dev/null | grep -E '^resense:' | tr '\n' ' ' || true)"
  echo "ros:       $ROS_MODE"
  echo "kit:       bench_8core.sh $([ -x scripts/bench_8core.sh ] && echo yes || echo 'no (fallback)'), regression_gate.py $([ -f scripts/regression_gate.py ] && echo yes || echo 'no (fallback)')"
  local b
  for b in doubleT_obstacle roundT_doubleT doubleT_platform roundT_pressureGate_roundT roundT_squareT_pressureGate_squareT squareT_platform_squareT_switch; do
    printf '  %-40s bag %-4s cache %s\n' "$b" "$(bag_ok "$BAGS/$b" && echo yes || echo no)" "$(npy_count "$CACHE_DIR/$b")"
  done
  printf '  %-40s bag %-4s cache %s\n' cloud_with_fake_obj "$(bag_ok "$DATA_DIR/cloud_with_fake_obj" && echo yes || echo no)" "$(npy_count "$CACHE_DIR/cloud_with_fake_obj")"
  printf '  %-40s bag %-4s cache %s split files\n' new_data "$(bag_ok "$DATA_DIR/new_data" && echo yes || echo no)" \
    "$({ find "$CACHE_DIR/new_data" -maxdepth 1 -name '*_stamps.json' 2>/dev/null || true; } | wc -l | tr -d ' ')"
  echo "archives:  $(find "$DIST_DIR" "$REPO_DIR/dist" -maxdepth 1 -name 'resense-image-*.tar.gz' 2>/dev/null | tr '\n' ' ')"
  echo "offline:   $(if root_q iptables -w -C OUTPUT -j RESENSE_OFFLINE 2>/dev/null; then echo 'BLOCK ACTIVE (run_plan.sh restore-network)'; else echo 'no block'; fi)"
  echo "results ($RESULTS_ROOT/$RUN_DATE):"
  local r
  for r in "$RESULTS_ROOT/$RUN_DATE"/*/result.txt; do [ -f "$r" ] && echo "  $(head -n 1 "$r")"; done
  return 0
}

# ---- bench -------------------------------------------------------------------------------------------
cmd_bench() {
  ensure_docker; need_bags; begin
  if [ "$NPROC" -lt 8 ]; then note "$NPROC vCPU: not an 8-core analogue of the i7-9700E; the numbers are for this VM only"; fi
  if [ "${THREADS_PER_CORE:-1}" != 1 ]; then note "$NPROC vCPU = $CORES physical cores x $THREADS_PER_CORE threads (the i7-9700E: 8 cores, no hyper-threading)"; fi
  note "cpu steal before the runs: $(cpu_steal_pct) % (shared vCPUs make timing noisy above ~5 %)"
  if [ -x scripts/bench_8core.sh ]; then
    step_run bench_8core env RESENSE_DATA="$BAGS" RESENSE_CACHE="$CACHE_DIR" PYTHON="$PY" PATH="$VENV/bin:$PATH" \
      BENCH_OUT="$RES/bench_$RUN_DATE" scripts/bench_8core.sh "$BAG_OBS" "$BAG_CLR"
    [ -f "$RES/bench_$RUN_DATE/summary.txt" ] && cp "$RES/bench_$RUN_DATE/summary.txt" "$RES/bench_summary.txt"
  else
    note "scripts/bench_8core.sh is not on this branch: fallback (build, dry_run.sh with docker stats, bench_node_path.py and resense bench on the host)"
    (
      set +e +o pipefail
      echo "## lscpu"; lscpu; echo "## free -m"; free -m; echo "## uname -a"; uname -a
      echo "## governor"; cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor 2>/dev/null | sort | uniq -c
      echo "## UDP buffers"; sysctl net.core.rmem_max net.core.wmem_max
      echo "## docker info"; docker info
      exit 0
    ) > "$RES/system.txt" 2>&1
    step_run build scripts/build.sh
    step_run dry_obstacle_native with_stats "$RES/dry_obstacle_native/docker_stats.tsv" \
      env SKIP_BUILD=1 OUT="$RES/dry_obstacle_native" scripts/dry_run.sh "$BAG_OBS"
    step_run dry_clear_native with_stats "$RES/dry_clear_native/docker_stats.tsv" \
      env SKIP_BUILD=1 OUT="$RES/dry_clear_native" scripts/dry_run.sh "$BAG_CLR" --expect-clear --max-alarm-frames 2
    if grep -q DOCKER_ARGS scripts/dry_run.sh; then
      step_run dry_obstacle_numpy with_stats "$RES/dry_obstacle_numpy/docker_stats.tsv" \
        env SKIP_BUILD=1 DOCKER_ARGS="-e RESENSE_NATIVE=0" OUT="$RES/dry_obstacle_numpy" scripts/dry_run.sh "$BAG_OBS"
    else
      note "dry_run.sh here cannot pass RESENSE_NATIVE=0 into the node: the numpy path is measured on the host only"
    fi
    local name kern
    for name in doubleT_obstacle roundT_doubleT; do
      if [ "$(npy_count "$CACHE_DIR/$name")" = 0 ] && [ "$DRY_RUN" != 1 ]; then step_skip "host_$name" "no cache $CACHE_DIR/$name"; continue; fi
      for kern in 1 0; do
        step_run "node_path_${name}_$([ $kern = 1 ] && echo native || echo numpy)" \
          pyenv env RESENSE_NATIVE=$kern OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 "$PY" scripts/bench_node_path.py --npy "$CACHE_DIR/$name"
        step_run "stages_${name}_$([ $kern = 1 ] && echo native || echo numpy)" \
          pyenv env RESENSE_NATIVE=$kern OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 "$PY" -m resense.cli bench --npy "$CACHE_DIR/$name"
      done
    done
  fi
  finish
}

# ---- dryrun ------------------------------------------------------------------------------------------
cmd_dryrun() {
  ensure_docker; need_bags; begin
  step_run original_bags compare_metadata
  step_run dry_obstacle with_stats "$RES/dry_obstacle/docker_stats.tsv" \
    env SKIP_BUILD="${DRYRUN_SKIP_BUILD:-0}" OUT="$RES/dry_obstacle" scripts/dry_run.sh "$BAG_OBS"
  if ! need_image; then note "no resense:latest after the build: the other steps cannot run"; finish; return; fi
  step_run dry_clear with_stats "$RES/dry_clear/docker_stats.tsv" \
    env SKIP_BUILD=1 OUT="$RES/dry_clear" scripts/dry_run.sh "$BAG_CLR" --expect-clear --max-alarm-frames 2
  step_run console_image env OUT="$RES/console_image" scripts/console_test.sh "$BAG_CLR" "$BAG_OBS" -- "${CT_CHECK[@]}"
  if grep -q PLAYER_DDS scripts/console_test.sh; then
    step_run console_stock_dds env PLAYER_DDS=stock OUT="$RES/console_stock_dds" scripts/console_test.sh "$BAG_CLR" "$BAG_OBS" -- "${CT_CHECK[@]}"
  fi
  if [ "$ROS_MODE" = host ] && has_host_ros || [ "$DRY_RUN" = 1 ]; then
    step_run host_fastdds host_console "$RES/host_fastdds" rmw_fastrtps_cpp "$BAG_CLR" "$BAG_OBS" -- "${CT_CHECK[@]}"
    if [ -d /opt/ros/humble/share/rmw_cyclonedds_cpp ] || [ "$DRY_RUN" = 1 ]; then
      step_run host_cyclonedds host_console "$RES/host_cyclonedds" rmw_cyclonedds_cpp "$BAG_CLR" "$BAG_OBS" -- "${CT_CHECK[@]}"
    fi
  else
    step_skip host_console "no ROS 2 Humble on this host (Docker-only mode, e.g. Ubuntu 24.04): CAPTAIN C4 needs a 22.04 VM"
  fi
  if bag_ok "$DATA_DIR/new_data" && [ "${RIDE_REPLAY:-1}" = 1 ]; then
    if [ "$ROS_MODE" = host ]; then
      step_run ride_replay host_console "$RES/ride_replay" rmw_fastrtps_cpp "$DATA_DIR/new_data" -- \
        --min-frames 10000 --max-p95-latency 100 --max-dropped 100000
    else
      step_run ride_replay env OUT="$RES/ride_replay" scripts/console_test.sh "$DATA_DIR/new_data" -- \
        --min-frames 10000 --max-p95-latency 100 --max-dropped 100000
    fi
    note "ride_replay: every alarm on new_data is a false alarm (no obstacles in it); dropped frames include its recording holes"
  else
    step_skip ride_replay "the 20-minute bag is not kept on this disk (fetch_data.sh --ride keep needs ~90 GB)"
  fi
  finish
}

# ---- gate --------------------------------------------------------------------------------------------
gate_worktree() {   # a detached worktree of REF outside the checkout; prints its path
  local wt sha
  wt="$HOME/resense_ref/$(printf '%s' "$REF" | tr -c 'A-Za-z0-9._-' '_')"
  if ! sha="$(git rev-parse --verify -q "$REF^{commit}")"; then
    git fetch -q origin "$REF" >&2 || die 2 "cannot find $REF locally or on origin"
    sha="$(git rev-parse FETCH_HEAD)"
  fi
  if [ -d "$wt" ]; then
    git -C "$wt" checkout -q --detach "$sha" >&2
  else
    mkdir -p "$(dirname "$wt")"
    git worktree add -q --detach "$wt" "$sha" >&2
  fi
  if [ -x "$wt/scripts/build_native.sh" ]; then (cd "$wt" && PATH="$VENV/bin:$PATH" scripts/build_native.sh >&2) || warn "native build failed in $wt"; fi
  printf '%s\n' "$wt"
}
cmd_gate() {
  local root="$REPO_DIR" cached=0 b jobs baseline="" ride
  for b in doubleT_obstacle doubleT_platform roundT_doubleT roundT_pressureGate_roundT roundT_squareT_pressureGate_squareT squareT_platform_squareT_switch cloud_with_fake_obj; do
    if [ "$(npy_count "$CACHE_DIR/$b")" -gt 0 ]; then cached=$(( cached + 1 )); fi
  done
  if [ "$cached" -lt 7 ] && [ "$DRY_RUN" != 1 ]; then die 2 "only $cached of the 7 caches (six recordings + cloud_with_fake_obj) in $CACHE_DIR: run scripts/vm/fetch_data.sh"; fi
  "$PY" -c "import numpy, scipy, sklearn, yaml" 2>/dev/null || [ "$DRY_RUN" = 1 ] \
    || die 2 "$PY lacks numpy / scipy / scikit-learn / pyyaml: run scripts/vm/setup_vm.sh"
  begin
  ride="$({ find "$CACHE_DIR/new_data" -maxdepth 1 -name '*_stamps.json' 2>/dev/null || true; } | wc -l | tr -d ' ')"
  if [ "$ride" -ge 221 ]; then note "ride cached (221 split files): the gate covers all 13 759 real frames"
  else note "ride cache incomplete ($ride of 221 split files): the gate runs WITHOUT the full ride, which the go / no-go (action 11) needs"; fi
  jobs="${GATE_JOBS:-$(( RAM_MB / 2048 ))}"; [ "$jobs" -le "$NPROC" ] || jobs=$NPROC; [ "$jobs" -ge 1 ] || jobs=1
  if [ -n "$REF" ]; then
    if [ "$DRY_RUN" = 1 ]; then
      log "DRY: git worktree add --detach ~/resense_ref/<$REF> $REF; scripts/build_native.sh there"
    else
      root="$(gate_worktree)" || die 2 "could not prepare a worktree of $REF"
      note "candidate $REF at $(git -C "$root" rev-parse --short HEAD) in the worktree $root"
    fi
  fi
  local gate="$root/scripts/regression_gate.py"
  if [ ! -f "$gate" ] && [ -f "$REPO_DIR/scripts/regression_gate.py" ] && [ "$root" != "$REPO_DIR" ]; then
    cp "$REPO_DIR/scripts/regression_gate.py" "$gate"
    note "$REF has no regression_gate.py: the one of $(git rev-parse --short HEAD) was copied into its worktree"
  fi
  if [ -f "$gate" ]; then
    baseline="${GATE_BASELINE:-$(find "$REPO_DIR/docs/evidence/results" -maxdepth 1 -name 'regression_baseline_*.json' 2>/dev/null | sort | tail -n 1)}"
    [ -n "$baseline" ] || note "no committed regression_baseline_*.json: measured only, not compared"
    local path nat args
    for path in ${GATE_PATHS:-native}; do
      nat=1; [ "$path" = numpy ] && nat=0
      args=(--cache "$CACHE_DIR" --jobs "$jobs" --work "$RES/work_$path" --out "$RES/gate_$path.json")
      [ -n "$baseline" ] && args+=(--baseline "$baseline")
      # shellcheck disable=SC2206  # GATE_ARGS is a list of words by design
      [ -n "${GATE_ARGS:-}" ] && args+=(${GATE_ARGS})
      step_run "gate_$path" in_dir "$root" env PATH="$VENV/bin:$PATH" PYTHONPATH="$root" RESENSE_NATIVE=$nat \
        "$PY" "$gate" "${args[@]}"
    done
    note "regression_gate.py exit codes: 0 identical or better, 1 a gated metric worse, 2 missing data / failed set F"
  else
    note "scripts/regression_gate.py is not on this branch: fallback eval_real.py + score_fake_objects.py, NO baseline comparison (compare with EXPERIMENTS 'Current results' by hand)"
    step_run eval_real in_dir "$root" env PATH="$VENV/bin:$PATH" PYTHONPATH="$root" "$PY" "$root/scripts/eval_real.py" \
      --cache "$CACHE_DIR" --out "$RES/eval" --jobs "$jobs" --config "$root/configs/default.yaml"
    mkdir -p "$RES/set_o"
    step_run set_o_run in_dir "$root" env PATH="$VENV/bin:$PATH" PYTHONPATH="$root" "$PY" -m resense.cli run \
      --npy "$CACHE_DIR/cloud_with_fake_obj" --out "$RES/set_o/fake.jsonl" --quiet
    step_run set_o_score in_dir "$root" env PATH="$VENV/bin:$PATH" PYTHONPATH="$root" "$PY" "$root/scripts/score_fake_objects.py" \
      "$RES/set_o/fake.jsonl" --gt "$root/labels/cloud_with_fake_obj.json" --out "$RES/set_o/score.json"
  fi
  finish
}

# ---- export ------------------------------------------------------------------------------------------
cmd_export() {
  ensure_docker; begin
  local src="$REPO_DIR" version archive
  if [ -n "$REF" ]; then
    src="$HOME/resense_export/$(printf '%s' "$REF" | tr -c 'A-Za-z0-9._-' '_')"
    run rm -rf "$src"
    if ! run git clone -q --branch "$REF" "$(git remote get-url origin)" "$src"; then
      note "clone of $REF from origin failed; cloning the local checkout instead (same commit)"
      run git fetch -q --tags origin || true
      run git clone -q --branch "$REF" "$REPO_DIR" "$src"
    fi
    version="${VERSION_ARG:-$REF}"
  else
    version="${VERSION_ARG:-$(sed -n 's/^version[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' pyproject.toml | head -n 1)-$(git rev-parse --short HEAD)}"
    note "no --ref: exported from the checkout at $(git rev-parse --short HEAD) as $version (the upload uses --ref v1.0-rc1 / v1.0-final)"
  fi
  archive="$DIST_DIR/resense-image-$version.tar.gz"
  run mkdir -p "$DIST_DIR"
  step_run export_image env VERSION="$version" OUT_DIR="$DIST_DIR" GZIP_LEVEL="${GZIP_LEVEL:-6}" "$src/scripts/export_image.sh"
  if [ "$LAST_RC" = 0 ]; then
    step_run load_check "$src/scripts/load_image.sh" "$archive"
    if [ "$DRY_RUN" != 1 ]; then
      {
        echo "archive:  $(basename "$archive")"
        echo "bytes:    $(wc -c < "$archive" | tr -d ' ') ($(awk -v b="$(wc -c < "$archive")" 'BEGIN { printf "%.2f GiB", b / 1073741824 }'))"
        echo "sha256:   $(cut -d' ' -f1 "$archive.sha256")"
        echo "commit:   $(git -C "$src" rev-parse HEAD) ($([ -n "$REF" ] && echo "clean clone of $REF" || echo "checkout"))"
        echo "image:    $(docker image inspect -f '{{.Size}}' "resense:$version" 2>/dev/null) bytes unpacked"
        echo "docker:   $(docker_version)"
        echo "path:     $archive (+ .sha256; the archive itself is never committed)"
      } | tee "$RES/archive.txt"
      cp "$archive.sha256" "$RES/"
    fi
  fi
  finish
}

# ---- offline -----------------------------------------------------------------------------------------
OFF_DIR=/var/lib/resense-offline
OFF_UNIT=resense-offline-restore
write_offline_scripts() {   # -> $RES/apply_block.sh, $RES/restore_block.sh
  local ssh_ports ext_if allow_ips="" h ip ips
  ssh_ports="$( { root_q sshd -T 2>/dev/null | awk '/^port / { print $2 }' || true; echo "${SSH_CONNECTION:-}" | awk 'NF == 4 { print $4 }'; echo 22; } | sort -un | tr '\n' ' ')"
  ext_if="$(ip route show default 2>/dev/null | awk '{ for (i = 1; i < NF; i++) if ($i == "dev") { print $(i + 1); exit } }' || true)"
  for h in ${ALLOW_HOSTS//,/ }; do
    ips="$(getent ahostsv4 "$h" 2>/dev/null | awk '{ print $1 }' | sort -u | tr '\n' ' ' || true)"
    [ -n "${ips// /}" ] || warn "--allow-host $h does not resolve now: it will be blocked"
    for ip in $ips; do allow_ips="$allow_ips $ip"; done
  done
  cat > "$RES/restore_block.sh" <<EOF
#!/bin/sh
# ReSense offline rehearsal: restore outbound network. Idempotent. Written by scripts/vm/run_plan.sh.
# By hand, if ever needed:  sudo sh $OFF_DIR/restore.sh     (a reboot also clears the block: it is never saved)
for T in iptables ip6tables; do
  command -v "\$T" >/dev/null 2>&1 || continue
  while "\$T" -w -D OUTPUT -j RESENSE_OFFLINE 2>/dev/null; do :; done
  while "\$T" -w -D DOCKER-USER -j RESENSE_OFFLINE_FWD 2>/dev/null; do :; done
  for C in RESENSE_OFFLINE RESENSE_OFFLINE_FWD; do "\$T" -w -F "\$C" 2>/dev/null; "\$T" -w -X "\$C" 2>/dev/null; done
done
mkdir -p $OFF_DIR && echo "\$(date -Is) restored (\${1:-by hand})" >> $OFF_DIR/history.txt
[ "\${1:-}" = timer ] || systemctl stop $OFF_UNIT.timer 2>/dev/null
exit 0
EOF
  cat > "$RES/apply_block.sh" <<EOF
#!/bin/sh
# ReSense offline rehearsal: block outbound traffic from this host (and from Docker bridge
# networks), keep loopback, established connections (the SSH sessions), replies of sshd (ports:
# $ssh_ports), DDS discovery multicast, the cloud metadata service and DHCP.
set -e
C=RESENSE_OFFLINE
iptables -w -N \$C 2>/dev/null || iptables -w -F \$C
iptables -w -A \$C -o lo -j ACCEPT
iptables -w -A \$C -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
for p in $ssh_ports; do iptables -w -A \$C -p tcp --sport "\$p" -j ACCEPT; done
iptables -w -A \$C -d 224.0.0.0/4 -j ACCEPT
iptables -w -A \$C -d 169.254.169.254/32 -j ACCEPT
iptables -w -A \$C -p udp --dport 67:68 -j ACCEPT
$(if [ -n "$allow_ips" ]; then
  echo "iptables -w -A \$C -p udp --dport 53 -j ACCEPT"
  echo "iptables -w -A \$C -p tcp --dport 53 -j ACCEPT"
  for ip in $allow_ips; do echo "iptables -w -A \$C -d $ip/32 -p tcp --dport 443 -j ACCEPT"; done
fi)
iptables -w -A \$C -m limit --limit 30/min -j LOG --log-prefix "RESENSE-OFFLINE " --log-uid \
  || iptables -w -A \$C -m limit --limit 30/min -j LOG --log-prefix "RESENSE-OFFLINE " || true
iptables -w -A \$C -p tcp -j REJECT --reject-with tcp-reset
iptables -w -A \$C -j REJECT
iptables -w -C OUTPUT -j \$C 2>/dev/null || iptables -w -I OUTPUT 1 -j \$C
if iptables -w -n -L DOCKER-USER >/dev/null 2>&1 && [ -n "$ext_if" ]; then
  F=RESENSE_OFFLINE_FWD
  iptables -w -N \$F 2>/dev/null || iptables -w -F \$F
  iptables -w -A \$F -m conntrack --ctstate ESTABLISHED,RELATED -j RETURN
  iptables -w -A \$F -o $ext_if -j REJECT
  iptables -w -C DOCKER-USER -j \$F 2>/dev/null || iptables -w -I DOCKER-USER 1 -j \$F
fi
# IPv6 in a subshell: if it cannot be applied, the IPv4 block stays and the check that follows
# (scripts/check_no_network.py) still fails the rehearsal when IPv6 reaches the internet
if command -v ip6tables >/dev/null 2>&1 && ip6tables -w -n -L OUTPUT >/dev/null 2>&1; then (
  set -e
  ip6tables -w -N \$C 2>/dev/null || ip6tables -w -F \$C
  ip6tables -w -A \$C -o lo -j ACCEPT
  ip6tables -w -A \$C -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
  for p in $ssh_ports; do ip6tables -w -A \$C -p tcp --sport "\$p" -j ACCEPT; done
  ip6tables -w -A \$C -p ipv6-icmp -j ACCEPT
  ip6tables -w -A \$C -d ff00::/8 -j ACCEPT
  ip6tables -w -A \$C -d fe80::/10 -j ACCEPT
  ip6tables -w -A \$C -p udp --dport 546:547 -j ACCEPT
  ip6tables -w -A \$C -m limit --limit 30/min -j LOG --log-prefix "RESENSE-OFFLINE6 " || true
  ip6tables -w -A \$C -j REJECT
  ip6tables -w -C OUTPUT -j \$C 2>/dev/null || ip6tables -w -I OUTPUT 1 -j \$C
) || echo "WARNING: the IPv6 block could not be applied"; fi
EOF
  {
    echo "ssh ports kept: $ssh_ports"
    echo "external interface: ${ext_if:-?}"
    echo "allowed hosts: ${ALLOW_HOSTS:-none}${allow_ips:+ ($allow_ips; with DNS)}"
  } >> "$RES/window.txt"
}
BLOCK_ON=0
offline_restore() {   # idempotent; safe in a trap (no set -e, no dependence on the log pipe)
  set +e
  trap '' PIPE
  [ "$BLOCK_ON" = 1 ] || return 0
  if [ "$DRY_RUN" = 1 ]; then BLOCK_ON=0; log "DRY: sudo sh $OFF_DIR/restore.sh script"; return 0; fi
  if [ "$(id -u)" -eq 0 ]; then sh "$OFF_DIR/restore.sh" script; else sudo -n sh "$OFF_DIR/restore.sh" script; fi
  BLOCK_ON=0
  docker rm -f resense_vm_node resense_ct_node resense_ct_echo >/dev/null 2>&1
  {
    echo "restored: $(date -Is)"
    echo "internet after restore: github.com HTTP $(curl -s -o /dev/null -m 15 -w '%{http_code}' https://github.com 2>/dev/null)"
  } >> "$RES/window.txt" 2>/dev/null
  log "network restored" 2>/dev/null
  return 0
}
window_open() { [ "$DRY_RUN" = 1 ] || root_q iptables -w -C OUTPUT -j RESENSE_OFFLINE 2>/dev/null; }
off_step() {   # off_step <name> <command...>: only while the block is still on
  if ! window_open; then
    step_skip "$1" "the offline window closed (timer) before this step: rerun with a longer --minutes"
    record_step "$1-window" 1 FAIL 0 "window expired"
    return 0
  fi
  step_run "$@"
}
cmd_offline() {
  ensure_docker; ensure_sudo; need_bags
  have iptables || [ "$DRY_RUN" = 1 ] || die 3 "iptables is not installed (setup_vm.sh installs it)"
  local tar="$IMAGE_TAR_ARG"
  if [ -z "$tar" ]; then
    tar="$(find "$DIST_DIR" "$REPO_DIR/dist" -maxdepth 1 -name 'resense-image-*.tar.gz' -printf '%T@ %p\n' 2>/dev/null \
           | sort -rn | head -n 1 | cut -d' ' -f2- || true)"
  fi
  if [ -z "$tar" ] || [ ! -f "$tar" ]; then
    [ "$DRY_RUN" = 1 ] || die 2 "no image archive (resense-image-*.tar.gz in $DIST_DIR): run 'scripts/vm/run_plan.sh export' first, while the VM is online"
    tar="$DIST_DIR/resense-image-<version>.tar.gz"
  fi
  begin
  note "image archive: $tar"
  {
    echo "window: $MINUTES min max; started $(date -Is); automatic restore by the systemd timer $OFF_UNIT.timer"
  } > "$RES/window.txt"
  write_offline_scripts
  if [ "$DRY_RUN" = 1 ]; then
    log "DRY: the block that would be applied ($RES/apply_block.sh):"; sed 's/^/   /' "$RES/apply_block.sh"
    log "DRY: the restore ($RES/restore_block.sh), armed first as a timer:"; sed 's/^/   /' "$RES/restore_block.sh"
  fi
  as_root install -D -m 0755 "$RES/restore_block.sh" "$OFF_DIR/restore.sh"
  # 1. the safety net first: a timer that restores the network in $MINUTES min, whatever happens here
  root_q systemctl stop "$OFF_UNIT.timer" "$OFF_UNIT.service" >/dev/null 2>&1 || true
  root_q systemctl reset-failed "$OFF_UNIT.timer" "$OFF_UNIT.service" >/dev/null 2>&1 || true
  if as_root systemd-run --unit="$OFF_UNIT" --on-active="${MINUTES}min" --timer-property=AccuracySec=1s \
       /bin/sh "$OFF_DIR/restore.sh" timer && { [ "$DRY_RUN" = 1 ] || root_q systemctl is-active -q "$OFF_UNIT.timer"; }; then
    echo "safety net: systemd timer $OFF_UNIT.timer, fires at $(date -d "+$MINUTES min" -Is)" | tee -a "$RES/window.txt"
  elif as_root setsid -f sh -c "sleep $(( MINUTES * 60 )); sh $OFF_DIR/restore.sh timer" >/dev/null 2>&1 < /dev/null; then
    echo "safety net: background 'sleep $(( MINUTES * 60 )); restore' (systemd-run unavailable)" | tee -a "$RES/window.txt"
  else
    die 3 "could not arm the automatic restore: the block is NOT applied"
  fi
  # 2. the block, restored on any exit of this script as well
  BLOCK_ON=1
  trap 'offline_restore' EXIT
  trap 'offline_restore; exit 130' INT TERM HUP
  if ! as_root sh "$RES/apply_block.sh"; then
    note "applying the block failed: restored, nothing rehearsed"
    record_step apply_block 1 FAIL 0 "iptables rules could not be applied"
    offline_restore; finish; return
  fi
  record_step apply_block "$([ "$DRY_RUN" = 1 ] && echo - || echo 0)" "$([ "$DRY_RUN" = 1 ] && echo DRY || echo PASS)" 0 \
    "outbound blocked until $(date -d "+$MINUTES min" +%T) at the latest"
  [ "$DRY_RUN" = 1 ] || { root_q iptables -w -S RESENSE_OFFLINE; root_q ip6tables -w -S RESENSE_OFFLINE 2>/dev/null || true; } > "$RES/rules.txt"
  step_run verify_blocked python3 scripts/check_no_network.py
  if [ "$LAST_RC" != 0 ]; then
    note "this host still reaches the internet with the block on: nothing rehearsed (restored)"
    offline_restore; finish; return
  fi
  if [ -t 0 ] && [ "${OFFLINE_CONFIRM:-1}" = 1 ] && [ "$DRY_RUN" != 1 ]; then
    echo
    echo ">>> Outbound internet is now blocked (automatic restore at $(date -d "+$MINUTES min" +%T))."
    echo ">>> Open a NEW ssh session to this VM now. If it works, type 'yes' here within 120 s;"
    echo ">>> anything else, or no answer, restores the network at once."
    local ans=""
    read -r -t 120 ans || true
    if [ "$ans" != yes ]; then
      record_step ssh_confirm 1 FAIL 0 "no confirmation that a new SSH login works"
      offline_restore; finish; return
    fi
    record_step ssh_confirm 0 PASS 0 "a new SSH login works with the block on"
  fi
  # 3. the stand's procedure, offline
  if [ "${KEEP_IMAGE:-0}" != 1 ]; then
    off_step remove_images sh -c "docker images --format '{{.Repository}}:{{.Tag}}' | grep '^resense:' | xargs -r docker rmi -f"
  fi
  off_step load_image scripts/load_image.sh "$tar"
  off_step dry_obstacle env SKIP_BUILD=1 OFFLINE=1 OUT="$RES/dry_obstacle" scripts/dry_run.sh "$BAG_OBS"
  off_step dry_clear env SKIP_BUILD=1 OFFLINE=1 OUT="$RES/dry_clear" scripts/dry_run.sh "$BAG_CLR" --expect-clear --max-alarm-frames 2
  if [ "$ROS_MODE" = host ] && has_host_ros || [ "$DRY_RUN" = 1 ]; then
    off_step jury_console host_console "$RES/jury_console" rmw_fastrtps_cpp "$BAG_OBS" -- \
      --expect-obstacle --distance 50:62 --min-frames 20 --max-p95-latency 1000 --max-dropped 100000
  else
    off_step jury_console env OUT="$RES/jury_console" scripts/console_test.sh "$BAG_OBS" -- \
      --expect-obstacle --distance 50:62 --min-frames 20 --max-p95-latency 1000 --max-dropped 100000
    note "no host ROS 2: the player ran from the image as uid 1000 (console_test.sh), not from the host console"
  fi
  window_open || note "the window had closed before the last step finished"
  # 4. what tried to go out while blocked
  if [ "$DRY_RUN" != 1 ]; then
    root_q journalctl -k --since "@$T_BEGIN" --no-pager 2>/dev/null | grep 'RESENSE-OFFLINE' \
      | sed -E 's/ (SRC|MAC)=[^ ]*//g' > "$RES/blocked_attempts.txt" || true
    note "outbound attempts blocked and logged (rate-limited; they include the deliberate ones of check_no_network.py):" \
         "$(wc -l < "$RES/blocked_attempts.txt" | tr -d ' '), by uid: $(grep -o 'UID=[0-9]*' "$RES/blocked_attempts.txt" | sort | uniq -c | tr -s ' \n' ' ')"
  fi
  offline_restore
  trap - EXIT INT TERM HUP
  [ -n "$ALLOW_HOSTS" ] && note "kept open during the window: DNS and HTTPS to $ALLOW_HOSTS (so an agent session survives); all else blocked"
  finish
}

cmd_restore() {
  ensure_sudo
  if [ "$DRY_RUN" = 1 ]; then as_root sh "$OFF_DIR/restore.sh" manual; return 0; fi
  if [ -f "$OFF_DIR/restore.sh" ]; then as_root sh "$OFF_DIR/restore.sh" manual
  else
    local t
    for t in iptables ip6tables; do
      have "$t" || continue
      while root_q "$t" -w -D OUTPUT -j RESENSE_OFFLINE 2>/dev/null; do :; done
      while root_q "$t" -w -D DOCKER-USER -j RESENSE_OFFLINE_FWD 2>/dev/null; do :; done
      root_q "$t" -w -F RESENSE_OFFLINE 2>/dev/null || true; root_q "$t" -w -X RESENSE_OFFLINE 2>/dev/null || true
      root_q "$t" -w -F RESENSE_OFFLINE_FWD 2>/dev/null || true; root_q "$t" -w -X RESENSE_OFFLINE_FWD 2>/dev/null || true
    done
  fi
  root_q systemctl stop "$OFF_UNIT.timer" >/dev/null 2>&1 || true
  if root_q iptables -w -C OUTPUT -j RESENSE_OFFLINE 2>/dev/null; then die 1 "the block is still in place"; fi
  echo "no offline block active; github.com answers HTTP $(curl -s -o /dev/null -m 15 -w '%{http_code}' https://github.com || true)"
}

# ---- all ---------------------------------------------------------------------------------------------
cmd_all() {
  begin
  local s rc
  for s in dryrun bench gate export offline collect; do
    hr; log "== all: $s"
    set +e
    "$SELF" "$s" --minutes "$MINUTES" ${ALLOW_HOSTS:+--allow-host "$ALLOW_HOSTS"}
    rc=$?
    set -e
    if [ "$rc" = 0 ]; then record_step "$s" 0 PASS 0; else record_step "$s" "$rc" FAIL 0 "see $RESULTS_ROOT/$RUN_DATE/$s/result.txt"; fi
  done
  finish
}

# ---- collect -----------------------------------------------------------------------------------------
stage_evidence() {   # stage_evidence <results subdir> <docs/evidence folder name>
  local src="$1" name="$2" dst f
  [ -d "$src" ] || return 0
  dst="$REPO_DIR/docs/evidence/$name"
  if [ -e "$dst" ]; then local i=2; while [ -e "${dst}_$i" ]; do i=$(( i + 1 )); done; dst="${dst}_$i"; fi
  mkdir -p "$dst"
  (cd "$src" && tar -cf - --exclude='work_*' .) | tar -xf - -C "$dst"
  find "$dst" -name '*.log' -exec sh -c 'mv "$1" "${1%.log}_log.txt"' _ {} \;
  find "$dst" -name '*.jsonl' -exec gzip -f {} \;
  find "$dst" -type f -size +20M -print -delete | sed 's/^/   dropped (> 20 MB): /'
  echo "   $src -> ${dst#"$REPO_DIR"/}"
}
cmd_collect() {
  local day="${COLLECT_DATE:-$RUN_DATE}" d out
  d="$RESULTS_ROOT/$day"
  [ -d "$d" ] || die 2 "no results for $day in $RESULTS_ROOT"
  RUN_DATE="$day"; begin
  out="${COLLECT_OUT:-$HOME/resense_results_$day.tar.gz}"
  [ "$DRY_RUN" = 1 ] && { log "DRY: would write $d/summary.md and $out"; finish; return; }
  find "$d" -name '*.jsonl' -size +1M -not -path '*/work_*' -exec gzip -f {} \; 2>/dev/null || true
  local md="$d/summary.md" s r host
  host="$(hostname)"
  {
    echo "# ReSense VM results, $day"
    echo
    echo "Packed by \`scripts/vm/run_plan.sh collect\` on $(date -Is). Machine and commit:"
    echo
    echo '```text'
    if [ -f "$d/setup/resources.txt" ]; then grep -E '^(os|cpu|ram|disk):' "$d/setup/resources.txt"; else print_resources; fi
    git_facts
    echo '```'
    echo
    echo "| run | result | copy to the repository | then update |"
    echo "|---|---|---|---|"
    for s in setup fetch dryrun bench gate export offline all; do
      r="not run"
      [ -f "$d/$s/result.txt" ] && r="$(head -n 1 "$d/$s/result.txt" | sed 's/|/\//g')"
      [ -f "$d/$s/summary.txt" ] && [ "$s" = setup ] && r="$(grep -E '^(READY|NOT READY)' "$d/$s/summary.txt" | head -n 1)"
      [ -f "$d/$s/inventory.txt" ] && [ "$s" = fetch ] && r="$(tail -n 1 "$d/$s/fetch_log.txt" 2>/dev/null)"
      case "$s" in
        setup|fetch) echo "| $s | $r | \`docs/evidence/vm_$day/\` | — |" ;;
        dryrun) echo "| dryrun | $r | \`docs/evidence/dry_run_$day/\` | SUBMISSION \"Dry run\"; CAPTAIN C7 (C4 when host_fastdds passed), action 15 |" ;;
        bench) echo "| bench | $r | \`docs/evidence/bench_$day/\` | EXPERIMENTS §3 (append the 8-core table); CAPTAIN C8, action 7 |" ;;
        gate) echo "| gate | $r | \`docs/evidence/gate_$day/\` (JSON, no work dirs) | CAPTAIN action 11 (go / no-go is the human's) |" ;;
        export) echo "| export | $r | \`docs/evidence/export_$day/\` (archive.txt, .sha256; never the archive) | CAPTAIN actions 14b / 16 and §5 (size, sha256); SUBMISSION \"Upload\" |" ;;
        offline) echo "| offline | $r | \`docs/evidence/offline_$day/\` | CAPTAIN C25 (and action 15 on 28.09); SUBMISSION \"Dry run\" |" ;;
        all) echo "| all | $r | — | — |" ;;
      esac
    done
    echo
    for s in dryrun bench gate export offline; do
      [ -f "$d/$s/result.txt" ] || continue
      echo "## $s"; echo; echo '```text'; cat "$d/$s/result.txt"
      if [ -s "$d/$s/highlights.txt" ]; then echo; head -n 80 "$d/$s/highlights.txt"; fi
      echo '```'; echo
    done
    echo "## Before committing"
    echo
    echo "* No personal data: names, e-mails, tokens, keys, IP addresses of team members. Files that look"
    echo "  suspicious (automatic scan):"
    grep -rIlE 'ghp_[A-Za-z0-9]{20,}|github_pat_|BEGIN [A-Z ]*PRIVATE KEY|y0_[A-Za-z0-9_-]{30,}|AQVN[A-Za-z0-9_-]{20,}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}' \
      "$d" --exclude=summary.md 2>/dev/null | sed "s#^$d/#  * #" || echo "  * none found"
    echo "* The VM hostname \`$host\` is recorded (uname, docker info): fine unless it is a person's name."
    echo "* \`.gitignore\` hides \`*.log\` and \`*.jsonl\`: \`collect --to-repo\` renames and gzips them."
  } > "$md"
  local list
  list="$(mktemp)"
  (cd "$RESULTS_ROOT" && find "$day" -type f -size -25M -not -path '*/work_*' -not -name '*.jsonl' | sort) > "$list"
  if tar -czf "$out" -C "$RESULTS_ROOT" -T "$list"; then
    echo "packed $(wc -l < "$list" | tr -d ' ') files into $out ($(du -h "$out" | cut -f1)); left out: files > 25 MB, gate work dirs, raw *.jsonl"
    record_step pack 0 PASS 0 "$out"
  else
    record_step pack 1 FAIL 0 "tar failed"
  fi
  rm -f "$list"
  cp "$md" "$RES/summary.md"
  if [ "$TO_REPO" = 1 ]; then
    log "staging into $REPO_DIR/docs/evidence/ (not committed; review, then git add)"
    stage_evidence "$d/dryrun" "dry_run_$day"
    if [ -d "$d/bench/bench_$day" ]; then stage_evidence "$d/bench/bench_$day" "bench_$day"; cp "$d/bench/result.txt" "$REPO_DIR/docs/evidence/bench_$day/vm_result.txt" 2>/dev/null || true
    else stage_evidence "$d/bench" "bench_$day"; fi
    stage_evidence "$d/gate" "gate_$day"
    stage_evidence "$d/export" "export_$day"
    stage_evidence "$d/offline" "offline_$day"
    if [ -d "$d/setup" ] || [ -d "$d/fetch" ]; then
      mkdir -p "$REPO_DIR/docs/evidence/vm_$day"
      for f in setup/resources.txt setup/summary.txt fetch/plan.txt fetch/inventory.txt; do
        [ -f "$d/$f" ] && cp "$d/$f" "$REPO_DIR/docs/evidence/vm_$day/${f//\//_}"
      done
      cp "$md" "$REPO_DIR/docs/evidence/vm_$day/summary.md"
      echo "   setup / fetch facts -> docs/evidence/vm_$day/"
    fi
    git -C "$REPO_DIR" status --short docs/evidence 2>/dev/null | head -n 40 || true
    echo "   review, then: git add docs/evidence/*_$day (AGENT_BRIEF.md step 9)"
    record_step stage_to_repo 0 PASS 0 "docs/evidence/*_$day (not committed)"
  fi
  finish
}

case "$SUB" in
  status) cmd_status ;;
  bench) cmd_bench ;;
  dryrun) cmd_dryrun ;;
  gate) cmd_gate ;;
  export) cmd_export ;;
  offline) cmd_offline ;;
  restore-network) cmd_restore ;;
  all) cmd_all ;;
  collect) cmd_collect ;;
esac
exit "$RC_FINAL"
