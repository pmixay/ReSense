# shellcheck shell=bash
# Shared helpers of the VM kit (scripts/vm/): paths, logging, dry-run printing, resource
# detection, the kit's state file. Sourced by setup_vm.sh, fetch_data.sh and run_plan.sh; not run.
#
# Environment understood by every script of the kit (all optional):
#   REPO_DIR       the ReSense checkout (default: the checkout this file is in, else ~/ReSense)
#   DATA_DIR       where the organizers' data goes (default /data); CACHE_DIR (default $DATA_DIR/cache)
#   VENV           the python venv of the kit (default ~/resense-venv)
#   RESULTS_ROOT   default ~/resense_results; every run writes to $RESULTS_ROOT/<date>/<subcommand>/
#   RUN_DATE       the <date> above (default: today, YYYY-MM-DD)
#   DIST_DIR       where export puts the image archive (default ~/resense_dist)
#   DRY_RUN=1      print the commands instead of running them (nothing is installed or downloaded)
#   OS_RELEASE_FILE  read this instead of /etc/os-release (to try the 24.04 path elsewhere)

if [ "${VM_TRACE:-0}" = 1 ]; then set -x; fi      # VM_TRACE=1: trace every command (debugging)
VM_KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESENSE_REPO_URL="${RESENSE_REPO_URL:-https://github.com/pmixay/ReSense}"
# shellcheck disable=SC2034  # used by the scripts that source this file
RESENSE_BRANCH_DEFAULT="claude/nifty-pascal-lzgl78"
VM_STATE_FILE="${VM_STATE_FILE:-$HOME/.resense_vm.env}"

# The kit's state file (written by setup_vm.sh): fills only the variables the caller left unset.
if [ -f "$VM_STATE_FILE" ]; then
  while IFS='=' read -r _k _v; do
    case "$_k" in
      REPO_DIR|DATA_DIR|CACHE_DIR|VENV|RESULTS_ROOT|DIST_DIR|ROS_MODE|BRANCH)
        if [ -z "${!_k:-}" ]; then printf -v "$_k" '%s' "$_v"; fi ;;
    esac
  done < <(grep -E '^[A-Z_]+=' "$VM_STATE_FILE" || true)
  unset _k _v
fi

if [ -z "${REPO_DIR:-}" ]; then
  if [ -f "$VM_KIT_DIR/../../pyproject.toml" ] && [ -d "$VM_KIT_DIR/../../resense" ]; then
    REPO_DIR="$(cd "$VM_KIT_DIR/../.." && pwd)"
  else
    REPO_DIR="$HOME/ReSense"
  fi
fi
DATA_DIR="${DATA_DIR:-/data}"
CACHE_DIR="${CACHE_DIR:-$DATA_DIR/cache}"
VENV="${VENV:-$HOME/resense-venv}"
RESULTS_ROOT="${RESULTS_ROOT:-$HOME/resense_results}"
RUN_DATE="${RUN_DATE:-$(date +%F)}"
DIST_DIR="${DIST_DIR:-$HOME/resense_dist}"
DRY_RUN="${DRY_RUN:-0}"
ROS_MODE="${ROS_MODE:-}"
BRANCH="${BRANCH:-}"

# ---- output -------------------------------------------------------------------------------------
log()  { printf '%s  %s\n' "$(date +%H:%M:%S)" "$*"; }
info() { log "$*"; }
warn() { printf '%s  WARNING: %s\n' "$(date +%H:%M:%S)" "$*" >&2; }
die() {   # die [code] message...
  local code=1
  if [[ "${1:-}" =~ ^[0-9]+$ ]]; then code="$1"; shift; fi
  printf '%s  ERROR: %s\n' "$(date +%H:%M:%S)" "$*" >&2
  exit "$code"
}
hr() { printf '%s\n' "------------------------------------------------------------------------------------------"; }
# header_help <script>: the script's leading comment block (after the shebang) is its --help
header_help() { awk 'NR == 1 { next } /^#/ { sub(/^# ?/, ""); print; next } { exit }' "$1"; }

# start_log <file>: from here on, everything the script prints also goes to <file>.
start_log() {
  mkdir -p "$(dirname "$1")"
  exec > >(tee -a "$1") 2>&1
  log "log: $1"
}

# run <cmd...>: run it, or with DRY_RUN=1 print it (shell-quoted) and succeed.
run() {
  if [ "$DRY_RUN" = 1 ]; then
    printf 'DRY:'; printf ' %q' "$@"; printf '\n'
    return 0
  fi
  "$@"
}
# as_root <cmd...>: run as root (sudo when needed), honouring DRY_RUN.
as_root() {
  if [ "$(id -u)" -eq 0 ]; then run "$@"; else run sudo "$@"; fi
}
# as_root_sh '<shell text>': the same for a shell snippet.
as_root_sh() {
  if [ "$DRY_RUN" = 1 ]; then printf 'DRY: (as root) %s\n' "$1"; return 0; fi
  if [ "$(id -u)" -eq 0 ]; then bash -c "$1"; else sudo bash -c "$1"; fi
}
have() { command -v "$1" >/dev/null 2>&1; }
# root_q <cmd...>: a read-only query as root; runs even with DRY_RUN=1 (never prompts for a password)
root_q() {
  if [ "$(id -u)" -eq 0 ]; then "$@"; else sudo -n "$@"; fi
}

# ---- resources ----------------------------------------------------------------------------------
# nearest existing directory of a path (df needs one)
existing_parent() {
  local p="$1"
  while [ ! -e "$p" ] && [ "$p" != / ]; do p="$(dirname "$p")"; done
  printf '%s\n' "$p"
}
free_mb() { df -Pm "$(existing_parent "$1")" 2>/dev/null | awk 'NR == 2 { print $4 }'; }
total_mb() { df -Pm "$(existing_parent "$1")" 2>/dev/null | awk 'NR == 2 { print $2 }'; }
fs_of() { df -P "$(existing_parent "$1")" 2>/dev/null | awk 'NR == 2 { print $1 " " $6 }'; }
same_fs() { [ "$(stat -c %d "$(existing_parent "$1")" 2>/dev/null)" = "$(stat -c %d "$(existing_parent "$2")" 2>/dev/null)" ]; }
# sizes in the kit are MiB (df -Pm); gb prints GiB, as `df -h` does
gb() { awk -v m="$1" 'BEGIN { printf "%.1f", m / 1024 }'; }

lscpu_field() { LC_ALL=C lscpu 2>/dev/null | sed -n "s/^$1:[[:space:]]*//p" | head -n 1; }

# detect_resources: sets OS_ID OS_VERSION_ID OS_CODENAME OS_PRETTY ARCH CPU_MODEL NPROC CORES
# THREADS_PER_CORE RAM_MB and prints nothing.
detect_resources() {
  local osr="${OS_RELEASE_FILE:-/etc/os-release}" cps sockets
  OS_ID="$(sed -n 's/^ID=//p' "$osr" 2>/dev/null | tr -d '"')"
  OS_VERSION_ID="$(sed -n 's/^VERSION_ID=//p' "$osr" 2>/dev/null | tr -d '"')"
  OS_CODENAME="$(sed -n 's/^UBUNTU_CODENAME=//p' "$osr" 2>/dev/null | tr -d '"')"
  [ -n "$OS_CODENAME" ] || OS_CODENAME="$(sed -n 's/^VERSION_CODENAME=//p' "$osr" 2>/dev/null | tr -d '"')"
  OS_PRETTY="$(sed -n 's/^PRETTY_NAME=//p' "$osr" 2>/dev/null | tr -d '"')"
  ARCH="$(dpkg --print-architecture 2>/dev/null || uname -m)"
  CPU_MODEL="$(lscpu_field 'Model name')"
  NPROC="$(nproc 2>/dev/null || echo 1)"
  cps="$(lscpu_field 'Core(s) per socket')"; sockets="$(lscpu_field 'Socket(s)')"
  THREADS_PER_CORE="$(lscpu_field 'Thread(s) per core')"
  if [[ "$cps" =~ ^[0-9]+$ && "$sockets" =~ ^[0-9]+$ ]]; then CORES=$(( cps * sockets )); else CORES="?"; fi
  RAM_MB="$(awk '/^MemTotal/ { printf "%d", $2 / 1024 }' /proc/meminfo 2>/dev/null || echo 0)"
}

# CPU steal over ~2 s (a shared / burstable cloud vCPU shows up here), in percent.
cpu_steal_pct() {
  local a b
  a="$(awk '/^cpu / { print $2+$3+$4+$5+$6+$7+$8+$9, $9 }' /proc/stat)"
  sleep 2
  b="$(awk '/^cpu / { print $2+$3+$4+$5+$6+$7+$8+$9, $9 }' /proc/stat)"
  awk -v a="$a" -v b="$b" 'BEGIN { split(a, x, " "); split(b, y, " "); t = y[1] - x[1];
    printf "%.1f", (t > 0 ? 100 * (y[2] - x[2]) / t : 0) }'
}

print_resources() {
  detect_resources
  echo "os:        ${OS_PRETTY:-?} (id ${OS_ID:-?} ${OS_VERSION_ID:-?}, codename ${OS_CODENAME:-?}), arch $ARCH, kernel $(uname -r)"
  echo "cpu:       ${CPU_MODEL:-?}; $NPROC vCPU, $CORES physical cores, $THREADS_PER_CORE thread(s) per core"
  echo "ram:       $(gb "$RAM_MB") GiB"
  local d
  for d in / "$DATA_DIR" "$HOME" /var/lib/docker; do
    echo "disk:      $d -> $(fs_of "$d"): $(gb "$(free_mb "$d")") GiB free of $(gb "$(total_mb "$d")") GiB"
  done
}

# ---- repository facts ---------------------------------------------------------------------------
git_facts() {
  if git -C "$REPO_DIR" rev-parse --git-dir >/dev/null 2>&1; then
    echo "commit:    $(git -C "$REPO_DIR" rev-parse HEAD) ($(git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD))"
    if [ -n "$(git -C "$REPO_DIR" status --porcelain --untracked-files=no 2>/dev/null)" ]; then
      echo "worktree:  DIRTY (uncommitted changes to tracked files)"
    else
      echo "worktree:  clean"
    fi
  else
    echo "commit:    n/a ($REPO_DIR is not a git checkout)"
  fi
}

venv_python() { printf '%s\n' "$VENV/bin/python"; }

# pyenv <cmd...>: run with the repository on PYTHONPATH and the venv first on PATH (no pip install
# of the project: the scripts import resense from the checkout, the native kernels are built in place)
pyenv() {
  run env PATH="$VENV/bin:$PATH" PYTHONPATH="$REPO_DIR${PYTHONPATH:+:$PYTHONPATH}" "$@"
}

# ros_env: source ROS 2 Humble into the current shell (set -u safe); fails without it.
ros_env() {
  [ -f /opt/ros/humble/setup.bash ] || return 1
  set +u
  # shellcheck disable=SC1091
  . /opt/ros/humble/setup.bash
  set -u
}
has_host_ros() { [ -f /opt/ros/humble/setup.bash ]; }

# bag_ok <dir>: a rosbag2 directory with metadata.yaml and every file it lists, non-empty
bag_ok() {
  local d="$1" f
  [ -f "$d/metadata.yaml" ] || return 1
  while read -r f; do
    [ -n "$f" ] || continue
    [ -s "$d/$f" ] || return 1
  done < <(bag_files "$d")
  return 0
}
# the files a bag lists under relative_file_paths
bag_files() {
  awk '/^[[:space:]]*relative_file_paths:/ { f = 1; next }
       f && /^[[:space:]]*- / { sub(/^[[:space:]]*- */, ""); gsub(/"/, ""); print; next }
       f { exit }' "$1/metadata.yaml" 2>/dev/null
}
# message count of a bag (metadata.yaml), empty if unknown
bag_messages() {
  sed -n '/^ *message_count:/ { s/^ *message_count: *//p; q }' "$1/metadata.yaml" 2>/dev/null
}
# duration of a bag in whole seconds (metadata.yaml), 0 if unknown
bag_seconds() {
  awk '/duration:/ { f = 1 } f && /nanoseconds:/ { printf "%d", $2 / 1e9; exit }' "$1/metadata.yaml" 2>/dev/null || echo 0
}
npy_count() { { find "$1" -maxdepth 1 -name '*.npy' 2>/dev/null || true; } | wc -l | tr -d ' '; }

# results directory of a subcommand for today; an earlier run of the same day is kept as <sub>_<time>
results_dir() {
  local d="$RESULTS_ROOT/$RUN_DATE/$1"
  if [ "$DRY_RUN" != 1 ] && [ -d "$d" ] && [ -n "$(ls -A "$d" 2>/dev/null)" ]; then
    mv "$d" "${d}_$(date -r "$d" +%H%M%S 2>/dev/null || date +%H%M%S)"
  fi
  mkdir -p "$d"
  printf '%s\n' "$d"
}
