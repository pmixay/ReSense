import sys,json,pickle,time,copy
sys.path.insert(0,'/home/user/ReSense')
import numpy as np
import scripts.false_stop_ledger as L
from scripts.cache_io import load_cache_stamps
from resense.config import DetectorConfig
from resense.detector import Detector
runs='/data/runs_dbg'
pieces=L.piece_table(runs,'/data/cache',[L.RIDE])
p=pieces[3]; rows=L.read_jsonl(p['path']); stamps=load_cache_stamps('/data/cache/new_data')
cfg=DetectorConfig.from_dict(L.window_config(runs,[]))
cfg2=DetectorConfig.from_dict(L.load_cfg_dict(runs+'/config.yaml',[])) if hasattr(L,'load_cfg_dict') else None
det=Detector(cfg)
out=[]
for i,fr in L._frames(p['files'],stamps,cfg,0,299):
    r=det.process(fr)
    if i==199:
        t=time.time(); blob=pickle.dumps(det); print('pickle size MB',len(blob)/1e6,'t',round(time.time()-t,3))
        det2=pickle.loads(blob)
    if i>=200:
        r2=det2.process(fr)
        a,b=r.to_dict(),r2.to_dict()
        for k in ('obstacle','n_candidates'):
            assert a[k]==b[k],(i,k)
        assert a['track']['center']==b['track']['center'] and a['track']['floor_coef']==b['track']['floor_coef'],(i,'track')
print('pickle resume identical for frames 200..299')
