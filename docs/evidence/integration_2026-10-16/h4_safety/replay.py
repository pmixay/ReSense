"""Independent development stress, H3 boundary replay and dark-observer sensitivity."""
import argparse
import json
from pathlib import Path
import numpy as np
from common import OUT,ROOT,arrid,sha,save,emit,identity,normalize,cluster_desc,track_desc

def main(argv):
    ap=argparse.ArgumentParser(); ap.add_argument('--mode',choices=['all','plain','dark','dark-inherited','stress'],default='all')
    a=ap.parse_args(argv)
    cfg=identity()
    from resense.detector import Detector
    from resense.frame import frame_from_compact
    import resense.clustering as cl
    from scripts.cache_io import cache_files,cache_file_stem,load_cache_array,load_cache_stamps
    state={'frame':None,'calls':[],'spares':[]}
    if hasattr(cl,'top_is_free'):
        original=cl.top_is_free
        def observed(rays,idx,*args,**kwargs):
            raw=original(rays,idx,*args,**kwargs)
            if a.mode not in ('dark','dark-inherited'): return raw
            p=rays.xyz[idx].astype(float)
            e=np.degrees(np.arctan2(p[:,2],np.hypot(p[:,0],p[:,1])))
            az=np.degrees(np.arctan2(p[:,1],p[:,0])); top=float(e.max())
            rt=float(np.median(np.linalg.norm(p[e>=top-.06],axis=1)))
            q=rays.xyz.astype(float)
            qe=np.degrees(np.arctan2(q[:,2],np.hypot(q[:,0],q[:,1])))
            qa=np.degrees(np.arctan2(q[:,1],q[:,0]))
            tol=max(.5,.02*rt)+(.5 if a.mode=='dark-inherited' else 0)
            pad=.02 if a.mode=='dark-inherited' else .12
            remove=(np.abs(np.linalg.norm(q,axis=1)-rt)<=tol) & (qe>top+.04) & (qe<=top+.6)
            remove &= (q[:,0]>0)&(qa>=az.min()-pad)&(qa<=az.max()+pad)
            remove[idx]=False
            keep=~remove; remap=np.cumsum(keep)-1
            masked=cl.FrameRays(rays.xyz[keep],None if rays.ring is None else rays.ring[keep],
                                None if rays.h is None else rays.h[keep],None if rays.dy is None else rays.dy[keep])
            ans=original(masked,remap[idx],*args,**kwargs)
            state['calls'].append(dict(idx=arrid(idx),centroid=p.mean(0).tolist(),
                bbox=[p.min(0).tolist(),p.max(0).tolist()],top=top,range=rt,removed=arrid(np.flatnonzero(remove)),
                removed_n=int(remove.sum()),plain_answer=bool(raw),masked_answer=bool(ans)))
            return ans
        cl.top_is_free=observed
    jobs=[]
    if a.mode in ('all','stress'):
        for bag in ['roundT_doubleT','squareT_platform_squareT_switch']:
            d='/data/cache/'+bag
            jobs.append((bag,cache_files(d),load_cache_stamps(d),True))
    if a.mode in ('all','plain','dark','dark-inherited'):
        files=cache_files('/data/cache/new_data'); stamps=load_cache_stamps('/data/cache/new_data')
        for i in [1,3]: jobs.append((f'ride_{i}',list(np.array_split(np.array(files),8)[i]),stamps,False))
    summary={}
    for bag,files,stamps,drop in jobs:
        det=Detector(cfg); rng=np.random.default_rng(461023)
        if hasattr(det.tracker,'_uncorroborated_spare'):
            spare_original=det.tracker._uncorroborated_spare
            def spare(c,hist):
                pre=cluster_desc(c)
                spare_original(c,hist)
                if c.spared:
                    state['spares'].append(dict(candidate_identity=id(c),prior_hist=list(hist),pre=pre,post=cluster_desc(c)))
            det.tracker._uncorroborated_spare=spare
        stops=[]; warnings=[]; h3_mismatch=[]; n=0
        retained=None
        if not drop and a.mode not in ('dark','dark-inherited'):
            run='baseline-707ea9cda051-20261016T060147Z-68fb3429' if 'baseline' in str(ROOT) else 'candidate-f8c088dc4f32-20261016T073403Z-4b64ec55'
            retained=(Path('/h3')/run/'frames'/('new_data_'+bag[-1]+'.jsonl')).open()
        with (OUT/(bag+'.jsonl')).open('w') as f:
            for i,path in enumerate(files):
                stem=cache_file_stem(path); assert stem in stamps
                arr=load_cache_array(path)
                fr=frame_from_compact(arr,cfg.sensor,stamp=stamps[stem],frame_id=stem)
                mask=np.ones(fr.n,bool)
                if drop:
                    mask=rng.random(fr.n)>=.27
                    fr.xyz=fr.xyz[mask]; fr.intensity=fr.intensity[mask]
                    fr.ring=None if fr.ring is None else fr.ring[mask]
                state.update(frame=stem,calls=[],spares=[])
                r=det.process(fr)
                d=normalize(r.to_dict())
                if retained:
                    h=json.loads(next(retained))
                    if normalize(h['serialized'])!=d: h3_mismatch.append(stem)
                for s in state['spares']:
                    cid=s.pop('candidate_identity')
                    matches=[t for t in det.tracker.tracks if id(t.last)==cid]
                    s['tracks_by_object_identity']=[track_desc(t) for t in matches]
                    s['output_membership']=[dict(id=t.id,detection=any(x.id==t.id for x in r.detections),
                                                   warning=any(x.id==t.id for x in r.warnings)) for t in matches]
                row=dict(i=i,frame_id=stem,stamp=fr.stamp,input=arrid(arr),cache_sha256=sha(Path(path).read_bytes()),
                         mask=arrid(mask),serialized=d,candidates=[cluster_desc(c) for c in r.candidates],
                         tracks=[track_desc(t) for t in det.tracker.tracks],observer=state['calls'],spares=state['spares'])
                emit(f,row)
                if r.obstacle: stops.append(stem)
                if r.warning: warnings.append(stem)
                if stem=='new_data_54_0009':
                    save(bag+'-promotion.json',row)
                n+=1
                if i%200==0: print(bag,i,stem,flush=True)
        if retained:
            assert retained.readline()==''
            retained.close()
        summary[bag]=dict(frames=n,stops=stops,warning_frames=warnings,h3_non_timing_mismatches=h3_mismatch,
                          seed=461023 if drop else None,dropout=.27 if drop else 0)
        save('summary.json',summary)
        print(bag,n,'STOP',len(stops),'H3 mismatch',len(h3_mismatch),flush=True)
