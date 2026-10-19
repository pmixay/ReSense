"""Independent saved-row matching using the published label boxes and judge tolerances."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
WORK = Path('/tmp/opencode/r3-h1')
labels = json.loads((ROOT/'labels/cloud_with_fake_obj.json').read_text())
tag = sys.argv[1]
base = [json.loads(x) for x in (WORK/'baseline/setO.off.jsonl').read_text().splitlines()]
cand = [json.loads(x) for x in (WORK/tag/'setO.jsonl').read_text().splitlines()]


def matches(rows, name):
    hits = {}
    for r in rows:
        for o in labels.get(f"{r['i']:05d}", []):
            if o.get('label') != name or not o.get('plausible',True) or o.get('n_points',0) <= 0:
                continue
            X=o['distance']
            L,W=o['size'][:2]
            y=sum(p[1] for p in o['bbox'])/2
            if any(abs(d['d']-X) <= max(2,.03*X)+L/2 and abs(d['c'][1]-y)<=1+W/2 for d in r['dets']):
                hits[r['i']] = X
    return hits


out={}
for name in ['thin_hanging','small_center']:
    b,c=matches(base,name),matches(cand,name)
    out[name]=dict(baseline_first=max(b.values(),default=None),candidate_first=max(c.values(),default=None),
                   added=sorted(set(c)-set(b)),lost=sorted(set(b)-set(c)),
                   baseline_hits=b,candidate_hits=c,baseline_truncated_at=790)
    print(name,{k:v for k,v in out[name].items() if not k.endswith('_hits')})
b=json.loads((WORK/'baseline/E6.off.json').read_text())
c=json.loads((WORK/tag/'E6.json').read_text())
hb={r['k'] for r in b['rows'] if r['hit'] and r['n_obj']>0 and r['X']>3}
hc={r['k'] for r in c['rows'] if r['hit'] and r['n_obj']>0 and r['X']>3}
out['E6']=dict(baseline=b['summary'],candidate=c['summary'],added=sorted(hc-hb),lost=sorted(hb-hc))
print('E6 added/lost',out['E6']['added'],out['E6']['lost'])
(WORK/tag/'screen_check.json').write_text(json.dumps(out,indent=2))
