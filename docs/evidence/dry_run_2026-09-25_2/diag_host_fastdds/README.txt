CORRECTION (25.09 evening, third team VM, ../dry_run_2026-09-25_3/README.txt): every "fastdds" host run in
this folder, and ../host_console_fastdds.txt, ran a CycloneDDS player. The host's ROS 2 was installed with
ros-humble-ros-base and ros-humble-rmw-cyclonedds-cpp in one apt call; ros-humble-rmw-implementation takes
"rmw-fastrtps-cpp | rmw-cyclonedds-cpp | ...", so no Fast DDS RMW was installed and RMW_IMPLEMENTATION unset
loaded rmw_cyclonedds_cpp. The table below therefore shows CycloneDDS at rmem_max 212992 (FAIL, as on 25.09
morning) and at 32 MiB (PASS), not stock Fast DDS. A genuine stock Fast DDS player (rmw_fastrtps_cpp,
fastrtps 2.6.12, checked in /proc/<pid>/maps) passed at 212992 on the third VM, 2 of 2 over UDP and 2 of 2 in
shm mode, as it had on the first VM (../../dry_run_2026-09-25/host_fastdds.txt).

Diagnostic follow-up of the host console with stock Fast DDS (VM_GUIDE §4.2), 25.09 afternoon, second
team VM (8 vCPU = 4 physical cores, Ubuntu 22.04, kernel 5.15.0-191, host ROS 2 Humble from apt: rosbag2
0.15.17, fastrtps 2.6.12), code 76bf24e, image resense:latest built on this VM. Bags from a RAM tmpfs.
Each run: the node container on its default command (--net=host --ipc=host); on the HOST as uid 1000,
RMW_IMPLEMENTATION unset (rmw_fastrtps_cpp), no Fast DDS profile: ros2 topic echo of /resense/decision and
/resense/status, ros2 bag play roundT_doubleT, then doubleT_obstacle (--delay 3), as in VM_GUIDE §4.2.

run (file host_console_fastdds_<tag>.txt)   net.core.rmem_max   node's UDP profile          360-degree clouds (doubleT_obstacle)   check
../host_console_fastdds.txt (the §4.2 run)  212992 (default)    image (32 MiB requested)     1 of 201 processed                    FAIL
repeat                                      212992              image                        0-1                                   FAIL
repeat2                                     212992              image                        none (1 recording seen)               FAIL
profile8mib                                 212992              the 25.09 profile (8 MiB),   0-1                                   FAIL
profile8mib_repeat                          212992                mounted over the image's   0-1                                   FAIL
rmem32                                      33554432            image                        144 STOP at 55.6-56.5 m               PASS
(../host_console_cyclonedds.txt: rmw_cyclonedds_cpp at rmem_max 33554432: 144 STOP, PASS)

The 120-degree roundT_doubleT (~3 MB clouds) arrives in every run. The profile8mib runs mount
fastdds_udp.xml of ead8502 (receiveBufferSize 8388608) over /opt/resense/fastdds_udp.xml as a runtime
override only (NODE_ARGS in host_console.sh); nothing in the repository was changed. On 25.09 morning the
same host console passed on the first team VM at rmem_max 212992 (dry_run_2026-09-25/host_fastdds.txt,
137 STOP, code 7290873), so at Ubuntu's default buffer the result depends on the machine; with rmem_max
at 32 MiB it passed here too. The Docker stock player (ct_stock, PLAYER_DDS=stock) passed at 212992 on
this VM. The offline README jury console (offline_2026-09-25_2/jury_console.txt) failed the same way
(6 of 201 clouds).
