import glob,json,os,sys,time
import numpy as np
sys.path.insert(0, os.path.join(os.environ["RESENSE_REPO"], "docs/evidence/judgement_2026-10-13/scripts"))
import judge_runner as jr
from range_test import run_frame
c=sys.argv[1]; meta=json.load(open(c+'/meta.json')); fs=sorted(glob.glob(c+'/f_*.npz'))
rep=jr.NodeReplica(); t=[]
for k,(m,f) in enumerate(zip(meta,fs)):
    d=np.load(f); res=run_frame(rep,d['xyz'],d['inten'],d['ring'],m,k); t.append(res.timing_ms['total'])
t=np.array(t); print(os.environ["RESENSE_REPO"], 'mean %.1f p50 %.1f p95 %.1f max %.1f'%(t.mean(),np.median(t),np.percentile(t,95),t.max()))
