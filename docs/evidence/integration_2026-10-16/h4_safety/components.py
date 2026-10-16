"""New analytic physical caster and component probes, independent of authored tests."""
import argparse
import copy
import inspect
import itertools
import numpy as np
from common import OUT,save,emit,identity,arrid,cluster_desc,track_desc

def cast(boxes,band=None,beam=False):
    from resense.sensor import RING_ELEVATION_DEG
    az=np.radians(np.arange(-50,50.00001,.1)+.037)
    el=np.radians(RING_ELEVATION_DEG)
    aa,ee=np.meshgrid(az,el)
    rays=np.stack([np.cos(ee)*np.cos(aa),np.cos(ee)*np.sin(aa),np.sin(ee)],axis=-1).reshape(-1,3)
    ring=np.repeat(np.arange(el.size),az.size)
    # Exit distances from rectangular tunnel, origin at sensor, rail z=-1.83.
    limits=[]
    for j,b in [(0,247.),(1,2.43),(1,-2.43),(2,4.12-1.83),(2,-1.83)]:
        with np.errstate(divide='ignore',invalid='ignore'): t=b/rays[:,j]
        limits.append(np.where(t>0,t,np.inf))
    dist=np.min(limits,axis=0); label=np.zeros(dist.size,int)
    objects=list(boxes)
    if beam:
        d=boxes[0][0][0]
        objects.append(([d-4,-1.2,3.05-1.83],[d-3.7,1.2,3.25-1.83]))
    for k,(lo,hi) in enumerate(objects,1):
        with np.errstate(divide='ignore',invalid='ignore'):
            t0=np.asarray(lo)/rays; t1=np.asarray(hi)/rays
        near=np.minimum(t0,t1).max(1); far=np.maximum(t0,t1).min(1)
        hit=(far>=np.maximum(near,0)) & (near>0) & (near<dist)
        dist[hit]=near[hit]; label[hit]=k
    xyz=rays*dist[:,None]
    keep=(dist<=225)&(dist>=2.5)
    if band is not None:
        keep &= ~((label>0)&(label<=len(boxes))&(xyz[:,2]+1.83>=band[0])&(xyz[:,2]+1.83<=band[1]))
    return xyz[keep].astype(np.float32),ring[keep],label[keep]

def clusters(xyz,ring,cfg,frame=True):
    import resense.clustering as cl
    from resense.gauge import point_in_polygon,widened_profile,gauge_core_mask
    dy=xyz[:,1]; h=xyz[:,2]+1.83; x=xyz[:,0]
    warning=point_in_polygon(dy,h,widened_profile(cfg.gauge,cfg.gauge.warning_margin))
    warning &= (x>=cfg.gauge.range_min)&(x<=cfg.gauge.range_max)
    idx=np.flatnonzero(warning)
    core=gauge_core_mask(dy[idx],h[idx],x[idx],cfg.gauge)
    kw=dict(frame_idx=idx,gauge=cfg.gauge,axis_valid=225.,height_valid=225.)
    if frame and 'frame_xyz' in inspect.signature(cl.find_clusters).parameters:
        kw.update(frame_xyz=xyz,frame_ring=ring,frame_h=h,frame_dy=dy)
    if ring is not None: kw['ring']=ring[idx]
    return cl.find_clusters(xyz[idx],np.full(idx.size,35,np.float32),dy[idx],h[idx],core,cfg.cluster,**kw)

def sequence(cs,missing,labels,missing_labels,cfg):
    from resense.tracking import Tracker
    tr=Tracker(cfg.tracking); out=[]; identities={}
    for f in range(20):
        use=copy.deepcopy(missing if f in (9,10) else cs)
        lab=missing_labels if f in (9,10) else labels
        pre=[cluster_desc(c) for c in use]
        reported=tr.update(use,frame_dt=.1)
        for t in tr.tracks:
            if any(t.last is c for c in use):
                ids,cnt=np.unique(lab[t.last.points_idx],return_counts=True)
                identities[t.id]=int(ids[cnt.argmax()]) if ids.size else -1
        out.append(dict(frame=f,pre=pre,post=[cluster_desc(c) for c in use],
            tracks=[dict(**track_desc(t),physical_label=identities.get(t.id,-1)) for t in tr.tracks],
            stop_labels=sorted(set(identities.get(t.id,-1) for t in reported if t.reported and t.zone=='gauge')),
            stop_ids=[t.id for t in reported if t.reported and t.zone=='gauge']))
    return out

def physical(cfg,only_beam=False):
    cases=[]
    for d,y,w,top in itertools.product([37.,67.,109.,137.],[0.,.68,-.68,1.30],[.28,.46],[2.72,3.22,3.62,4.12]):
        cases.append(dict(d=d,y=y,w=w,top=top,band=None,beam=False,multi=False))
    for d,y,w,band in itertools.product([37.,67.,109.,137.],[0.,.68,-.68,1.30],[.28,.46],[(2.54,3.18),(2.54,4.12)]):
        cases.append(dict(d=d,y=y,w=w,top=4.12,band=band,beam=False,multi=False))
    for d in [37.,67.,109.,137.]: cases.append(dict(d=d,y=.68,w=.46,top=2.72,band=None,beam=True,multi=False))
    cases.append(dict(d=37.,y=.68,w=.46,top=4.12,band=None,beam=False,multi=True))
    if only_beam: cases=[p for p in cases if p['beam']]
    perm=np.random.default_rng(461019).permutation(128)
    summary=[]
    with (OUT/'physical.jsonl').open('w') as f:
        for n,p in enumerate(cases):
            ds=[37.,67.,109.] if p['multi'] else [p['d']]
            boxes=[([d-p['w']/2,p['y']-p['w']/2,-1.83],
                    [d+p['w']/2,p['y']+p['w']/2,p['top']-1.83]) for d in ds]
            xyz,ring,lab=cast(boxes,p['band'],p['beam'])
            for mode,drop in itertools.product(['highest','reverse','permuted','absent'],[0.,.27]):
                keep=np.random.default_rng(461021).random(len(xyz))>=drop
                pts=xyz[keep]; ll=lab[keep]
                rr=None if mode=='absent' else (ring if mode=='highest' else 127-ring if mode=='reverse' else perm[ring])[keep]
                cs=clusters(pts,rr,cfg)
                missing=(ll==0)|(ll>len(boxes))
                cm=clusters(pts[missing],None if rr is None else rr[missing],cfg)
                frames=sequence(cs,cm,ll,ll[missing],cfg)
                row=dict(case=n,params=p,ring_mode=mode,dropout=drop,boxes=boxes,
                         xyz=arrid(pts),ring=None if rr is None else arrid(rr),labels=arrid(ll),
                         object_returns={int(k):int((ll==k).sum()) for k in range(1,len(boxes)+1)},frames=frames)
                emit(f,row)
                summary.append(dict(case=n,params=p,ring_mode=mode,dropout=drop,
                    object_returns=row['object_returns'],clusters=len(cs),
                    inside=bool(abs(p['y'])-p['w']/2<1.05),
                    matched_stop_frames={k:[s['frame'] for s in frames if k in s['stop_labels']] for k in range(1,len(boxes)+1)},
                    background_stop_frames=[s['frame'] for s in frames if 0 in s['stop_labels']],
                    initial=[cluster_desc(c) for c in cs]))
            if n%20==0: print('physical',n,'/',len(cases),flush=True)
    save('physical-summary.json',summary)

def surface_points(width,top,residual,mirror=1,echo=1):
    x,h=np.meshgrid(np.arange(76,143.0001,.23),np.arange(.11,2.9701,.19))
    def wall(x,h): return 1.17-.073*(x-103)+.31*h-.12*h*h
    pts=[np.column_stack([x.ravel(),wall(x,h).ravel(),h.ravel()-1.83])]; labels=[np.zeros(x.size,int)]
    for label,d in enumerate([93.,111.],1):
        hh,ww=np.meshgrid(np.arange(.11,top+.0001,.13),np.linspace(-width/2,width/2,max(2,int(np.ceil(width/.045))+1)))
        yy=wall(d,hh)-residual+ww
        front=np.column_stack([np.full(hh.size,d),yy.ravel(),hh.ravel()-1.83])
        pts.append(front); labels.append(np.full(len(front),label))
        # Connecting side surfaces make the attachment geometry explicit.
        depth=np.linspace(0,residual,max(2,int(np.ceil(residual/.13))+1))
        for edge in [-width/2,width/2]:
            hv,dv=np.meshgrid(np.arange(.11,top+.0001,.13),depth)
            side=np.column_stack([np.full(hv.size,d), (wall(d,hv)-dv+edge).ravel(),hv.ravel()-1.83])
            pts.append(side); labels.append(np.full(len(side),label))
    p=np.concatenate(pts).astype(np.float32); p[:,1]*=mirror
    return np.repeat(p,echo,axis=0),np.repeat(np.concatenate(labels),echo)

def surface(cfg):
    summary=[]
    with (OUT/'surface.jsonl').open('w') as f:
        for n,(w,top,res,mirror,rev,echo) in enumerate(itertools.product([.17,.39,.63],[1.73,2.71],[1.12,1.36,1.64],[-1,1],[False,True],[1,2])):
            pts,lab=surface_points(w,top,res,mirror,echo)
            if rev: pts=pts[::-1].copy(); lab=lab[::-1].copy()
            cs=clusters(pts,None,cfg)
            frames=sequence(cs,cs,lab,lab,cfg)
            row=dict(case=n,params=dict(width=w,top=top,residual=res,mirror=mirror,reversed=rev,echo=echo),
                     xyz=arrid(pts),labels=arrid(lab),initial=[cluster_desc(c) for c in cs],frames=frames)
            emit(f,row)
            summary.append(dict(case=n,params=row['params'],clusters=len(cs),
                cut=sum(bool(getattr(c,'cut',False)) for c in cs),spared=sum(bool(getattr(c,'spared',False)) for c in cs),
                matched_stop_frames={k:[s['frame'] for s in frames if k in s['stop_labels']] for k in [1,2]},
                boxes=[dict(label=k,bmin=pts[lab==k].min(0),bmax=pts[lab==k].max(0)) for k in [1,2]],
                initial=[cluster_desc(c) for c in cs]))
    save('surface-summary.json',summary)

def azimuth(cfg):
    import resense.clustering as cl
    if not hasattr(cl,'FrameRays'): return
    rng=np.random.default_rng(461029)
    p=rng.uniform([-225,-250,-10],[225,250,10],(80000,3)).astype(np.float32)
    p[:100,0]=0
    for i,b in enumerate(range(255)):
        p[100+i]=[100.,100.*(b-127.)/105.,0.]
    r=cl.FrameRays(p)
    windows=[(-50,50),(-89,89),(-.0001,.0001),(0,0),(-50,-49.9),(49.9,50)]
    for b in [0,1,126,127,128,253,254]:
        a=float(np.degrees(np.arctan((b-127.)/105.)))
        windows.extend([(a,a),(a-.000001,a+.000001)])
    for _ in range(150-len(windows)):
        a,b=np.sort(rng.uniform(-89,89,2)); windows.append((a,b))
    results=[]
    for a,b in windows:
        t0,t1=np.tan(np.radians(a)),np.tan(np.radians(b))
        oracle=np.flatnonzero((p[:,0]>0)&(p[:,1]>=t0*p[:,0])&(p[:,1]<=t1*p[:,0]))
        got=r.window(a,b)
        results.append(dict(window=[a,b],expected=arrid(oracle),actual=arrid(got),mismatches=np.setxor1d(oracle,got).tolist()))
    save('azimuth.json',dict(seed=461029,xyz=arrid(p),windows=results,total_mismatches=sum(len(x['mismatches']) for x in results)))

def span(cfg,face_x=111.):
    import resense.clustering as cl
    if not hasattr(cl,'_off_structure_parts'): return
    results=[]
    for nominal,echo in itertools.product([0.,.099,.100,.101],[1,2]):
        # Exact source wall plus a front face at x=111; bypass connectivity only.
        pts,lab=surface_points(.17,1.73,1.64)
        pts=pts[lab==0]
        hh=np.arange(.11,1.73001,.13)
        angles=np.array([-.3]) if nominal==0 else np.array([-.3,-.3+nominal])
        h,a=np.meshgrid(hh,np.radians(angles))
        face=np.column_stack([np.full(h.size,face_x),face_x*np.tan(a).ravel(),h.ravel()-1.83]).astype(np.float32)
        face=np.repeat(face,echo,axis=0)
        allpts=np.concatenate([pts,face]); heights=allpts[:,2]+1.83
        vox,inv=cl.voxelize(allpts,cfg.cluster)
        b=cl._Blob.of(allpts,np.arange(len(allpts)),len(vox))
        parts=cl._off_structure_parts(b,allpts,heights,np.ones(len(allpts),bool),vox,inv,cfg.cluster)
        results.append(dict(nominal_deg=nominal,echo=echo,face_x=face_x,xyz=arrid(allpts),
            actual_deg=float(np.degrees(np.ptp(np.arctan2(face[:,1].astype(float),face[:,0].astype(float))))),
            parts=[dict(n_vox=p.n_vox,bmin=p.bmin,bmax=p.bmax) for p in parts]))
    save('span.json',results)

def low_witness(cfg):
    from resense.clustering import Cluster
    from resense.detector import Detector,Candidates
    from resense.tracking import Tracker
    if not hasattr(Cluster,'spared'): return
    def make(x,y,z,size,kind='',spared=False,cut=False):
        center=np.array([x,y,z],np.float32); size=np.array(size,np.float32)
        return Cluster(np.arange(12),12,12,center,center-size/2,center+size/2,
            float(x-size[0]/2),y,z+1.83-size[2]/2,z+1.83+size[2]/2,35.,12.,1.,
            zone='gauge',n_gauge=12,kind=kind,spared=spared,cut=cut)
    det=Detector(cfg); tr=Tracker(cfg.tracking); control=Tracker(cfg.tracking); rows=[]
    empty=Candidates(np.empty((0,3),np.float32),np.empty(0),np.empty(0),np.empty(0,bool),
                     np.empty(0),np.empty(0,int),np.empty(0,bool))
    for f in range(20):
        part=make(93.,.50,-.45,[.10,.30,2.54],spared=(f==0),cut=True)
        if f>0: part.zone='warning'; part.reason='column'
        low=make(93.35,.75,-1.70,[.20,.30,.20],kind='low')
        cr=control.update([copy.deepcopy(low)],frame_dt=.1)
        kept=det._not_part_of_corridor_objects([low],[],[part],empty)
        pre=cluster_desc(part); reported=tr.update([part]+kept,frame_dt=.1)
        rows.append(dict(frame=f,low_kept=bool(kept),part_pre=pre,part_post=cluster_desc(part),
                         tracks=[track_desc(t) for t in tr.tracks],stop_ids=[t.id for t in reported if t.reported and t.zone=='gauge'],
                         low_only_control_tracks=[track_desc(t) for t in cr],
                         low_only_control_STOP_ids=[t.id for t in cr if t.reported and t.zone=='gauge']))
    save('low-witness.json',dict(scope='constructed filter/tracker boundary; not a physical scene',frames=rows))

def main(argv):
    ap=argparse.ArgumentParser(); ap.add_argument('--mode',default='all'); a=ap.parse_args(argv)
    cfg=identity()
    azimuth(cfg); span(cfg,93. if a.mode=='span' else 111.); low_witness(cfg)
    if a.mode=='all':
        physical(cfg)
        surface(cfg)
    elif a.mode=='beam':
        physical(cfg,only_beam=True)
