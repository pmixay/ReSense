# source with the checkout as $1:  . env.sh /home/user/ReSense
. /home/user/venv/bin/activate
export RESENSE_REPO=${1:-/home/user/ReSense}
export PYTHONPATH=$RESENSE_REPO:$RESENSE_REPO/ros2_ws/src/resense_ros
export OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
