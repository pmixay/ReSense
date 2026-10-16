"""Independent exact non-timing differential plus axis-only min equations."""
import copy
import json
from pathlib import Path
import sys

out = Path(sys.argv[1])
data = {name:json.loads((out/(name+'.json')).read_text()) for name in ('target_on','target_off','control')}
rows, failures = [], []
for on, off, base in zip(*(data[k]['rows'] for k in ('target_on','target_off','control'))):
    assert on['key'] == off['key'] == base['key']
    a,b,c = [copy.deepcopy(v['raw']) for v in (on,off,base)]
    drift = on['wall_drift']
    checks = {}
    for name, key in (('monitored','monitored_range'),('health_clear','clear_distance')):
        checks[name] = a['health'][key] == round(max(0.,min(b['health'][key],drift)),1)
    checks['result_clear'] = a['clear_distance'] == round(max(0.,min(b['clear_distance'],drift)),1)
    for raw in (a,b):
        raw['track'].pop('wall_drift')
        for cl in raw['candidates']:
            assert not cl.pop('spared') and not cl.pop('cut')
    for raw in (a,b,c):
        raw['health'].pop('wall_drift',None)
    checks['target_off_control_exact'] = b == c
    for raw in (a,b,c):
        raw.pop('clear_distance')
        raw['health'].pop('clear_distance'); raw['health'].pop('monitored_range')
    checks['axis_only_geometry_exact'] = a == b == c
    row = dict(key=on['key'],checks=checks,wall_drift=drift,error_at_cap_bin=on['error_at_cap_bin'],
               monitored=[base['raw']['health']['monitored_range'],on['raw']['health']['monitored_range']],
               clear=[base['raw']['clear_distance'],on['raw']['clear_distance']],obstacle=on['raw']['obstacle'])
    rows.append(row)
    if not all(checks.values()): failures.append(row)
answer = dict(frames=len(rows),families=12,checks=len(rows)*5, failures=failures,
              finite_drift=sum(r['wall_drift'] < 1e9 for r in rows),
              monitored_reduced=sum(r['monitored'][1]<r['monitored'][0] for r in rows),
              clear_reduced=sum(r['clear'][1]<r['clear'][0] for r in rows),
              obstacle_frames=sum(r['obstacle'] for r in rows), rows=rows)
assert len(rows) == 96
(out/'scene_comparison.json').write_text(json.dumps(answer,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:v for k,v in answer.items() if k != 'rows'},indent=2))
raise SystemExit(int(bool(failures)))
