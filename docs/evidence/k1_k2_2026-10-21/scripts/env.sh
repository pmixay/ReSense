. /opt/venv/bin/activate
export OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
setrepo() { export RESENSE_REPO=$1 PYTHONPATH=$1:$1/ros2_ws/src/resense_ros; }
setrepo /home/user/ReSense
U="--set track.axis_joint_fit=true --set track.axis_joint_range=false --set track.axis_joint_min_curvature=0.0001 --set track.axis_joint_union=true"
T=/home/user/ReSense/docs/evidence/k1_k2_2026-10-21/scripts/trace_decoded.py
