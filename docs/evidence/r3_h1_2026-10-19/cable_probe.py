"""Unchanged judge range test with whole-cloud, post-insertion X3 transforms."""
import sys
from pathlib import Path

import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'docs/evidence/judgement_2026-10-13/scripts'))
import range_test as t
from probe import rot

variant=sys.argv.pop(1)
orig=t.run_frame
angles={'pitch_p2':(0,2,0),'pitch_m2':(0,-2,0),'roll_p2':(2,0,0)}
R=rot(*angles.get(variant,(0,0,0)))


def frame(rep,xyz,inten,ring,m,idx):
    if variant=='dedup':
        _,first=np.unique(xyz,axis=0,return_index=True)
        keep=np.sort(first)
        xyz,inten,ring=xyz[keep],inten[keep],ring[keep]
    if variant.startswith('drop30_s'):
        keep=np.random.default_rng(100000*int(variant[-1])+idx).random(len(xyz))>=.3
        xyz,inten,ring=xyz[keep],inten[keep],ring[keep]
    if variant in angles:
        rv=rep.R_vs.astype(np.float64)
        xyz=((xyz.astype(np.float64)@rv.T)@R.T@rv).astype(np.float32)
    return orig(rep,xyz,inten,ring,m,idx)


t.run_frame=frame
t.main()
