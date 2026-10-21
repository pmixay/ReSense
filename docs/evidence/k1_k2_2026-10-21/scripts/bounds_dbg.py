import os, sys, json
import numpy as np
REPO=os.environ["RESENSE_REPO"]; sys.path[:0]=[REPO, os.path.join(REPO,"scripts")]
import eval_real
import resense.track as T
from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import frame_from_compact
from scripts.cache_io import cache_file_stem, cache_files, load_cache_array, load_cache_stamps
cap={}
orig=T._joint_output
def hook(base,js,cfg,bounds=None,held=0.0):
    cap['b']=bounds; cap['base']=base; return orig(base,js,cfg,bounds,held)
T._joint_output=hook
root,piece,frame=sys.argv[1],int(sys.argv[2]),int(sys.argv[3])
d=os.path.join(root,"new_data"); files=list(np.array_split(np.array(cache_files(d)),8)[piece]); stamps=load_cache_stamps(d)
cfg=DetectorConfig.from_dict(eval_real.load_cfg_dict(os.path.join(REPO,"configs/default.yaml"),[]))
det=Detector(cfg)
for i,f in enumerate(files[:frame+1]):
    stem=cache_file_stem(f); fr=frame_from_compact(load_cache_array(f),cfg.sensor,stamp=stamps.get(stem,i*0.1),frame_id=stem); res=det.process(fr)
b=cap['b']; base=cap['base']; cv=det.track.curve
for name,(x,y) in b.items():
    x=np.asarray(x); y=np.asarray(y)
    print(name, 'reach base %.0f curve %.0f'%(T._followed_reach(x,y,base,cfg.track), T._followed_reach(x,y,cv,cfg.track)))
    print('  ', ' '.join('%.0f:%.2f/%.2f'%(xi, yi-base.center_y(xi), yi-cv.center_y(xi)) for xi,yi in zip(x,y)))
