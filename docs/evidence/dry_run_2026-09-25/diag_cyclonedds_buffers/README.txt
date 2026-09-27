Diagnostic follow-up of the step host_cyclonedds (FAIL: recording 2, doubleT_obstacle, 0 alarm frames), 25.09 ~09:40 UTC.
Same VM, same image (commit 7290873), bags from a RAM tmpfs. host_console.sh (this folder) is a minimal copy of the
kit's host_console step: the node container on its default command (--net=host --ipc=host), and on the HOST as uid 1000
with stock ROS 2 Humble and RMW_IMPLEMENTATION=rmw_cyclonedds_cpp: ros2 bag play <bag> --delay 3, ros2 topic echo of
/resense/decision and /resense/status. One bag only: doubleT_obstacle (360 deg, ~10 MB per cloud).

host_cyclone_default/  net.core.rmem_max = rmem_default = 212992 (Ubuntu default): the node received no cloud at all
                       (node.log has no "input 1" line; 55 status messages, all FAULT / no input).
host_cyclone_32mb/     net.core.{r,w}mem_{max,default} = 33554432 for this run only (restored to 212992 right after):
                       the clouds arrive: 132 status messages, 111 alarm frames at 55.8-56.2 m, latency p95 72 ms,
                       4 frames dropped after the first 5 s; one detector restart on "header stamps jumped by -0.8 s".
Reading: the node's Fast DDS reader loses CycloneDDS's fragment bursts of the 10 MB clouds with the stock socket buffer;
a stock Fast DDS player (step host_fastdds) is not affected. The 120 deg recording (~3 MB clouds) arrives either way.
