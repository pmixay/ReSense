#!/bin/bash
export PATH=/home/user/venv/rs/bin:$PATH
python -c "import numpy; assert numpy.__version__ == '1.26.4'"
date -u
python /data/work_k2/scripts/range_subset.py /data/work_k2/trees/base base /data/work_k2/range -j 1
date -u
python /data/work_k2/scripts/range_subset.py /data/work_k2/trees/v5 v5b /data/work_k2/range -j 1
date -u; echo RANGE_DONE
