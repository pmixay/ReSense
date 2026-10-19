import json, numpy as np, sys
sys.path.insert(0,'scripts'); from gauge_stability import lateral
sys.path.insert(0,'docs/evidence/judgement_2026-10-13/scripts'); from judge_runner import NodeReplica
bag, k, tb, tc, out = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5]
d=np.load(f'/data/decoded/{bag}/f_{k:05d}.npz')
b=json.load(open(tb))['rows'][k]; c=json.load(open(tc))['rows'][k]
xyz=(d['xyz']@NodeReplica().R_vs.T)@np.array(b['R']).T
m=(xyz[:,0]>0)&(xyz[:,0]<170)&(np.abs(xyz[:,1])<9)
X=np.arange(0,170,1.0)
np.savez(out, xyz=xyz[m], X=X, base=[lateral(b,x) for x in X], cand=[lateral(c,x) for x in X])
