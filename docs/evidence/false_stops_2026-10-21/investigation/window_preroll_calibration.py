import sys,json,os
sys.path.insert(0,'/home/user/ReSense')
import scripts.false_stop_ledger as L
from scripts.cache_io import load_cache_stamps
from concurrent.futures import ProcessPoolExecutor
runs='/data/runs_dbg'
bags=L.EMPTY_BAGS+[L.RIDE]
pieces=L.piece_table(runs,'/data/cache',bags)
pidx={(p['bag'],p['piece']):p for p in pieces}
led=json.load(open('/data/led_dbg2/ledger.json'))
cfg_off=L.window_config(runs,[])
cfg_on=L.window_config(runs,[]); cfg_on['calibration']['enabled']=True
st={}
def job(a):
    e,pre,calib=a
    p=pidx[(e['recording'],e['piece'])]
    st.setdefault(e['recording'],load_cache_stamps('/data/cache/'+e['recording']))
    on=e['piece_frame']
    j={'id':e['id'],'cfg':cfg_on if calib else cfg_off,'files':p['files'],'stamps':st[e['recording']],'onset':on,'size':e['size'],'lo':max(0,on-pre),'hi':on+3,'stop_after_onset':True,'save':False}
    r,_=L.replay_job(j)
    ok,df,dd=L.reproduces(e,r)
    return e['id'],pre,calib,ok,df,dd,r['frames']
fails=[e for e in led['episodes'] if not e['window']['reproduced']]
jobs=[(e,pre,c) for e in fails for pre in (150,300,600,10**6) for c in (False,True)]
res={}
with ProcessPoolExecutor(4) as ex:
    for r in ex.map(job,jobs):
        res.setdefault(r[0],[]).append(r[1:])
for k,v in res.items():
    print(k, ' '.join(f"{'full' if pre==10**6 else pre}{'+cal' if c else ''}:{'OK' if ok else 'no'}" for pre,c,ok,df,dd,fr in v))
