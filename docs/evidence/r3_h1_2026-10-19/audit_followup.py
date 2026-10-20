"""Exact retained-row audits of final supplemental runs and target examples."""
from collections import Counter
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
W=Path('/tmp/opencode/r3-h1')


def read(p):
    return json.loads(p.read_text())


def score(run):
    visible=[r for r in run['rows'] if r['X'] is not None and r['X']>3 and r['n_obj']>0]
    hits={r['k'] for r in visible if r['hit']}
    first=next((r['X'] for r in visible if r['hit']),None)
    n=0
    held=None
    for i,r in enumerate(sorted(visible,key=lambda r:r['X']),1):
        n+=r['hit']
        if n>=.9*i:
            held=r['X']
    assert (first,held,len(hits))==(run['summary']['first_stop_X'],run['summary']['held_from_X'],run['summary']['stop_frames'])
    return hits


result={'range':{},'falcon':{},'nominal_E6_payloads':{}}
variants=['nominal','pitch_p2','pitch_m2','roll_p2','drop30_s1','drop30_s2','drop30_s3','drop30_s7','dedup']
for name in ['E6-'+v for v in variants]+['A-axis','C-person']:
    b=read(W/'supplement-range'/f'reference-{name}.json')
    c=read(W/'supplement-final-range'/f'candidate-{name}.json')
    assert len(b['rows'])==len(c['rows'])
    assert [tuple(r.get(k) for k in ['k','X','Y','Zb','n_obj']) for r in b['rows']]==[
           tuple(r.get(k) for k in ['k','X','Y','Zb','n_obj']) for r in c['rows']]
    bs,cs=score(b),score(c)
    def off(run):
        return {r['k'] for r in run['rows'] if r['decision']=='STOP' and not r['hit']}
    result['range'][name]={'baseline':b['summary'],'candidate':c['summary'],
                           'lost_matched':sorted(bs-cs),'added_matched':sorted(cs-bs),
                           'new_off_object_STOP_decisions':sorted(off(c)-off(b))}
    assert not bs-cs,name
    assert not off(c)-off(b),name
    print(name,'first',b['summary']['first_stop_X'],'->',c['summary']['first_stop_X'],
          'held',b['summary']['held_from_X'],'->',c['summary']['held_from_X'],
          'matched',len(bs),'->',len(cs))
for side in ['reference','candidate']:
    d=W/('supplement-falcon' if side=='reference' else 'supplement-final-falcon')
    rr=[json.loads(x) for x in (d/f'{side}-Falcon.jsonl').read_text().splitlines()]
    assert [r['i'] for r in rr]==list(range(4443))
    result['falcon'][side]=dict(STOP=[r['i'] for r in rr if r['obstacle']],frames=len(rr))
    if side=='reference':
        previous=rr
    else:
        changes={field:[b['i'] for b,c in zip(previous,rr) if b[field]!=c[field]]
                 for field in ['decision','dets','warns','warning','nearest']}
        result['falcon']['changed_fields']=changes
        assert not any(changes.values())
print('Falcon retained exact detection/decision payloads',len(result['falcon']['candidate']['STOP']))
nodes=[read(W/f'{s}-target-inspection.nodes.json') for s in ['reference','candidate']]
assert len(nodes[0])==len(nodes[1])==340
added_unmatched=[]
new_dets=[]
for b,c in zip(*nodes):
    assert b['info']==c['info']
    bc,cc=[Counter(json.dumps(d,sort_keys=True) for d in r['node']['dets']) for r in [b,c]]
    assert not bc-cc
    info=c['info']
    for raw,n in (cc-bc).items():
        d=json.loads(raw)
        X,Y=info.get('X'),info.get('Y')
        matched=X is not None and Y is not None and X>3 and abs(d['d']-X)<=max(2,.03*X)+.025 and abs(d['c'][1]-Y)<=1.025
        record=dict(k=c['node']['i'],matched=bool(matched),count=n,detection=d)
        new_dets.append(record)
        if not matched:
            added_unmatched.append(record)
assert new_dets and not added_unmatched
result['nominal_E6_payloads']=dict(paired_frames=340,added_detections=new_dets,
                                   lost_old_payloads=0,added_unmatched=added_unmatched)
(HERE/'final-supplement-audit.json').write_text(json.dumps(result,indent=2)+'\n')
