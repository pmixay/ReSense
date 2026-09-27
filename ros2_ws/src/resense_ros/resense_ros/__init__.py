"""ReSense ROS 2 package.

Single-threaded BLAS / OpenMP unless the environment says otherwise (25.09). docker/Dockerfile
sets the same three variables; a node started outside the image (a host colcon build) would
otherwise run numpy's BLAS thread pool on the cores the bag player needs: 256 against 67 ms per
360-degree frame of the node's path on a busy 4-vCPU sandbox (EXPERIMENTS.md section 3a). Set
here because the package is imported before ``detector_node`` imports numpy; an explicit value
(``OPENBLAS_NUM_THREADS=4 ros2 launch ...``) wins.
"""
import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_var, "1")
