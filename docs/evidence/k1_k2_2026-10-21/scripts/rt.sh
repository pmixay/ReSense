#!/bin/bash
# rt.sh <tag> <repo> <bag> <name> <args...> : one range_test job; cache via /data/dev/range/c_<tag>
tag=$1; repo=$2; bag=$3; name=$4; shift 4
. /data/work/env.sh; setrepo $repo; cd $repo
python /home/user/ReSense/docs/evidence/k1_k2_gauge_2026-10-19/tools/range_test.py /data/dev/range/c_$tag/$bag /data/icp/icp_$bag.json /data/dev/range/${tag}_$name "$@" > /data/dev/range/${tag}_$name.log 2>&1
python3 -c "import json;s=json.load(open('/data/dev/range/${tag}_$name.json'))['summary'];print('$tag $name',{k:s[k] for k in s if k in ('first_visible_X','first_stop_X','held_from_X','stop_frames','visible_frames','bins')})"
