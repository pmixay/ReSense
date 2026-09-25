Runs of 25.09 evening on a third team VM (Xeon Icelake 2.0 GHz, 8 vCPU = 4 physical cores, Ubuntu 22.04,
Docker 29.8.1), code d4b396e (the transport fixes of be39362: README jury step 0, opt-in RESENSE_DDS=shm;
nothing in docker/, resense/ or the node changed after it), image built by dry_run.sh --no-cache as the
VM's first build, the two original bags from a RAM tmpfs copy. Scripts: g_fix.sh (this folder).

HOST ROS NOTE. The host's ROS 2 Humble was installed as VM_GUIDE §1 says (ros-humble-ros-base, and
ros-humble-rmw-cyclonedds-cpp in the same apt call). ros-humble-rmw-implementation depends on
"rmw-fastrtps-cpp | rmw-cyclonedds-cpp | rmw-connextdds", so that call installs NO Fast DDS RMW, and a
player with RMW_IMPLEMENTATION unset runs CycloneDDS (checked in /proc/<pid>/maps: librmw_cyclonedds_cpp.so,
libddsc.so.0.10.5). The same happened on the second VM (dry_run_2026-09-25_2): every "fastdds" host run
there was a CycloneDDS player. Here ros-humble-rmw-fastrtps-cpp was then installed (fastrtps 2.6.12, as in
the image) and every later host run records the RMW it loaded ("RMW loaded" in *_console4.txt).

run (file)                          node      player (verified)        rmem_max   result
dry_obstacle / dry_clear            udp       in the container         212992     PASS / PASS (0 alarm frames)
host_jury_step0_cyclonedds*         udp       CycloneDDS (no Fast DDS) 33554432   PASS, 152 STOP
host_shm_cyclonedds_rmem212992*     shm       CycloneDDS (no Fast DDS) 212992     FAIL: the 360-degree recording never arrived
host_shm_cyclonedds*                shm       CycloneDDS               33554432   PASS, 153 STOP; console 4: no Fast DDS port mapped
ct_shm*                             shm       stock Fast DDS in Docker 212992     PASS over shared memory
host_jury_step0_fastdds*            udp       stock Fast DDS 2.6.12    33554432   PASS, 153 STOP
host_fastdds_udp*, _udp2*           udp       stock Fast DDS 2.6.12    212992     PASS, PASS (152 / 150 STOP)
host_shm_fastdds*, _fastdds2*       shm       stock Fast DDS 2.6.12    212992     PASS, PASS (148 / 146 STOP); console 4: the
                                                                                  player maps the node's root 666 fastrtps_port7411

Reading: a stock Fast DDS player reaches the node at Ubuntu's default rmem_max over UDP (2 of 2 here; the
first VM of 25.09 too) and over shared memory in shm mode (2 of 2); a CycloneDDS player needs rmem_max
32 MiB in either mode (it cannot use Fast DDS shared memory).
