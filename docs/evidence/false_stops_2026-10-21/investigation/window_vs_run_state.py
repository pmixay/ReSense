import sys,json
sys.path.insert(0,'/home/user/ReSense')
import numpy as np
import scripts.false_stop_ledger as L
from scripts.cache_io import load_cache_stamps
from resense.config import DetectorConfig
from resense.detector import Detector
runs='/data/runs_dbg'
pieces=L.piece_table(runs,'/data/cache',L.EMPTY_BAGS+[L.RIDE])
pidx={(p['bag'],p['piece']):p for p in pieces}
cfgd=L.window_config(runs,[])
led=json.load(open('/data/led_dbg2/ledger.json'))
for eid in sys.argv[1:]:
    e=next(x for x in led['episodes'] if x['id']==eid)
    p=pidx[(e['recording'],e['piece'])]; rows=L.read_jsonl(p['path'])
    st=load=L.load_cache_stamps if False else None
    stamps=load_cache_stamps('/data/cache/'+e['recording'])
    on=e['piece_frame']; lo=max(0,on-150)
    cfg=DetectorConfig.from_dict(cfgd); det=Detector(cfg)
    diffs={}
    for i,fr in L._frames(p['files'],stamps,cfg,lo,on+3):
        r=det.process(fr).to_dict(); f=rows[i]
        k=i-lo
        for name,a,b in (('obstacle',r['obstacle'],f['obstacle']),('ego_est',r['ego_speed_estimate'],f['ego_speed_estimate']),('n_acc',r['n_accumulated'],f['n_accumulated']),('n_cand',r['n_candidates'],f['n_candidates']),('n_points',r['n_points'],f['n_points']),
              ('trk_center',r['track']['center'],f['track']['center']),('trk_curv',r['track']['curvature'],f['track']['curvature']),('trk_age',r['track']['age'],f['track']['age']),('axis_valid',r['track']['axis_valid'],f['track']['axis_valid']),('floor0',r['track']['floor_coef'][2],f['track']['floor_coef'][2]),('mon',r['health']['monitored_range'],f['health']['monitored_range'])):
            same = (a==b) if not isinstance(a,float) or b is None else abs(a-b)<1e-6
            if not same: diffs.setdefault(name,[]).append(k)
    print(eid,'onset',on,'window start',lo)
    for n,v in diffs.items(): print('  ',n,'first diff at window frame',v[0],'count',len(v),'of',on+4-lo)
