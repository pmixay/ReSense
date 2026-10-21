import json,sys,os
sys.path.insert(0,'scripts'); sys.path.insert(0,'.')
import numpy as np, yaml
from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import frame_from_compact
from scripts.cache_io import cache_files, cache_file_stem, load_cache_array, load_cache_stamps
w=sys.argv[1]; piece=int(sys.argv[2]); n=int(sys.argv[3]); out=sys.argv[4]
raw=yaml.safe_load(open(w+'/config.yaml')); cfg=DetectorConfig.from_dict(raw.get('resense',raw)); assert cfg.track.axis_joint_union == ('cand' in w)
d='/data/cache/new_data'; files=cache_files(d); st=load_cache_stamps(d); part=list(np.array_split(np.array(files),8)[piece])
det=Detector(cfg)
with open(out,'w') as fh:
    for i,f in enumerate(part[:n]):
        stem=cache_file_stem(f); fr=frame_from_compact(load_cache_array(f),cfg.sensor,stamp=st.get(stem,i*0.1),frame_id=stem)
        r=det.process(fr).to_dict(); r.pop('timing_ms'); h=r['health']; [h.pop(k,None) for k in ('latency_p95_ms','messages','level','decision_level')]
        fh.write(json.dumps(r)+'\n')
