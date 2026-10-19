"""Full node payloads and raw target returns for the nominal E6 control."""
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
W=Path('/tmp/opencode/r3-h1')
sys.path.insert(0,str(ROOT/'docs/evidence/judgement_2026-10-13/scripts'))
import range_test as t  # noqa: E402
from judge_runner import record  # noqa: E402

side=sys.argv.pop(1)
out=W/f'{side}-target-inspection'
assert not out.with_suffix('.nodes.json').exists()
orig=t.run_frame
records=[]
examples=[]


def frame(rep,xyz,inten,ring,m,k):
    info=dict(sys._getframe(1).f_locals.get('info',{}))
    res=orig(rep,xyz,inten,ring,m,k)
    records.append(dict(info=info,node=record(k,m['bag_t'],m['stamp'],res,0.,0.,m['frame_id'],m['topic'])))
    if k in [276,278,279,296] and info.get('n_obj',0)>0:
        n=info['n_obj']
        p=(xyz[-2*n:]@rep.R_vs.T)@rep.detector.mount_rotation.T
        heights=p[:,2]-res.track.rail_z(p[:,0])
        examples.append(dict(k=k,X=info['X'],n_rays=n,xyz=p.tolist(),height=heights.tolist(),
                             footprint=np.ptp(p,axis=0).tolist()))
    return res


t.run_frame=frame
sys.argv=[str(t.__file__),str(W/'baseline/cache/roundT_squareT_pressureGate_squareT'),
          str(W/'baseline/icp_roundT_squareT_pressureGate_squareT.json'),str(out),
          '--obj','0.05,0.05,2.6','--start','150','--d0','230','--end','340','--base','0.2']
t.main()
out.with_suffix('.nodes.json').write_text(json.dumps(records))
out.with_suffix('.raw.json').write_text(json.dumps(examples,indent=2))
if side=='candidate':
    geo=json.loads((W/'baseline/hanging_geometry.json').read_text())
    fig,axs=plt.subplots(1,3,figsize=(13,4))
    e=next(e for e in examples if e['k']==278)
    p=np.array(e['xyz'])
    axs[0].scatter(p[:,1],e['height'],s=12)
    axs[0].set(xlabel='vehicle left [m]',ylabel='rail-relative height [m]',
               title=f"E6 k278, X={e['X']} m, {e['n_rays']} rays")
    for ax,k in zip(axs[1:],[777,778]):
        row=next(r for r in geo if r['k']==k)
        g=row['groups'][0]
        pp=np.array(g['xyz'])
        ax.scatter(pp[:,0],g['h'],s=25)
        ax.axhline(3.,color='red',linestyle='--')
        ax.set(xlabel='forward [m]',ylabel='rail-relative height [m]',
               title=f"Set O k{k}, X={row['X']:.2f} m")
    fig.tight_layout()
    fig.savefig(HERE/'r3-raw-examples.png',dpi=150)
    plt.close(fig)
