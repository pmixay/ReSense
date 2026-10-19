"""Read-only H1 positive-collision prototype on independently ray-cast controls.

This is a geometric proposal, NOT a detector classifier or a measured axis bound.
"""
import json
from pathlib import Path
import runpy

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
h=runpy.run_path(str(ROOT/'docs/evidence/integration_2026-10-16/h4_fixes/columns/withdrawn_acceptance.py.txt'))
rows=[]
for distance in [37.,67.,109.,137.]:
    for lateral in [-1.5,-.68,.68,1.5]:
        for top,absorbing in [(2.72,None),(3.22,None),(4.12,None),(4.12,(2.54,4.12))]:
            xyz,ring,labels=h['physical_column'](distance=distance,lateral=lateral,top=top,absorbing=absorbing)
            cs=[c for c in h['column_clusters'](xyz,ring) if np.mean(labels[c.points_idx]==1)>.5]
            assert len(cs)<=1
            if not cs:
                rows.append(dict(distance=distance,lateral=lateral,physical_top=top,absorbing=absorbing,
                                 truth_enters_envelope=abs(lateral)-.23<1.05,
                                 raw_object_points=int((labels==1).sum()),
                                 positive_core_with_supplied_3cm_bound=False,default_reason='no_cluster'))
                continue
            c=cs[0]
            # Analytical tunnel axis is known exactly here. 3 cm is a *supplied*
            # bound in this experiment, not an estimate from detector wall fits.
            y=xyz[c.points_idx,1]
            slack=.9-float(np.max(np.abs(y)))
            core=(slack>=.03 and c.n_gauge>=8 and c.height_max-c.height_min>=2.2
                  and c.height_min<=1. and c.size[0]<=.8)
            rows.append(dict(distance=distance,lateral=lateral,physical_top=top,absorbing=absorbing,
                             truth_enters_envelope=abs(lateral)-.23<1.05,raw_object_points=int((labels==1).sum()),
                             observed_height=[c.height_min,c.height_max],n_gauge=c.n_gauge,
                             observed_y=[float(y.min()),float(y.max())],max_axis_uncertainty_m=slack,
                             positive_core_with_supplied_3cm_bound=bool(core),
                             default_zone=c.zone,default_reason=c.reason))
            if (distance,lateral,top,absorbing)==(67.,.68,3.22,None):
                fig,axs=plt.subplots(1,2,figsize=(10,4))
                p=xyz[labels==1]
                axs[0].scatter(p[:,1],p[:,2]+1.83,s=16,label='all physical object returns')
                q=xyz[c.points_idx]
                axs[0].scatter(q[:,1],q[:,2]+1.83,s=8,label='candidate / strict voxels')
                axs[0].axhline(3.,color='red',linestyle='--',label='candidate top cut')
                axs[0].axvline(.9,color='orange',linestyle='--',label='strict lateral edge')
                axs[0].set(xlabel='known lateral [m]',ylabel='height above rail [m]',title='Physical H4 case45: 67 m')
                axs[0].legend(fontsize=7)
                axs[1].scatter(p[:,0],p[:,2]+1.83,s=14)
                axs[1].set(xlabel='forward [m]',ylabel='height [m]',title='84 raw returns; 80 in candidate')
                fig.tight_layout()
                fig.savefig(HERE/'h1-raw-case45.png',dpi=150)
                plt.close(fig)
result=dict(scope='Read-only component prototype; true axis / supplied uncertainty, not runtime acceptance',
            rows=rows,cases=len(rows),
            positive_core=sum(r['positive_core_with_supplied_3cm_bound'] for r in rows),
            outside_controls=sum(not r['truth_enters_envelope'] for r in rows),
            outside_core=sum(r['positive_core_with_supplied_3cm_bound'] for r in rows if not r['truth_enters_envelope']),
            blockers=['No independently calibrated runtime uncertainty tube exists in this patch.',
                      'The maximum geometric axis error allowed by case45 observed points is only about 4 cm.',
                      'No real-ride false-positive or full-detector H1 acceptance is claimed.'])
assert any(r['positive_core_with_supplied_3cm_bound'] for r in rows if r['physical_top']==3.22)
assert result['outside_controls']>0 and result['outside_core']==0
(HERE/'h1-prototype.json').write_text(json.dumps(result,indent=2))
print({k:v for k,v in result.items() if k!='rows'})
