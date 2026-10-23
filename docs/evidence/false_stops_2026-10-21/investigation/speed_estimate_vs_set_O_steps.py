import sys,json,numpy as np
sys.path.insert(0,'/home/user/ReSense')
import scripts.false_stop_ledger as L
rows=L.read_jsonl('/data/dbgO/cloud_with_fake_obj.jsonl')
lab=json.load(open('/home/user/ReSense/labels/cloud_with_fake_obj.json'))
v,src=L.speed_series(rows)
# truth speed from object steps: for each pair of consecutive frames, objects visible in both with plausible & n_points>=3 : dx of bbox min x
truth=np.full(len(rows),np.nan)
for i in range(len(rows)-1):
    a={o['name']:o for o in lab.get(f'{i:05d}',[]) if o.get('plausible') and o['n_points']>=3}
    b={o['name']:o for o in lab.get(f'{i+1:05d}',[]) if o.get('plausible') and o['n_points']>=3}
    ds=[]
    for k in a:
        if k in b:
            ca=np.array(a[k]['bbox']).mean(0); cb=np.array(b[k]['bbox']).mean(0)
            ds.append(np.hypot(*(ca[:2]))-np.hypot(*(cb[:2])))
    if ds:
        dt=L.frame_dt(rows[i]['stamp'],rows[i+1]['stamp'])
        truth[i]=np.median(ds)/dt
ok=~np.isnan(truth)
print('truth frames',ok.sum(), 'median',np.nanmedian(truth), 'range', np.nanpercentile(truth,[5,95]))
for s in ('estimate','interp','hold'):
    m=ok&(src==s)
    if m.sum(): 
        e=v[m]-truth[m]
        print(s,m.sum(),'bias',round(float(np.median(e)),2),'MAE',round(float(np.mean(np.abs(e))),2),'p90',round(float(np.percentile(np.abs(e),90)),2))
# integrated distances over windows 60-120 frames
for (a,b) in ((204,300),(300,420),(420,530),(520,630),(620,740)):
    st=[(truth[i]*L.frame_dt(rows[i]['stamp'],rows[i+1]['stamp'])) for i in range(a,b) if ok[i]]
    print(a,b,'truth cum',round(np.sum(st)/max(1,len(st))*(b-a),1),'est cum',round(sum(v[i]*L.frame_dt(rows[i]['stamp'],rows[i+1]['stamp']) for i in range(a,b)),1))
