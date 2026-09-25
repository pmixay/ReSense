#!/usr/bin/env bash
# One-time setup of a fresh Ubuntu 22.04 VM for the ReSense runs the team cannot do elsewhere
# (8-core bench, clean-machine dry run with the original bags, host-console player, offline
# rehearsal, image export, full regression gate): scripts/vm/AGENT_BRIEF.md.
#
#   scripts/vm/setup_vm.sh [--branch B] [options]          # from a checkout (it updates that checkout)
#   curl -fsSL https://raw.githubusercontent.com/pmixay/ReSense/<branch>/scripts/vm/setup_vm.sh \
#     | bash -s -- --branch <branch>                        # bootstrap: clones to ~/ReSense, re-runs from there
#
# Steps (each is skipped when already done, so a second run only repairs what is missing):
#   1. resources: OS, CPU, RAM, disks, internet reachability -> ~/resense_results/<date>/setup/
#   2. base packages (git, curl, zstd, pigz, python3-venv, g++, iptables, jq, tmux ...)
#   3. Docker Engine from Docker's apt repository (fallbacks: DOCKER_APT_MIRROR, then Ubuntu's
#      docker.io); the user joins the docker group; the base image of docker/Dockerfile is pulled
#   4. ROS 2 Humble ros-base + rosbag2 + sqlite3 / mcap storage plugins + vision_msgs + CycloneDDS on
#      the HOST (the jury's console: `ros2 bag play`, `ros2 topic echo`). Ubuntu 22.04 only: on 24.04
#      (no Humble packages) the kit continues in Docker-only mode (the player runs from the image)
#   5. the repository: clone or update (--branch, default claude/nifty-pascal-lzgl78)
#   6. python venv (~/resense-venv) with the dependencies of pyproject.toml and its [dev] extra
#      (the project itself is not pip-installed: scripts run with PYTHONPATH=<repo>); open3d optional
#   7. the native kernels built in place (scripts/build_native.sh)
#   8. /data owned by the user; ~/resense_env.sh and the kit state ~/.resense_vm.env written
#   9. readiness summary
#
# Options:
#   --branch B            branch to check out (default claude/nifty-pascal-lzgl78)
#   --repo-dir D          checkout (default: the one this script is in, else ~/ReSense)
#   --data-dir D          data directory (default /data)
#   --venv D              python venv (default ~/resense-venv)
#   --registry-mirror U   Docker Hub mirror for the daemon, e.g. https://mirror.gcr.io (when Docker
#                         Hub is unreachable or rate-limited from the VM)
#   --no-update           do not fetch / pull an existing checkout
#   --skip-docker --skip-ros --skip-python --skip-native --skip-repo --skip-pull
#   -n, --dry-run         print what would be done (same as DRY_RUN=1); nothing is installed
#   -h, --help
# Environment: DOCKER_APT_MIRROR (default https://mirror.yandex.ru/mirrors/docker, used only when
#   download.docker.com fails), GITHUB_TOKEN (clone a private repository without storing the token).
# Exit: 0 ready; 1 a required step failed (the summary says which); 2 bad arguments / unsupported OS.
# Log: ~/resense_results/<date>/setup/setup_log.txt
set -Eeuo pipefail

SELF="${BASH_SOURCE[0]:-$0}"
SELF_DIR="$(cd "$(dirname "$SELF")" 2>/dev/null && pwd)" || SELF_DIR="$(pwd)"

# ---- bootstrap: run alone (piped from curl, copied without the kit) -> clone, re-run from there --
if [ ! -f "$SELF_DIR/lib.sh" ]; then
  B="claude/nifty-pascal-lzgl78"; RD="${REPO_DIR:-$HOME/ReSense}"
  args=("$@")
  for ((i = 0; i < ${#args[@]}; i++)); do
    case "${args[$i]}" in
      --branch) B="${args[$((i + 1))]:-$B}" ;;
      --repo-dir) RD="${args[$((i + 1))]:-$RD}" ;;
    esac
  done
  echo "== bootstrap: the kit is not next to this script; cloning $B into $RD"
  if ! command -v git >/dev/null 2>&1; then sudo apt-get update && sudo apt-get install -y git; fi
  if [ -d "$RD/.git" ]; then
    git -C "$RD" fetch origin "$B" && git -C "$RD" checkout "$B" && git -C "$RD" pull --ff-only origin "$B"
  else
    git clone --branch "$B" https://github.com/pmixay/ReSense "$RD"
  fi
  exec bash "$RD/scripts/vm/setup_vm.sh" "$@"
fi

# shellcheck source=scripts/vm/lib.sh
. "$SELF_DIR/lib.sh"

usage() { header_help "$SELF"; }
SKIP_DOCKER=0; SKIP_ROS=0; SKIP_PYTHON=0; SKIP_NATIVE=0; SKIP_REPO=0; SKIP_PULL=0; NO_UPDATE=0
REGISTRY_MIRROR="${REGISTRY_MIRROR:-}"
BRANCH_ARG=""
while [ $# -gt 0 ]; do
  case "$1" in
    --branch) BRANCH_ARG="${2:?--branch needs a value}"; shift 2 ;;
    --repo-dir) REPO_DIR="${2:?}"; shift 2 ;;
    --data-dir) DATA_DIR="${2:?}"; CACHE_DIR="$DATA_DIR/cache"; shift 2 ;;
    --venv) VENV="${2:?}"; shift 2 ;;
    --registry-mirror) REGISTRY_MIRROR="${2:?}"; shift 2 ;;
    --no-update) NO_UPDATE=1; shift ;;
    --skip-docker) SKIP_DOCKER=1; shift ;;
    --skip-ros) SKIP_ROS=1; shift ;;
    --skip-python) SKIP_PYTHON=1; shift ;;
    --skip-native) SKIP_NATIVE=1; shift ;;
    --skip-repo) SKIP_REPO=1; shift ;;
    --skip-pull) SKIP_PULL=1; shift ;;
    -n|--dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; die 2 "unknown argument: $1" ;;
  esac
done
BRANCH="${BRANCH_ARG:-${BRANCH:-$RESENSE_BRANCH_DEFAULT}}"
if [ "$(id -u)" -eq 0 ] && [ -n "${SUDO_USER:-}" ] && [ "$SUDO_USER" != root ]; then
  die 2 "run it as $SUDO_USER, without sudo: the script calls sudo itself (the venv, the checkout and ~/.resense_vm.env belong to the user)"
fi
if [ "$(id -u)" -ne 0 ] && [ "$DRY_RUN" != 1 ] && ! sudo -n true 2>/dev/null; then
  if [ -t 0 ]; then
    echo "sudo needs a password once:"; sudo -v || die 1 "no sudo rights"
  else
    die 1 "passwordless sudo is needed (the cloud image's default user has it)"
  fi
fi
TARGET_USER="$(id -un)"
TARGET_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)"; TARGET_HOME="${TARGET_HOME:-$HOME}"
DOCKER_APT_MIRROR="${DOCKER_APT_MIRROR:-https://mirror.yandex.ru/mirrors/docker}"
APT_OPTS=(-o DPkg::Lock::Timeout=600 -o Dpkg::Options::=--force-confdef -o Dpkg::Options::=--force-confold)
export DEBIAN_FRONTEND=noninteractive

OUT="$RESULTS_ROOT/$RUN_DATE/setup"
mkdir -p "$OUT"
start_log "$OUT/setup_log.txt"
trap 'warn "failed at line $LINENO: $BASH_COMMAND"' ERR
log "== ReSense VM setup (branch $BRANCH, repo $REPO_DIR, data $DATA_DIR, venv $VENV, dry run $DRY_RUN)"

declare -A STATUS=()
ORDER=()
record() { STATUS[$1]="$2"; ORDER+=("$1"); log "[$1] $2"; }
status() { printf '%s\n' "$*" > "$OUT/.status"; }     # called inside a step (a subshell)
apt_get() { as_root env DEBIAN_FRONTEND=noninteractive apt-get "${APT_OPTS[@]}" "$@"; }

# step <name> <required 0|1> <function>: run the function in a subshell with -e; record the result
FAILED_REQUIRED=()
step() {
  local name="$1" req="$2" fn="$3" rc msg
  hr; log "== $name"
  rm -f "$OUT/.status"
  trap - ERR
  set +e
  ( set -Eeuo pipefail; trap 'warn "$name: failed at line $LINENO: $BASH_COMMAND"' ERR; "$fn" )
  rc=$?
  set -e
  trap 'warn "failed at line $LINENO: $BASH_COMMAND"' ERR
  msg="$(cat "$OUT/.status" 2>/dev/null || true)"
  rm -f "$OUT/.status"
  if [ "$rc" -eq 0 ]; then
    record "$name" "${msg:-OK}"
  elif [ "$rc" -eq 99 ]; then
    record "$name" "${msg:-SKIPPED}"
  else
    record "$name" "FAILED (exit $rc${msg:+; $msg}; see $OUT/setup_log.txt)"
    if [ "$req" = 1 ]; then FAILED_REQUIRED+=("$name"); fi
  fi
  # a step may leave facts for the next ones in the state file
  if [ -f "$OUT/.facts" ]; then
    # shellcheck disable=SC1091
    . "$OUT/.facts"
  fi
  return 0
}
fact() { printf '%s=%q\n' "$1" "$2" >> "$OUT/.facts"; }
rm -f "$OUT/.facts"
ROS_MODE=""

# ---- 1. resources -------------------------------------------------------------------------------
s_resources() {
  {
    print_resources
    echo "user:      $TARGET_USER (uid $(id -u "$TARGET_USER")), home $TARGET_HOME"
    echo "cpu steal: $(cpu_steal_pct) % over 2 s (above ~5 % the vCPUs are shared: timing numbers are then noisy)"
    echo "## lsblk"; lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT 2>/dev/null || true
    echo "## internet (HTTP status; 000 = unreachable)"
    local u
    for u in https://github.com https://download.docker.com https://registry-1.docker.io/v2/ \
             http://packages.ros.org https://pypi.org https://drive.usercontent.google.com \
             https://cloud-api.yandex.net https://claude.ai; do
      printf '  %-45s %s\n' "$u" "$(curl -s -o /dev/null -m 10 -w '%{http_code}' "$u" 2>/dev/null || true)"
    done
  } | tee "$OUT/resources.txt"
  detect_resources
  {
    echo "OS_ID=$OS_ID"; echo "OS_VERSION_ID=$OS_VERSION_ID"; echo "OS_CODENAME=$OS_CODENAME"; echo "ARCH=$ARCH"
    echo "NPROC=$NPROC"; echo "CORES=$CORES"; echo "RAM_MB=$RAM_MB"
    echo "DATA_FREE_MB=$(free_mb "$DATA_DIR")"; echo "ROOT_FREE_MB=$(free_mb /)"
  } > "$OUT/resources.env"
  [ "$OS_ID" = ubuntu ] || { echo "this kit supports Ubuntu (22.04; 24.04 in Docker-only mode), found '$OS_ID'"; return 2; }
  case "$ARCH" in amd64|arm64) ;; *) echo "unsupported architecture $ARCH (ROS 2 Humble: amd64 / arm64)"; return 2 ;; esac
  if [ "$NPROC" -lt 8 ]; then
    warn "$NPROC vCPU: the bench stands in for the stand's 8-core i7-9700E; with fewer vCPUs its numbers are for this VM only"
  fi
  if [ "${THREADS_PER_CORE:-1}" = 2 ] && [ "$CORES" != "?" ] && [ "$CORES" -lt 8 ]; then
    warn "$NPROC vCPU are $CORES physical cores with hyper-threading; the i7-9700E has 8 physical cores, no HT"
  fi
  if [ "$RAM_MB" -lt 7500 ]; then warn "$(gb "$RAM_MB") GiB RAM: the gate runs fewer jobs; 16 GiB or more is comfortable"; fi
  local unmounted
  unmounted="$(lsblk -dn -o NAME,TYPE,RO,MOUNTPOINT 2>/dev/null \
    | awk '$2 == "disk" && $3 == 0 && $4 == "" && $1 !~ /^(zram|loop|sr|ram)/ { print $1 }' | while read -r d; do
    if [ -z "$(lsblk -n -o MOUNTPOINT "/dev/$d" 2>/dev/null | tr -d '[:space:]')" ]; then echo "$d"; fi; done)"
  if [ -n "$unmounted" ]; then
    warn "disk(s) without a mounted filesystem: $unmounted. To use one for the data (ERASES it):"
    echo "   sudo mkfs.ext4 -L resense-data /dev/<disk> && sudo mkdir -p $DATA_DIR && sudo mount /dev/<disk> $DATA_DIR"
    echo "   echo 'LABEL=resense-data $DATA_DIR ext4 defaults,nofail 0 2' | sudo tee -a /etc/fstab"
  fi
  status "OK: $NPROC vCPU / $CORES cores, $(gb "$RAM_MB") GiB RAM, $(gb "$(free_mb "$DATA_DIR")") GiB free for $DATA_DIR, ${OS_PRETTY}"
}

# ---- 2. base packages ---------------------------------------------------------------------------
BASE_PKGS=(ca-certificates curl gnupg lsb-release git jq zstd pigz unzip python3 python3-venv python3-pip
           python3-dev build-essential iptables iproute2 procps sysstat tmux htop lsof util-linux)
s_base() {
  local missing=() p
  for p in "${BASE_PKGS[@]}"; do dpkg -s "$p" >/dev/null 2>&1 || missing+=("$p"); done
  if [ ${#missing[@]} -eq 0 ]; then status "OK (already installed)"; return 0; fi
  log "installing: ${missing[*]}"
  apt_get update
  apt_get install -y --no-install-recommends "${missing[@]}"
}

# ---- 3. Docker Engine ---------------------------------------------------------------------------
s_docker() {
  [ "$SKIP_DOCKER" = 1 ] && { status "SKIPPED (--skip-docker)"; return 99; }
  local codename="$OS_CODENAME" arch="$ARCH" key=/etc/apt/keyrings/docker.asc src=""
  if have docker && root_q docker info >/dev/null 2>&1; then
    log "Docker already installed: $(root_q docker version --format '{{.Server.Version}}' 2>/dev/null || echo '?')"
  else
    as_root install -m 0755 -d /etc/apt/keyrings
    if run curl -fsSL -m 60 https://download.docker.com/linux/ubuntu/gpg -o /tmp/resense-docker.asc; then
      src="https://download.docker.com/linux/ubuntu"
    elif run curl -fsSL -m 60 "$DOCKER_APT_MIRROR/gpg" -o /tmp/resense-docker.asc; then
      warn "download.docker.com unreachable: using the mirror $DOCKER_APT_MIRROR"
      src="$DOCKER_APT_MIRROR"
    fi
    if [ -n "$src" ]; then
      as_root install -m 0644 /tmp/resense-docker.asc "$key"
      as_root_sh "echo 'deb [arch=$arch signed-by=$key] $src $codename stable' > /etc/apt/sources.list.d/docker.list"
      apt_get update
      if ! apt_get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin; then
        warn "docker-ce from $src failed; falling back to Ubuntu's docker.io"
        as_root rm -f /etc/apt/sources.list.d/docker.list
        apt_get update
        src=""
      fi
    fi
    if [ -z "$src" ]; then
      apt_get install -y docker.io
      apt_get install -y docker-buildx docker-compose-v2 \
        || warn "no buildx for docker.io here: builds use the legacy builder (export_image.sh warns; docker load still works)"
    fi
  fi
  as_root systemctl enable --now docker
  if ! id -nG "$TARGET_USER" | tr ' ' '\n' | grep -qx docker; then
    as_root usermod -aG docker "$TARGET_USER"
    warn "$TARGET_USER joined the docker group: log out and back in (or run 'newgrp docker'); run_plan.sh re-execs itself with 'sg docker' meanwhile"
  fi
  if [ -n "$REGISTRY_MIRROR" ]; then
    log "Docker Hub mirror for the daemon: $REGISTRY_MIRROR"
    as_root_sh "python3 - '$REGISTRY_MIRROR' <<'PY'
import json, os, sys
p = '/etc/docker/daemon.json'
d = json.load(open(p)) if os.path.exists(p) and os.path.getsize(p) else {}
m = d.setdefault('registry-mirrors', [])
if sys.argv[1] not in m:
    m.append(sys.argv[1])
os.makedirs('/etc/docker', exist_ok=True)
json.dump(d, open(p, 'w'), indent=2)
PY"
    as_root systemctl restart docker
  fi
  [ "$DRY_RUN" = 1 ] && { status "DRY RUN"; return 0; }
  local v bx
  v="$(root_q docker version --format '{{.Server.Version}}')"
  bx="$(root_q docker buildx version 2>/dev/null | head -n 1 || echo 'no buildx')"
  local hub
  hub="$(curl -s -o /dev/null -m 10 -w '%{http_code}' https://registry-1.docker.io/v2/ || true)"
  if [ "$hub" != 401 ] && [ -z "$REGISTRY_MIRROR" ]; then
    warn "Docker Hub answered '$hub' (401 expected): if the base image cannot be pulled, re-run with --registry-mirror https://mirror.gcr.io"
  fi
  local base
  base="$(sed -n 's/^FROM[[:space:]]\{1,\}\([^[:space:]]\{1,\}\).*/\1/p' "$REPO_DIR/docker/Dockerfile" 2>/dev/null | head -n 1)"
  if [ "$SKIP_PULL" != 1 ] && [ -n "$base" ]; then
    if as_root docker pull -q "$base" >/dev/null; then
      log "base image $base pulled"
    else
      warn "could not pull $base: the build (dry run, bench, export) needs it; try --registry-mirror https://mirror.gcr.io"
      status "PARTIAL: Docker $v ($bx) runs, but $base could not be pulled"
      return 0
    fi
  fi
  status "OK: Docker $v, $bx; user $TARGET_USER in group docker"
}

# ---- 4. ROS 2 Humble on the host ----------------------------------------------------------------
ROS_PKGS=(ros-humble-ros-base ros-humble-rosbag2 ros-humble-rosbag2-storage-default-plugins
          ros-humble-rosbag2-storage-mcap ros-humble-vision-msgs ros-humble-rmw-fastrtps-cpp
          ros-humble-rmw-cyclonedds-cpp)
s_ros() {
  if [ "$SKIP_ROS" = 1 ]; then
    if has_host_ros; then fact ROS_MODE host; else fact ROS_MODE docker-only; fi
    status "SKIPPED (--skip-ros)"; return 99
  fi
  if [ "$OS_CODENAME" != jammy ]; then
    fact ROS_MODE docker-only
    warn "ROS 2 Humble has apt packages for Ubuntu 22.04 (jammy) only; this VM is ${OS_PRETTY:-$OS_CODENAME}."
    warn "Continuing in Docker-only mode: the console player runs from the image (scripts/console_test.sh, uid 1000);"
    warn "the host-console check with stock Fast DDS (CAPTAIN C4) needs an Ubuntu 22.04 VM."
    status "SKIPPED: ${OS_PRETTY:-$OS_CODENAME} has no ROS 2 Humble packages -> Docker-only mode"
    return 99
  fi
  local missing=() p
  for p in "${ROS_PKGS[@]}"; do dpkg -s "$p" >/dev/null 2>&1 || missing+=("$p"); done
  if [ ${#missing[@]} -gt 0 ]; then
    if ! dpkg -s ros2-apt-source >/dev/null 2>&1 && [ ! -f /etc/apt/sources.list.d/ros2.list ] \
        && [ ! -f /etc/apt/sources.list.d/ros2.sources ]; then
      apt_get install -y software-properties-common
      as_root add-apt-repository -y universe
      local ver=""
      ver="$(curl -fsSLI -o /dev/null -m 30 -w '%{url_effective}' https://github.com/ros-infrastructure/ros-apt-source/releases/latest 2>/dev/null | sed -n 's#.*/tag/##p')" || ver=""
      if [ -n "$ver" ] && run curl -fsSL -m 120 -o /tmp/ros2-apt-source.deb \
          "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ver}/ros2-apt-source_${ver}.${OS_CODENAME}_all.deb"; then
        log "ROS apt source: ros2-apt-source $ver (the ROS 2 docs' current method)"
        apt_get install -y /tmp/ros2-apt-source.deb
      else
        warn "ros2-apt-source not downloadable; using the key from rosdistro (the older documented method)"
        as_root curl -fsSL -m 60 https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
        as_root_sh "echo 'deb [arch=$ARCH signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $OS_CODENAME main' > /etc/apt/sources.list.d/ros2.list"
      fi
    fi
    apt_get update
    apt_get install -y "${missing[@]}"
  fi
  fact ROS_MODE host
  [ "$DRY_RUN" = 1 ] && { status "DRY RUN"; return 0; }
  local out
  out="$(bash -c 'set +u; . /opt/ros/humble/setup.bash; ros2 bag --help >/dev/null && ros2 pkg prefix rosbag2_storage_mcap >/dev/null && ros2 pkg prefix rosbag2_storage_default_plugins >/dev/null && echo ok' 2>&1 | tail -n 1)"
  [ "$out" = ok ] || { echo "ros2 check failed: $out"; return 1; }
  status "OK: ROS 2 Humble on the host (ros2 bag + sqlite3 / mcap plugins, vision_msgs, Fast DDS + CycloneDDS)"
}

# ---- 5. repository ------------------------------------------------------------------------------
git_auth() {   # extra git args for a private repository (the token is never written to .git/config)
  if [ -n "${GITHUB_TOKEN:-}" ]; then
    printf '%s\n' -c "http.https://github.com/.extraheader=AUTHORIZATION: basic $(printf 'x-access-token:%s' "$GITHUB_TOKEN" | base64 -w0)"
  fi
}
s_repo() {
  [ "$SKIP_REPO" = 1 ] && { status "SKIPPED (--skip-repo): $(git -C "$REPO_DIR" rev-parse --short HEAD 2>/dev/null || echo '?')"; return 99; }
  local auth=()
  mapfile -t auth < <(git_auth)
  if [ -d "$REPO_DIR/.git" ] || git -C "$REPO_DIR" rev-parse --git-dir >/dev/null 2>&1; then
    if [ "$NO_UPDATE" = 1 ]; then
      log "--no-update: leaving $REPO_DIR as it is"
    elif [ -n "$(git -C "$REPO_DIR" status --porcelain --untracked-files=no)" ]; then
      warn "$REPO_DIR has uncommitted changes: not updated (commit or stash them, then re-run)"
    else
      run git "${auth[@]}" -C "$REPO_DIR" fetch origin "$BRANCH"
      if git -C "$REPO_DIR" show-ref --verify --quiet "refs/heads/$BRANCH"; then
        run git -C "$REPO_DIR" checkout "$BRANCH"
      else
        run git -C "$REPO_DIR" checkout -b "$BRANCH" --track "origin/$BRANCH"
      fi
      run git "${auth[@]}" -C "$REPO_DIR" pull --ff-only origin "$BRANCH"
    fi
  else
    if ! run git "${auth[@]}" clone --branch "$BRANCH" "$RESENSE_REPO_URL" "$REPO_DIR"; then
      echo "clone failed. A private repository needs credentials: GITHUB_TOKEN=<token> $0 ..., or 'gh auth login' first"
      return 1
    fi
  fi
  [ "$DRY_RUN" = 1 ] && { status "DRY RUN"; return 0; }
  status "OK: $REPO_DIR at $(git -C "$REPO_DIR" rev-parse --short HEAD) ($(git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD))"
}

# ---- 6. python venv -----------------------------------------------------------------------------
s_python() {
  [ "$SKIP_PYTHON" = 1 ] && { status "SKIPPED (--skip-python)"; return 99; }
  [ -f "$REPO_DIR/pyproject.toml" ] || { echo "no $REPO_DIR/pyproject.toml"; return 1; }
  [ -x "$VENV/bin/python" ] || run python3 -m venv "$VENV"
  run "$VENV/bin/python" -m pip install -q --upgrade pip wheel setuptools
  [ "$DRY_RUN" = 1 ] && { status "DRY RUN"; return 0; }
  local reqs=() r core=() optional=()
  mapfile -t reqs < <("$VENV/bin/python" - "$REPO_DIR/pyproject.toml" <<'PY'
import sys
try:
    import tomllib as toml
except ImportError:
    try:
        import tomli as toml
    except ImportError:
        from pip._vendor import tomli as toml
with open(sys.argv[1], "rb") as fh:
    project = toml.load(fh)["project"]
for req in project["dependencies"] + project["optional-dependencies"]["dev"]:
    print(req)
PY
)
  [ ${#reqs[@]} -gt 0 ] || { echo "no dependencies read from pyproject.toml"; return 1; }
  for r in "${reqs[@]}"; do
    case "$r" in open3d*) optional+=("$r") ;; *) core+=("$r") ;; esac
  done
  log "pip install (from pyproject.toml, the project itself is not installed): ${core[*]}"
  "$VENV/bin/python" -m pip install -q "${core[@]}"
  local o3d="not installed"
  if [ ${#optional[@]} -gt 0 ]; then
    if "$VENV/bin/python" -m pip install -q "${optional[@]}"; then o3d="installed"; else
      warn "open3d did not install (only the synthetic-tunnel tests need it; the kit does not)"; fi
  fi
  "$VENV/bin/python" -m pip install -q gdown || warn "gdown not installed (only a fallback for the Google Drive download)"
  "$VENV/bin/python" -c "import numpy, scipy, sklearn, yaml, rosbags, zstandard; print('python ok, numpy', numpy.__version__)"
  status "OK: $VENV ($("$VENV/bin/python" -V 2>&1)), pyproject deps + [dev], open3d $o3d"
}

# ---- 7. native kernels --------------------------------------------------------------------------
s_native() {
  [ "$SKIP_NATIVE" = 1 ] && { status "SKIPPED (--skip-native)"; return 99; }
  [ -x "$REPO_DIR/scripts/build_native.sh" ] || { status "SKIPPED: no scripts/build_native.sh on this branch"; return 99; }
  run env PATH="$VENV/bin:$PATH" "$REPO_DIR/scripts/build_native.sh"
  [ "$DRY_RUN" = 1 ] && { status "DRY RUN"; return 0; }
  local st
  st="$(cd "$REPO_DIR" && PYTHONPATH="$REPO_DIR" "$VENV/bin/python" -c 'from resense import _native; print(_native.status())')"
  status "OK: $st"
}

# ---- 8. data directory, env file, state -----------------------------------------------------------
s_files() {
  if [ ! -d "$DATA_DIR" ] || [ ! -w "$DATA_DIR" ]; then
    as_root mkdir -p "$DATA_DIR"
    as_root chown "$TARGET_USER:$(id -gn "$TARGET_USER")" "$DATA_DIR"
  fi
  run mkdir -p "$CACHE_DIR" "$RESULTS_ROOT" "$DIST_DIR"
  local mode="${ROS_MODE:-}"
  if [ -z "$mode" ]; then if has_host_ros; then mode=host; else mode=docker-only; fi; fi
  if [ "$DRY_RUN" = 1 ]; then log "DRY: would write $VM_STATE_FILE and $TARGET_HOME/resense_env.sh"; return 0; fi
  cat > "$VM_STATE_FILE" <<EOF
# written by scripts/vm/setup_vm.sh on $(date -Is); read by the other scripts of scripts/vm/
REPO_DIR=$REPO_DIR
DATA_DIR=$DATA_DIR
CACHE_DIR=$CACHE_DIR
VENV=$VENV
RESULTS_ROOT=$RESULTS_ROOT
DIST_DIR=$DIST_DIR
ROS_MODE=$mode
BRANCH=$BRANCH
EOF
  cat > "$TARGET_HOME/resense_env.sh" <<EOF
# ReSense VM shell environment (scripts/vm/setup_vm.sh): source ~/resense_env.sh
export RESENSE_REPO="$REPO_DIR" RESENSE_DATA="$DATA_DIR/for_hackathon" RESENSE_CACHE="$CACHE_DIR"
if [ -f /opt/ros/humble/setup.bash ]; then . /opt/ros/humble/setup.bash; fi
if [ -f "$VENV/bin/activate" ]; then . "$VENV/bin/activate"; fi
export PYTHONPATH="$REPO_DIR\${PYTHONPATH:+:\$PYTHONPATH}"
cd "$REPO_DIR" 2>/dev/null || true
EOF
  status "OK: $DATA_DIR writable, $VM_STATE_FILE (ROS_MODE=$mode), $TARGET_HOME/resense_env.sh"
}

step resources 1 s_resources
# shellcheck disable=SC1091  # written by s_resources
[ -f "$OUT/resources.env" ] && . "$OUT/resources.env"
if [ ${#FAILED_REQUIRED[@]} -gt 0 ]; then die 2 "unsupported machine (above)"; fi
detect_resources
step base 1 s_base
[ ${#FAILED_REQUIRED[@]} -eq 0 ] && step repo 1 s_repo
[ ${#FAILED_REQUIRED[@]} -eq 0 ] && step docker 1 s_docker
[ ${#FAILED_REQUIRED[@]} -eq 0 ] && step ros 0 s_ros
[ ${#FAILED_REQUIRED[@]} -eq 0 ] && step python 1 s_python
[ ${#FAILED_REQUIRED[@]} -eq 0 ] && step native 0 s_native
[ ${#FAILED_REQUIRED[@]} -eq 0 ] && step files 1 s_files
trap - ERR

# ---- 9. readiness summary -----------------------------------------------------------------------
hr
{
  echo "ReSense VM readiness, $(date -Is)"
  printf '  %-10s %s\n' "branch" "$BRANCH"
  for k in "${ORDER[@]}"; do printf '  %-10s %s\n' "$k" "${STATUS[$k]}"; done
  printf '  %-10s %s\n' "ros mode" "${ROS_MODE:-?} (host = the jury's console path can be rehearsed; docker-only = player from the image)"
  echo
  if [ ${#FAILED_REQUIRED[@]} -gt 0 ]; then
    echo "NOT READY: ${FAILED_REQUIRED[*]} failed (log: $OUT/setup_log.txt). Fix and re-run; finished steps are skipped."
  else
    echo "READY. Next (new login first if you just joined the docker group):"
    echo "  source ~/resense_env.sh"
    echo "  $REPO_DIR/scripts/vm/fetch_data.sh --plan      # what fits on the disk"
    echo "  $REPO_DIR/scripts/vm/fetch_data.sh             # data + frame caches (~1-2 h)"
    echo "  $REPO_DIR/scripts/vm/run_plan.sh status"
    echo "  $REPO_DIR/scripts/vm/run_plan.sh all           # or step by step: scripts/vm/AGENT_BRIEF.md"
  fi
} | tee "$OUT/summary.txt"
rm -f "$OUT/.facts"
[ ${#FAILED_REQUIRED[@]} -eq 0 ]
