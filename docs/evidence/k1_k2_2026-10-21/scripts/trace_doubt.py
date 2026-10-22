# trace the track near the given distance window: obs laterals, withheld, opinion prob; frames a..b of a decoded cache
import glob,json,os,sys
import numpy as np
sys.path.insert(0, os.path.join(os.environ["RESENSE_REPO"], "docs/evidence/judgement_2026-10-13/scripts"))
import judge_runner as jr
from range_test import run_frame
from resense.opinion import track_features
c, a, b, dlo, dhi = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])
meta=json.load(open(c+'/meta.json')); fs=sorted(glob.glob(c+'/f_*.npz'))
rep=jr.NodeReplica()
for k,(m,f) in enumerate(zip(meta,fs)):
    if k>b: break
    d=np.load(f); res=run_frame(rep,d['xyz'],d['inten'],d['ring'],m,k)
    if k<a: continue
    tr=rep.detector.tracker; op=tr.opinion
    for t in tr.tracks:
        if t.last is not None and dlo<=t.last.distance<=dhi:
            p=op.prob(track_features(t.obs,t.hits,t.hit_fraction)) if (op and t.obs) else None
            print(k, jr.node_decision(res), 'trk',t.id,'d=%.1f'%t.last.distance,'zone',t.zone,'withheld',t.withheld,'p=%s'%(None if p is None else round(p,3)),
                  'lat',[round(o[1],2) for o in t.obs[-6:]],'beyond',[int(o[14]) for o in t.obs[-6:]],'added',getattr(rep.detector,'_curve_added',0))
