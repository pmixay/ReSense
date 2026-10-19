"""Recount all saved gate/X3 rows and exact object matches; validate negative controls."""
from collections import Counter
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tarfile

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
W=Path('/tmp/opencode/r3-h1')
DATA=Path('/tmp/opencode/resense-b4-data/decoded')
p=argparse.ArgumentParser()
p.add_argument('--revision',default='')
args=p.parse_args()
PREFIX=args.revision+'-' if args.revision else ''
sys.path.insert(0,str(ROOT/'scripts'))
import robustness_battery as rb  # noqa: E402
import range_attrib as ra  # noqa: E402
from resense.config import DetectorConfig  # noqa: E402


def read(p):
    return json.loads(p.read_text())


def rows(p):
    return [json.loads(x) for x in p.read_text().splitlines()]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def match_sets(rr,labels):
    result={}
    for r in rr:
        for o in labels.get(f"{r['i']:05d}",[]):
            if not o.get('plausible',True) or o.get('n_points',1)==0:
                continue
            L,V=o.get('size',[.5,.5,.5])[:2]
            y=sum(p[1] for p in o['bbox'])/2
            found=any(abs(d['d']-o['distance'])<=max(2,.03*o['distance'])+L/2
                      and abs(d['c'][1]-y)<=1+V/2 for d in r['dets'])
            if found:
                name=o.get('label',o.get('name'))
                intent='inside' if o['in_gauge'] else 'outside'
                result.setdefault(name+':'+intent,set()).add(r['i'])
    return result


review=read(HERE/f'{PREFIX}gate-frame-review.json')
gate={k:{'frames':v['frames'],'lost':v['lost_stop_frames'],'added':v['added_stop_frames'],
         'old_payload_changes':v['frames_with_changed_or_missing_old_detection_payload'],
         'field_counts':{f:len(ids) for f,ids in v['changed_fields'].items()}}
      for k,v in review['ordinary'].items()}
assert not any(v['lost'] for v in gate.values())
assert not any(s['lost_hits'] for s in review['set_F'])
assert not any(v['added'] for k,v in gate.items() if k!='cloud_with_fake_obj')
metrics=review['gate_metrics']
assert not any(r['fails'] or r['allowed'] for r in metrics)
non_time=[r for r in metrics if not r['metric'].startswith('latency_ms.')]
print('gate',Counter(r['verdict'] for r in non_time),
      'added rows',{k:v['added'] for k,v in gate.items() if v['added']})
result={'gate':gate,'gate_metric_counts':dict(Counter(r['verdict'] for r in non_time)),
        'gate_changed_metrics':[r for r in non_time if r['verdict']!='same'],
        'set_F_lost_hits':sum(len(s['lost_hits']) for s in review['set_F']),
        'set_F_added_hits':sum(len(s['added_hits']) for s in review['set_F']),
        'X3':{},'attribution':{},'positive_controls':{}}
def sustained(sequence):
    visible=sorted((r for r in sequence['rows'] if r['n']>0),key=lambda r:r['d'])
    count=n=0
    passed=[]
    from itertools import groupby
    for distance,group in groupby(visible,key=lambda r:r['d']):
        group=list(group)
        count+=sum(bool(r['hit']) for r in group)
        n+=len(group)
        if n>=5 and count>=.9*n:
            passed.append(distance)
    return max(passed,default=None)
sf_b=read(W/'gate-reference-work/setF_straight.json')
sf_c=read(W/f'gate-{PREFIX}candidate-work/setF_straight.json')
sf=[]
for b,c in zip(sf_b['sequences'],sf_c['sequences']):
    x,y=sustained(b),sustained(c)
    assert x is None or (y is not None and y>=x)
    if b['kind']=='cable':
        sf.append(dict(file=b['file0'],baseline_sustained=x,candidate_sustained=y,
                       baseline_hit_rows=sum(r['hit'] for r in b['rows']),
                       candidate_hit_rows=sum(r['hit'] for r in c['rows'])))
result['set_F_cable_sustained_population']=sf
print('Set F cable per-sequence sustained',sf)
base,cur=read(W/'x3-reference.json'),read(W/f'x3-{PREFIX}candidate.json')
assert cur['status']=='PASS' and len(cur['entries'])==40
assert base['sources']==cur['sources']
for key in base['entries']:
    bag,variant=key.split('/')
    b,c=(rows(Path(s['entries'][key]['raw_path'])) for s in [base,cur])
    meta=read(DATA/bag/'meta.json')
    assert [r['i'] for r in b]==[r['i'] for r in c]==list(range(0,len(meta),2 if variant=='hz5' else 1))
    labels=read(ROOT/f'labels/{bag}.json') if bag in ['doubleT_obstacle','cloud_with_fake_obj'] else None
    for rr,s in [(b,base),(c,cur)]:
        assert rb.summarize(rr,labels)==s['entries'][key]['metrics']
        assert sha(Path(s['entries'][key]['raw_path']))==s['entries'][key]['raw_sha256']
    bs={r['i'] for r in b if r['decision']=='STOP'}
    cs={r['i'] for r in c if r['decision']=='STOP'}
    item={'frames':len(b),'baseline_STOP':len(bs),'candidate_STOP':len(cs),
          'lost_STOP':sorted(bs-cs),'added_STOP':sorted(cs-bs)}
    if labels:
        bm,cm=match_sets(b,labels),match_sets(c,labels)
        item['lost_matches']={k:sorted(v-cm.get(k,set())) for k,v in bm.items() if k.endswith(':inside')}
        item['added_matches']={k:sorted(v-bm.get(k,set())) for k,v in cm.items()}
        assert not any(item['lost_matches'].values()),(key,item)
    assert not item['lost_STOP'],(key,item)
    if bag in ['squareT_platform_squareT_switch','roundT_squareT_pressureGate_squareT']:
        assert bs==cs
    result['X3'][key]=item
print('X3 exact old STOP and inside-match losses: 0 /',sum(x['frames'] for x in result['X3'].values()))
# Positive controls for the exact-loss detector itself.
positive=next(v for v in result['X3'].values() if v['baseline_STOP']>0)
assert positive['baseline_STOP']>0
bp=rows(Path(base['entries']['doubleT_obstacle/nominal']['raw_path']))
removed=deepcopy(bp)
idx=next(i for i,r in enumerate(removed) if r['dets'])
removed[idx]['decision']='GO'
removed[idx]['dets']=[]
lost={r['i'] for r in bp if r['decision']=='STOP'}-{r['i'] for r in removed if r['decision']=='STOP'}
assert lost=={bp[idx]['i']}
bm=match_sets(bp,read(ROOT/'labels/doubleT_obstacle.json'))
cm=match_sets(removed,read(ROOT/'labels/doubleT_obstacle.json'))
assert any(v-cm.get(k,set()) for k,v in bm.items())
result['positive_controls']['deleted_known_positive_detection_is_found']=True
# Check every attribution row on both sources, not just whether each category exists.
for side in ['reference','candidate']:
    for case in ['E6','setO']:
        trace_dir=W/('trace-'+args.revision if args.revision and side=='candidate' else 'trace')
        r=read(trace_dir/f'{side}-{case}.attrib.json')
        assert r['hooks_off']['equal']
        cfg=DetectorConfig()
        checked=[]
        for row in r['rows']:
            if row['hit']:
                continue
            ok,ev=ra.recheck(row,r['frames'][str(row['k'])],cfg)
            # Current-source dynamic thresholds are recorded at the firing branch.
            assert ok,(side,case,row,ev)
            assert row['cause']==row['recon_cause']
            checked.append({'k':row['k'],'cause':row['cause'],'confirmed':ok,'evidence':ev})
        result['attribution'][f'{side}-{case}']={'rows':len(r['rows']),'checked':checked,
                                                'counts':dict(Counter(x.get('cause','STOP') for x in r['rows']))}
# Historical X3: verify raw files against their original hashes, preserve source mismatches.
hist=read(ROOT/'docs/evidence/p4_eval_1.1.0_2026-10-16/battery_1.1.0_linux_haswell.json')
with tarfile.open(ROOT/'docs/evidence/p4_eval_1.1.0_2026-10-16/raw/p4_raw_2026-10-16.tar.xz') as t:
    members={m.name:m for m in t if m.isfile() and 'battery_1.1.0_linux_haswell.raw/' in m.name
             and m.name.endswith('/probe.jsonl')}
    comparisons={}
    for key,entry in hist['entries'].items():
        member=next(m for name,m in members.items() if name.endswith('/'+key+'/probe.jsonl'))
        raw=t.extractfile(member).read()
        assert hashlib.sha256(raw).hexdigest()==entry['raw_sha256']
        bag,variant=key.split('/')
        labels=read(ROOT/f'labels/{bag}.json') if bag in ['doubleT_obstacle','cloud_with_fake_obj'] else None
        assert rb.summarize([json.loads(x) for x in raw.splitlines()],labels)==entry['metrics']
        comparisons[key]=rb.compare_metrics(entry['metrics'],cur['entries'][key]['metrics'])
source_diffs={}
for bag in hist['sources']:
    hfiles={v['name']:v for v in hist['sources'][bag]['files']}
    cfiles={v['name']:v for v in cur['sources'][bag]['files']}
    different=sorted(name for name in hfiles.keys()|cfiles.keys() if hfiles.get(name)!=cfiles.get(name))
    source_diffs[bag]={'different_payload_entries':different,
                       'metadata_equal':hist['sources'][bag]['meta_sha256']==cur['sources'][bag]['meta_sha256']}
historical=dict(raw_reports_verified=40,source_differences=source_diffs,
                comparison=comparisons,
                numerical_checks_pass=all(r['passed'] for rr in comparisons.values() for r in rr),
                strict_source_parity=all(not v['different_payload_entries'] and v['metadata_equal']
                                         for v in source_diffs.values()))
result['historical_1_1_0']=historical
print('historical X3 numeric',historical['numerical_checks_pass'],'container byte parity',historical['strict_source_parity'])
if (HERE/'canonical-inputs.json').exists():
    canonical=read(HERE/'canonical-inputs.json')
    historical['canonical_windows_input_check']={b:{'checked':v['arrays_checked'],'mismatches':v['mismatches']}
                                               for b,v in canonical['bags'].items()}
result['measured_source']=read(HERE/f'gate-{PREFIX}candidate.json')['code']
(HERE/f'{PREFIX}raw-audit.json').write_text(json.dumps(result,indent=2)+'\n')
print('raw audit complete')
