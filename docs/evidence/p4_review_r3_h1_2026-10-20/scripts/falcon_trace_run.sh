#!/bin/bash
# Falcon once more, default config, with the read-only switch trace (falcon_switch_trace.py); stream sha256 kept.
set -u
W=/home/user/wt_ship; O=/home/user/p4r/falcon
export PATH=/home/user/venv/rs/bin:$PATH OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 RESENSE_REPO=$W PYTHONPATH=$W
HREF=$(curl -fsS --get --data-urlencode "public_key=https://disk.yandex.ru/d/SfBeRHbs8bNJAQ" \
  --data-urlencode "path=/falcon_test.zst" https://cloud-api.yandex.net/v1/disk/public/resources/download \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["href"])')
date -u +"start %T"
curl -fsSL "$HREF" | tee >(sha256sum > $O/trace_stream.sha256) \
  | python /home/user/p4r/scripts/falcon_switch_trace.py /dev/stdin --out $O/default_traced > $O/default_traced.log 2>&1
echo "pipe ${PIPESTATUS[*]}"; date -u +"end %T"; sleep 3; cat $O/trace_stream.sha256; echo FTRACE_DONE
