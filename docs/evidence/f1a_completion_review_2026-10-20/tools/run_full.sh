#!/bin/bash
# usage: run_full.sh <wt> <name>   -- the full pytest suite on checkout <wt>
S=/tmp/claude-0/-home-user-ReSense/2f98805c-ba30-5c4f-b1a6-a591bfc61cdc/scratchpad/f1a_review
$S/run_in.sh $1 $S/venv/bin/python -m pytest -q -rs -p no:cacheprovider --junitxml=$S/out/$2.xml tests > $S/out/$2.log 2>&1
echo "exit $?" >> $S/out/$2.log
