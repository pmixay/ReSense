"""Streaming comparison and compact packaging of independently measured H4 outputs."""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path

ap=argparse.ArgumentParser(); ap.add_argument('--root',required=True); ap.add_argument('--out',required=True)
a=ap.parse_args(); R=Path(a.root); O=Path(a.out); O.mkdir(exist_ok=True)
EXPORTS={'physical_candidate_cases.json','physical_changed_cases.json','physical_witnesses.json',
         'dark_excess_witnesses.json','dark_inherited_witnesses.json','surface_cases.json'}
def load(p): return json.loads(p.read_text())
def save(n,v):
    base=R/'exports' if n in EXPORTS else O
    base.mkdir(exist_ok=True)
    (base/n).write_bytes((json.dumps(v,indent=2)+'\n').encode())
def rows(p):
    with p.open() as f:
        for line in f: yield json.loads(line)

real={}; excess=[]
for bag in ['roundT_doubleT','squareT_platform_squareT_switch','ride_1','ride_3']:
    s=R/'replay-sealed-all'/(bag+'.jsonl'); c=R/'replay-candidate-all'/(bag+'.jsonl')
    if not (s.exists() and c.exists()): continue
    counts=Counter(); stops=[[],[]]; warnings=[[],[]]; descriptor_changes=[]
    for x,y in zip(rows(s),rows(c),strict=True):
        assert x['frame_id']==y['frame_id']
        for k in ['input','cache_sha256','mask','stamp']: assert x[k]==y[k],(bag,k,x['frame_id'])
        counts['frames']+=1
        for j,v in enumerate([x,y]):
            if v['serialized']['obstacle']: stops[j].append(v['frame_id'])
            if v['serialized']['warning']: warnings[j].append(v['frame_id'])
        for k in ['obstacle','warning','detections','warnings','nearest_distance']:
            if x['serialized'][k]!=y['serialized'][k]:
                counts[k+'_changed_frames']+=1
                descriptor_changes.append(dict(frame=x['frame_id'],field=k,sealed=x['serialized'][k],candidate=y['serialized'][k]))
    real[bag]=dict(counts=counts,sealed_stop_frames=stops[0],candidate_stop_frames=stops[1],
                   stop_sets_equal=stops[0]==stops[1],warning_sets_equal=warnings[0]==warnings[1],
                   descriptor_changes=descriptor_changes)
    d=R/'replay-candidate-dark'/(bag+'.jsonl')
    complete=(R/'replay-candidate-dark'/'completion.json').exists()
    if bag.startswith('ride') and d.exists() and complete:
        dark_stops=[]; changed_calls=[]
        for x,y,z in zip(rows(s),rows(c),rows(d),strict=True):
            assert x['frame_id']==z['frame_id']
            assert x['input']==z['input'] and x['mask']==z['mask'] and x['stamp']==z['stamp']
            if z['serialized']['obstacle']: dark_stops.append(z['frame_id'])
            for call in z['observer']:
                if call['plain_answer']!=call['masked_answer']:
                    changed_calls.append(dict(frame=z['frame_id'],**call))
            if z['serialized']['obstacle'] and not x['serialized']['obstacle']:
                matches=[]
                for det in z['serialized']['detections']:
                    options=x['serialized']['warnings']+x['serialized']['detections']
                    dist=lambda v: sum((aa-bb)**2 for aa,bb in zip(v['center'],det['center']))**.5
                    near=min(options,key=dist) if options else None
                    matches.append(dict(dark_detection=det,sealed_nearest=near,
                                        center_distance=None if near is None else dist(near)))
                excess.append(dict(bag=bag,frame=z['frame_id'],index=z['i'],stamp=z['stamp'],matches=matches,
                    dark_candidates=z['candidates'],dark_tracks=z['tracks'],observer=z['observer'],spares=z['spares'],
                    sealed_tracks=x['tracks']))
        real[bag]['dark']=dict(stop_frames=dark_stops,excess_vs_sealed=sorted(set(dark_stops)-set(stops[0])),
            removed_vs_sealed=sorted(set(stops[0])-set(dark_stops)),answer_changes=changed_calls)
save('real_comparison.json',real); save('dark_excess_witnesses.json',excess)

inherited={}; witnesses=[]; track_matches=[]
di=R/'replay-candidate-dark-inherited'
if (di/'completion.json').exists() and load(di/'completion.json')['ok']:
    for bag in ['ride_1','ride_3']:
        stopsets=[[],[]]; answer_changes=[]; excess_frames=[]
        for x,z in zip(rows(R/'replay-sealed-all'/(bag+'.jsonl')),rows(di/(bag+'.jsonl')),strict=True):
            assert x['frame_id']==z['frame_id']
            for k in ['input','cache_sha256','mask','stamp']: assert x[k]==z[k]
            for j,v in enumerate([x,z]):
                if v['serialized']['obstacle']: stopsets[j].append(v['frame_id'])
            for call in z['observer']:
                if call['plain_answer']!=call['masked_answer']: answer_changes.append(dict(frame=z['frame_id'],**call))
            if z['serialized']['obstacle'] and not x['serialized']['obstacle']:
                excess_frames.append(z['frame_id'])
                witnesses.append(dict(bag=bag,sealed=x,dark=z))
                for det in z['serialized']['detections']:
                    options=x['serialized']['warnings']
                    dist=lambda v:sum((aa-bb)**2 for aa,bb in zip(v['center'],det['center']))**.5
                    near=min(options,key=dist) if options else None
                    track_matches.append(dict(bag=bag,frame=z['frame_id'],dark_detection=det,
                        nearest_sealed_warning=near,center_distance=None if near is None else dist(near),
                        dark_track=[t for t in z['tracks'] if t['id']==det['id']],
                        sealed_track=[] if near is None else [t for t in x['tracks'] if t['id']==near['id']]))
        inherited[bag]=dict(frames=1409,sealed_STOP_frames=stopsets[0],inherited_dark_STOP_frames=stopsets[1],
            excess=excess_frames,lost=sorted(set(stopsets[0])-set(stopsets[1])),answer_changes=answer_changes)
    save('dark_inherited_comparison.json',inherited)
    save('dark_inherited_witnesses.json',witnesses)
    save('dark_inherited_track_matches.json',track_matches)

promotion=R/'replay-candidate-all'/'ride_1-promotion.json'
if promotion.exists():
    row=load(promotion)
    target=[s for s in row['spares'] if abs(s['pre']['distance']-73.55999755859375)<1e-5]
    save('promotion.json',dict(frame=row['frame_id'],index=row['i'],cache_sha256=row['cache_sha256'],input=row['input'],
        obstacle=row['serialized']['obstacle'],nearest=row['serialized']['nearest_distance'],
        clear=row['serialized']['clear_distance'],witness=target))

for src in ['sealed','candidate']:
    p=R/('replay-'+src+'-all')
    if (p/'summary.json').exists():
        v=load(p/'summary.json')
        save(src+'-replay-validation.json',{k:dict(frames=x['frames'],h3_non_timing_mismatches=x['h3_non_timing_mismatches']) for k,x in v.items()})
    if (p/'identity.json').exists(): save(src+'-identity.json',load(p/'identity.json'))

s=R/'components-sealed-all'; c=R/'components-candidate-all'
if (c/'physical-summary.json').exists():
    overview=defaultdict(Counter)
    for x in load(c/'physical-derived-summary.json'):
        p=x['params']; g='band_'+str(p['band']) if p['band'] else 'beam' if p['beam'] else 'multi' if p['multi'] else 'top_'+str(p['top'])
        overview[g]['cases']+=1
        for k,v in x['matched_stop_frames'].items():
            overview[g]['matched_STOP_frames']+=len(v)
            overview[g]['inside_objects_without_STOP']+=int(x['inside'] and not v)
    save('physical_candidate_overview.json',dict(overview))
if all((p/'completion.json').exists() and load(p/'completion.json')['ok'] for p in [s,c]):
    ss=load(s/'physical-derived-summary.json'); cc=load(c/'physical-derived-summary.json'); ps={}; diffs=[]
    assert len(ss)==len(cc)
    identity_checks={}
    hold_checks=Counter(); rearm_delays=[]; rearm_witness=[]
    for kind in ['physical','surface']:
        checked=0
        for x,y in zip(rows(s/(kind+'.jsonl')),rows(c/(kind+'.jsonl')),strict=True):
            for k in ['case','params','xyz','labels']:
                assert x[k]==y[k],(kind,k,x['case'])
            if kind=='physical': assert x['ring']==y['ring'] and x['ring_mode']==y['ring_mode'] and x['dropout']==y['dropout']
            if kind=='physical':
                stop=lambda frame:set(t['physical_label'] for t in frame['tracks'] if t['reported'] and t['zone']=='gauge')
                for label in stop(y['frames'][8]):
                    if label<=0: continue
                    hold_checks['reported_before_dropout']+=1
                    hold_checks['held_first_missing_frame']+=int(label in stop(y['frames'][9]))
                    hold_checks['released_second_missing_frame']+=int(label not in stop(y['frames'][10]))
                    hold_checks['STOP_on_first_return']+=int(label in stop(y['frames'][11]))
                    hold_checks['STOP_on_second_return']+=int(label in stop(y['frames'][12]))
                    if label not in stop(y['frames'][11]):
                        rearm_delays.append(dict(case=y['case'],params=y['params'],ring_mode=y['ring_mode'],dropout=y['dropout'],
                            label=label,STOP_frames=[f['frame'] for f in y['frames'] if label in stop(f)]))
                        if y['case']==44 and y['ring_mode']=='highest' and y['dropout']==0:
                            rearm_witness.append(y)
            checked+=1
        identity_checks[kind]=checked
    save('component_input_identity.json',identity_checks)
    save('hold_release.json',dict(hold_checks))
    save('rearm_delays.json',rearm_delays)
    for row in rearm_witness:
        for f in row['frames']:
            f.pop('stop_labels',None); f.pop('stop_ids',None)
            f['STOP_ids']=[t['id'] for t in f['tracks'] if t['reported'] and t['zone']=='gauge']
    save('rearm_witness.json',rearm_witness)
    totals=Counter(); by=defaultdict(Counter)
    for x,y in zip(ss,cc,strict=True):
        for k in ['case','params','ring_mode','dropout','object_returns']: assert x[k]==y[k]
        p=x['params']; group='band_'+str(p['band']) if p['band'] else 'beam' if p['beam'] else 'multi' if p['multi'] else 'top_'+str(p['top'])
        z=by[group]; z['cases']+=1
        for k,v in x['matched_stop_frames'].items():
            old=set(v); new=set(y['matched_stop_frames'][k])
            z['sealed_matched_STOP_frames']+=len(old); z['candidate_matched_STOP_frames']+=len(new)
            z['new_STOP_frames']+=len(new-old); z['lost_STOP_frames']+=len(old-new)
            if y['inside']:
                z['inside_objects']+=1
                z['inside_no_STOP_objects']+=int(not new)
        z['candidate_background_STOP_frames']+=len(y['background_stop_frames'])
        if x['matched_stop_frames']!=y['matched_stop_frames'] or x['background_stop_frames']!=y['background_stop_frames']:
            diffs.append(dict(sealed=x,candidate=y))
    ps=dict(cases=len(ss),updates_per_source=20*len(ss),groups=dict(by),changed_cases=len(diffs))
    save('physical_comparison.json',ps); save('physical_changed_cases.json',diffs)
    save('physical_candidate_cases.json',cc)
    # Record per-scene actual geometries, masks, state witnesses only for a small deterministically chosen sample.
    picks={}
    for x in cc:
        p=x['params']
        if x['ring_mode']=='highest' and x['dropout']==0 and p['d'] in [67.,109.] and p['y']==.68 and p['w']==.46:
            picks[(x['case'],x['ring_mode'],x['dropout'])]=True
    selected=[x for x in rows(c/'physical.jsonl') if (x['case'],x['ring_mode'],x['dropout']) in picks]
    for row in selected:
        for f in row['frames']:
            f['initial_adapter_stop_labels_INVALID']=f.pop('stop_labels')
            f['initial_adapter_stop_ids_INVALID']=f.pop('stop_ids')
            f['stop_labels']=sorted(set(t['physical_label'] for t in f['tracks'] if t['reported'] and t['zone']=='gauge'))
            f['stop_ids']=[t['id'] for t in f['tracks'] if t['reported'] and t['zone']=='gauge']
    save('physical_witnesses.json',selected)
    tall=[x for x in selected if x['case']==45][0]
    save('tall_miss_witness.json',dict(params=tall['params'],xyz=tall['xyz'],ring=tall['ring'],labels=tall['labels'],
        object_returns=tall['object_returns'],candidate=tall['frames'][0]['pre'],
        per_frame=[dict(frame=f['frame'],STOP_ids=f['stop_ids'],tracks=f['tracks']) for f in tall['frames']]))
    surf=[]; groups=defaultdict(Counter); shortening=[]
    for x,y in zip(load(s/'surface-derived-summary.json'),load(c/'surface-derived-summary.json'),strict=True):
        assert x['case']==y['case'] and x['params']==y['params']
        z=groups[str(y['params']['residual'])]; z['cases']+=1; z['cuts']+=y['cut']; z['spared']+=y['spared']
        for k,v in x['matched_stop_frames'].items():
            old=set(v); new=set(y['matched_stop_frames'][k])
            z['sealed_matched_STOP_frames']+=len(old); z['candidate_matched_STOP_frames']+=len(new)
            z['lost_STOP_frames']+=len(old-new)
        for part in y['initial']:
            if not part.get('cut'): continue
            box=min(y['boxes'],key=lambda b:abs(b['bmin'][0]-part['distance']))
            shortening.append(dict(case=y['case'],params=y['params'],label=box['label'],
                expected_box=box,cut_part=part,
                bottom_shortened=part['bbox_min'][2]>box['bmin'][2]+1e-5,
                top_shortened=part['bbox_max'][2]<box['bmax'][2]-1e-5))
        if y['cut'] or x['matched_stop_frames']!=y['matched_stop_frames']: surf.append(dict(sealed=x,candidate=y))
    save('surface_comparison.json',dict(groups=dict(groups),changed_or_cut_cases=len(surf)))
    save('surface_cases.json',surf)
    save('surface_shortening.json',dict(parts=len(shortening),bottom_shortened=sum(x['bottom_shortened'] for x in shortening),
        top_shortened=sum(x['top_shortened'] for x in shortening),witnesses=shortening))
    for n in ['span.json','azimuth.json','low-witness.json']:
        if (c/n).exists() and n!='low-witness.json': save(n,load(c/n))

sp=R/'components-candidate-span'
if (sp/'completion.json').exists():
    save('span-corrected-fixture.json',load(sp/'span.json'))
    save('low-witness-corrected.json',load(sp/'low-witness.json'))
    low=load(sp/'low-witness.json')
    save('low-witness-summary.json',dict(scope=low['scope'],frames=[dict(frame=x['frame'],low_kept=x['low_kept'],
        part_pre_reason=x['part_pre']['reason'],part_post_reason=x['part_post']['reason'],
        STOP_ids=x['stop_ids'],control_STOP_ids=x['low_only_control_STOP_ids']) for x in low['frames']]))

bs=R/'components-sealed-beam'; bc=R/'components-candidate-beam'
if all((p/'completion.json').exists() and load(p/'completion.json')['ok'] for p in [bs,bc]):
    save('beam-corrected-comparison.json',dict(sealed=load(bs/'physical-summary.json'),candidate=load(bc/'physical-summary.json')))
    for x,y in zip(rows(bs/'physical.jsonl'),rows(bc/'physical.jsonl'),strict=True):
        for k in ['case','params','xyz','labels','ring']: assert x[k]==y[k]
        for f in y['frames']:
            assert f['stop_ids']==[t['id'] for t in f['tracks'] if t['reported'] and t['zone']=='gauge']

inventory={}
for p in sorted(R.rglob('*')):
    if p.is_file():
        h=hashlib.sha256()
        with p.open('rb') as f:
            for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
        inventory[p.relative_to(R).as_posix()]=dict(bytes=p.stat().st_size,sha256=h.hexdigest())
save('EXTERNAL_ARTIFACTS.json',dict(root=str(R),files=inventory))
print(json.dumps(dict(real={k:dict(frames=v['counts']['frames'],sealed_STOP=len(v['sealed_stop_frames']),
    candidate_STOP=len(v['candidate_stop_frames']),changes=len(v['descriptor_changes']),
    dark_STOP=len(v.get('dark',{}).get('stop_frames',[])),excess=len(v.get('dark',{}).get('excess_vs_sealed',[]))) for k,v in real.items()},
    inherited_dark={k:dict(STOP=len(v['inherited_dark_STOP_frames']),excess=len(v['excess'])) for k,v in inherited.items()},
    physical=ps if 'ps' in locals() else None),indent=2))
