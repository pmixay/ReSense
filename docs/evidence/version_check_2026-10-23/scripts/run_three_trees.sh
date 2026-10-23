#!/usr/bin/env bash
export PATH=/tmp/claude-0/venv/bin:$PATH OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
mkdir -p /tmp/claude-0/-home-user-ReSense/7cd22cbc-ee8e-51b7-bbd1-967a82c07b76/scratchpad/out
for v in v1.0.0 v1.2.0 head; do
 for b in doubleT_obstacle roundT_doubleT; do
  ( cd /tmp/claude-0/-home-user-ReSense/7cd22cbc-ee8e-51b7-bbd1-967a82c07b76/scratchpad/wt/$v && RESENSE_REPO=/tmp/claude-0/-home-user-ReSense/7cd22cbc-ee8e-51b7-bbd1-967a82c07b76/scratchpad/wt/$v PYTHONPATH=/tmp/claude-0/-home-user-ReSense/7cd22cbc-ee8e-51b7-bbd1-967a82c07b76/scratchpad/wt/$v python -m resense.cli run --bag /tmp/claude-0/-home-user-ReSense/7cd22cbc-ee8e-51b7-bbd1-967a82c07b76/scratchpad/data/for_hackathon/$b --out /tmp/claude-0/-home-user-ReSense/7cd22cbc-ee8e-51b7-bbd1-967a82c07b76/scratchpad/out/${v}_$b.jsonl --quiet > /tmp/claude-0/-home-user-ReSense/7cd22cbc-ee8e-51b7-bbd1-967a82c07b76/scratchpad/out/${v}_$b.log 2>&1; echo "$v $b exit $?" >> /tmp/claude-0/-home-user-ReSense/7cd22cbc-ee8e-51b7-bbd1-967a82c07b76/scratchpad/out/done.txt )
 done
done
