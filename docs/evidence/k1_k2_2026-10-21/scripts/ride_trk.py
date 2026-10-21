import os, sys, json
import numpy as np
REPO=os.environ["RESENSE_REPO"]; sys.path[:0]=[REPO, os.path.join(REPO,"scripts")]
import eval_real
from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import frame_from_compact
from scripts.cache_io import cache_file_stem, cache_files, load_cache_array, load_cache_stamps
root,piece,a,b=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),int(sys.argv[4])
d=os.path.join(root,"new_data"); files=list(np.array_split(np.array(cache_files(d)),8)[piece]); stamps=load_cache_stamps(d)
cfg=DetectorConfig.from_dict(eval_real.load_cfg_dict(os.path.join(REPO,"configs/default.yaml"),[]))
det=Detector(cfg)
for i,f in enumerate(files[:b+1]):
    stem=cache_file_stem(f); fr=frame_from_compact(load_cache_array(f),cfg.sensor,stamp=stamps.get(stem,i*0.1),frame_id=stem)
    det._curve_added=0; det._curve_seen=[]
    res=det.process(fr)
    if i<a: continue
    cv=det.track.curve
    tr=[(t.id, round(t.last.distance,1), t.zone, t.withheld, t.curve_seen, getattr(t.last,'curve',False)) for t in det.tracker.tracks if t.last is not None and t.curve_seen]
    print(i, 'STOP' if res.obstacle else '-', 'added',det._curve_added, 'curve_from', None if cv is None else round(cv.curve_from), 'curve_seen tracks', tr)
