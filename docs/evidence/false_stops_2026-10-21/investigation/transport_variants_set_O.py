import sys,json,numpy as np
sys.path.insert(0,'/home/user/ReSense')
import scripts.false_stop_ledger as L
rows=L.read_jsonl('/data/dbgO/cloud_with_fake_obj.jsonl')
lab=json.load(open('/home/user/ReSense/labels/cloud_with_fake_obj.json'))
v,src=L.speed_series(rows)
objs={}
for i in range(len(rows)):
    for o in lab.get(f'{i:05d}',[]):
        if o.get('plausible') and o['n_points']>=5:
            objs.setdefault(o['name'],{})[i]=o
orig=L.step_geometry
def variants():
    yield 'full', orig
    yield 'no_pitch', lambda t,near=10.0: (lambda r:(r[0],0.0,r[2],0.0))(orig(t,near))
    yield 'pitch_only_slope', lambda t,near=10.0: (lambda r:(r[0],r[1],r[2],0.0))(orig(t,near))
    yield 'flip_phi', lambda t,near=10.0: (lambda r:(r[0],-r[1],r[2],-r[3]))(orig(t,near))
    yield 'no_yaw', lambda t,near=10.0: (lambda r:(0.0,r[1],0.0,r[3]))(orig(t,near))
for name,fn in variants():
    L.step_geometry=fn
    errs=[]
    for oname,fr in objs.items():
        far=[k for k in fr if 40<=fr[k]['distance']<=140]
        if not far: continue
        f0=min(far,key=lambda k:abs(fr[k]['distance']-110))
        c0=L.label_center(fr[f0])
        path=L.transport(rows,f0,c0,(v,src))
        for q in path:
            f1=q['i']
            if f1 in fr and 10<=fr[f1]['distance']<=25:
                errs.append(q['p']-L.label_center(fr[f1]))
    e=np.array(errs)
    print(name,len(e),'x',np.round(np.percentile(np.abs(e[:,0]),[50,90]),2),'y',np.round(np.percentile(np.abs(e[:,1]),[50,90]),2),'z',np.round(np.percentile(np.abs(e[:,2]),[50,90]),2), 'zmean',np.round(e[:,2].mean(),2))
print('--- per object (no_pitch vs full): median z err, and mean slope phi along path')
for name,fn in (('full',orig),('no_pitch',lambda t,near=10.0: (lambda r:(r[0],0.0,r[2],0.0))(orig(t,near)))):
    L.step_geometry=fn
    for oname,fr in objs.items():
        far=[k for k in fr if 40<=fr[k]['distance']<=140]
        if not far: continue
        f0=min(far,key=lambda k:abs(fr[k]['distance']-110))
        c0=L.label_center(fr[f0])
        path=L.transport(rows,f0,c0,(v,src))
        es=[(q['p']-L.label_center(fr[q['i']])) for q in path if q['i'] in fr and 10<=fr[q['i']]['distance']<=25]
        phis=[orig(rows[i]['track'])[1] for i in range(f0,path[-1]['i'])]
        if es: print(name,oname,'f0',f0,'n',len(es),'z',np.round(np.median([e[2] for e in es]),2),'x',np.round(np.median([e[0] for e in es]),2),'meanphi',round(float(np.mean(phis)),4), 'trav', round(path[-1]['traveled']))
