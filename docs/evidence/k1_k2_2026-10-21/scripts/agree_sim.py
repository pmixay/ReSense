import json,sys
import numpy as np
sys.path.insert(0,'/home/user/ReSense/scripts')
import gauge_stability as g
b=sys.argv[1]; tol=float(sys.argv[2])
c=json.load(open(f'/data/acc/b6/track_control_{b}.json')); k=json.load(open(f'/data/acc/b6/track_cand1_{b}.json'))
xs=np.arange(0,251,1.0)
rows=[]; n=0
for rc,rk in zip(c['rows'],k['rows']):
    r=dict(rk)
    if 'center' in rc and 'center' in rk and (rc['center'],rc['tan_yaw'],rc['half_curv'])!=(rk['center'],rk['tan_yaw'],rk['half_curv']):
        n+=1
        dy=np.abs(np.array([g.lateral(rc,x)-g.lateral(rk,x) for x in xs]))
        bad=np.flatnonzero(dy>tol); agree=xs[bad[0]-1] if bad.size else xs[-1]
        r['axis_valid']=max(rk['axis_valid'], min(rc['axis_valid'], float(agree)))
    rows.append(r)
json.dump(dict(k,rows=rows),open(f'/tmp/claude-0/agree_{b}.json','w'))
print(b,'curve frames',n)
