# DDS transport of the ReSense image; docker/entrypoint.sh sources this and calls
# resense_dds_transport before it execs the command.
#
#   docker run --rm -it --net=host --ipc=host resense                     # udp: Fast DDS over UDPv4 only (default)
#   docker run --rm -it --net=host --ipc=host -e RESENSE_DDS=shm resense  # opt-in: shared memory + UDPv4
#
# udp (RESENSE_DDS unset, empty or udp) leaves the container as the image has it:
# FASTRTPS_DEFAULT_PROFILES_FILE stays /opt/resense/fastdds_udp.xml (or what `docker run -e` set) and
# nothing is started. shm points FASTRTPS_DEFAULT_PROFILES_FILE at fastdds_shm_udp.xml and starts
# fastdds_shm_share.py in the background, before the node creates its files: a player of another uid
# can then write into the node's shared-memory queues (that script's header has the Fast DDS source
# behind it). shm falls back to udp with a WARN when the container is not in the host's IPC namespace
# (no --ipc=host: a stock Fast DDS player on the host would take the node's shared-memory locators
# for its own /dev/shm and reach nothing, ProxyDataFilters.hpp:60-81), when the profile is missing,
# or when the script finds /dev/shm or /proc unusable. Any other value: WARN, udp. One INFO line names
# the mode. Never fails: the entrypoint runs under `set -e`.
#
# RESENSE_DDS_HOME, RESENSE_IPC_NS, RESENSE_SHM_DIR, RESENSE_PYTHON: other paths, for the tests only
# (tests/test_dds_transport.py).

# The kernel's fixed /proc inode of the initial IPC namespace (PROC_IPC_INIT_INO, include/linux/proc_ns.h);
# `docker run --ipc=host` joins it and bind-mounts the host's /dev/shm.
RESENSE_HOST_IPC_NS="ipc:[4026531839]"

resense_dds_transport() {
  local home="${RESENSE_DDS_HOME:-/opt/resense}" ipc_ns="${RESENSE_IPC_NS:-/proc/self/ns/ipc}"
  local shm_dir="${RESENSE_SHM_DIR:-/dev/shm}" py="${RESENSE_PYTHON:-python3}"
  local mode="${RESENSE_DDS:-udp}" why=""
  mode="${mode,,}"
  case "$mode" in
    udp) ;;
    shm)
      if [ "$(readlink "$ipc_ns" 2>/dev/null)" != "$RESENSE_HOST_IPC_NS" ]; then
        why="it needs --ipc=host (the host's /dev/shm), and this container has an IPC namespace of its own"
      elif [ ! -f "$home/fastdds_shm_udp.xml" ]; then
        why="$home/fastdds_shm_udp.xml is missing"
      elif ! "$py" "$home/fastdds_shm_share.py" --check --shm-dir "$shm_dir" </dev/null >/dev/null 2>&1; then
        why="$shm_dir cannot be shared from here (fastdds_shm_share.py --check failed)"
      fi
      if [ -n "$why" ]; then
        echo "[WARN] [resense.dds]: RESENSE_DDS=shm: $why; staying on UDP only" >&2
        mode=udp
      fi ;;
    *)
      echo "[WARN] [resense.dds]: RESENSE_DDS='$RESENSE_DDS' is neither udp nor shm; staying on UDP only" >&2
      mode=udp ;;
  esac
  if [ "$mode" = shm ]; then
    export FASTRTPS_DEFAULT_PROFILES_FILE="$home/fastdds_shm_udp.xml"
    "$py" "$home/fastdds_shm_share.py" --shm-dir "$shm_dir" </dev/null &
    echo "[INFO] [resense.dds]: DDS transport: shm, shared memory + UDPv4 ($FASTRTPS_DEFAULT_PROFILES_FILE);" \
         "this container's Fast DDS files in $shm_dir are opened to other users (fastdds_shm_share.py, pid $!)" >&2
  elif [ "${FASTRTPS_DEFAULT_PROFILES_FILE-}" = "$home/fastdds_udp.xml" ]; then
    echo "[INFO] [resense.dds]: DDS transport: udp, UDPv4 only ($FASTRTPS_DEFAULT_PROFILES_FILE);" \
         "-e RESENSE_DDS=shm adds shared memory" >&2
  else
    echo "[INFO] [resense.dds]: DDS transport: udp mode, the Fast DDS profile of the environment:" \
         "FASTRTPS_DEFAULT_PROFILES_FILE='${FASTRTPS_DEFAULT_PROFILES_FILE-}'" >&2
  fi
  return 0
}
