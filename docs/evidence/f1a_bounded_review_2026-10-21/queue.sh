#!/bin/bash
# queue.sh <outdir> "side family [--trace]" ...   (sequential)
out=$1; shift
for job in "$@"; do
  set -- $job
  /home/user/ReSense/docs/evidence/f1a_bounded_review_2026-10-21/run_attack.sh "$1" "$out" "$2" "${3:-}"
done
echo QUEUE_DONE
