"""Keep every X3 unmatched-alarm increase explicit; inspect actual saved full states."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
W=Path('/tmp/opencode/r3-h1')
sys.path.insert(0,str(ROOT/'scripts'))
import robustness_battery as rb  # noqa: E402

labels=json.loads((ROOT/'labels/cloud_with_fake_obj.json').read_text())
reports=[json.loads((W/f'x3-{s}.json').read_text()) for s in ['reference','final-candidate']]
trace=json.loads((W/'carry-final.attrib.json').read_text())
assert trace['hooks_off']['equal']
meta=json.loads(Path('/tmp/opencode/resense-b4-data/decoded/cloud_with_fake_obj/meta.json').read_text())
result={}
for variant in rb.VARIANTS:
    rr=[[json.loads(x) for x in Path(r['entries'][f'cloud_with_fake_obj/{variant}']['raw_path']).read_text().splitlines()]
        for r in reports]
    flags=[]
    for rows in rr:
        ids=set()
        for row in rows:
            used={j for o in labels.get(f"{row['i']:05d}",[]) if o.get('n_points',1)>0
                  for j,d in enumerate(row['dets']) if rb.matches(d,o)}
            if row['obstacle'] and row['dets'] and not used:
                ids.add(row['i'])
        flags.append(ids)
    added=flags[1]-flags[0]
    record={'baseline_unmatched_frames':len(flags[0]),'candidate_unmatched_frames':len(flags[1]),
            'added_unmatched_frames':sorted(added),'removed_unmatched_frames':sorted(flags[0]-flags[1]),
            'examples':[]}
    for row in rr[1]:
        if row['i'] not in added:
            continue
        e=dict(i=row['i'],dets=row['dets'],labels=labels.get(f"{row['i']:05d}",[]))
        if variant=='nominal' and str(row['i']) in trace['frames']:
            snap=trace['frames'][str(row['i'])]
            e['full_state']=snap
            t=next(t for t in snap['tracks'] if t['reported'] and t['last_kind']=='hanging')
            assignment=t['branch']['report_assignment']
            assert not assignment['q'] and assignment['reported_before']
            assert 0<assignment['misses']<=assignment['hold_misses'] and t['reported']
            e['firing_report_assignment']=assignment
            positions={int(k):o['distance'] for k,oo in labels.items() if k.isdigit() for o in oo
                       if o.get('label')=='thin_hanging' and o.get('n_points',0)>0}
            before=max(k for k in positions if k<row['i'])
            after=min(k for k in positions if k>row['i'])
            fraction=(meta[row['i']]['stamp']-meta[before]['stamp'])/(meta[after]['stamp']-meta[before]['stamp'])
            expected=positions[before]+fraction*(positions[after]-positions[before])
            e['independent_label_interpolation']=dict(before=before,after=after,distance=expected,
                                                       predicted_distance=row['dets'][0]['d'])
            assert abs(expected-row['dets'][0]['d'])<.05
        record['examples'].append(e)
    result[variant]=record
    if added or flags[0]-flags[1]:
        print(variant,'unmatched',len(flags[0]),'->',len(flags[1]),'added',sorted(added),'removed',sorted(flags[0]-flags[1]))
        for e in record['examples']:
            print(' example',e['i'],e['dets'],'labels',[(o.get('label'),o.get('n_points')) for o in e['labels']])
            if 'full_state' in e:
                print(' tracks',[(t['id'],t['misses'],t['last_kind'],t.get('branch',{}).get('gates'))
                                 for t in e['full_state']['tracks'] if t['reported']])
(HERE/'unmatched-alarm-audit.json').write_text(json.dumps(result,indent=2)+'\n')
