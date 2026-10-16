"""Read-only independent authentication/recount of retained H3 result evidence."""
from collections import Counter
import copy
import hashlib
import itertools
import json
from pathlib import Path
import re
import sys

PACKAGE = Path('/work/target/docs/evidence/integration_2026-10-16/h3')
EXTERNAL = Path('/h3-external')
OUT = Path(sys.argv[1])


def load(p): return json.loads(p.read_text())


def digest(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()


def normalized(d):
    d = copy.deepcopy(d)
    d.pop('timing_ms',None)
    h = d['health']
    for k in ('latency_p95_ms','latency_basis','latency_sample_age_frames'): h.pop(k,None)
    before = h['messages']
    h['messages'] = [s for s in before if not re.fullmatch(r'latency p95 \d+ ms over the \d+ ms budget',s)]
    if len(before) != len(h['messages']) and not h['messages'] and h['level'] == 'warn' and h['decision_level'] == 'ok':
        h['level'] = 'ok'
    return d


def diffs(a,b,path=''):
    if isinstance(a,dict) and isinstance(b,dict):
        for k in sorted(set(a)|set(b)):
            p = path+'.'+k if path else k
            if k not in a or k not in b: yield p, a.get(k,'<missing>'),b.get(k,'<missing>')
            else: yield from diffs(a[k],b[k],p)
    elif isinstance(a,list) and isinstance(b,list):
        if len(a) != len(b): yield path+'.length',len(a),len(b)
        for i,(x,y) in enumerate(zip(a,b)): yield from diffs(x,y,path+f'[{i}]')
    elif a != b: yield path,a,b


def numbers(a,b):
    if isinstance(a,dict) and isinstance(b,dict):
        for k in a.keys() & b.keys(): yield from numbers(a[k],b[k])
    elif isinstance(a,list) and isinstance(b,list):
        for x,y in zip(a,b): yield from numbers(x,y)
    elif type(a) in (int,float) and type(b) in (int,float): yield a,b


def main():
    package_files = load(PACKAGE/'HASHES.json')['files']
    for row in package_files:
        p = PACKAGE/row['path']
        assert p.stat().st_size == row['bytes'] and digest(p) == row['sha256'], str(p)
    ext_rows = load(PACKAGE/'EXTERNAL_ARTIFACTS.json')['files']
    # Original result captures, comparison/trace evidence, and copy sources only.
    # No original point-cloud data or held-out protocol is needed or mounted.
    relevant = {r['external_path'] for r in load(PACKAGE/'PACKAGE_MAP.json')}
    relevant.update(r['path'] for r in ext_rows if '/frames/' in r['path'])
    relevant.update(r['path'] for r in ext_rows if r['path'].endswith('/changes.jsonl'))
    checked = []
    for row in ext_rows:
        if row['path'] not in relevant: continue
        p = EXTERNAL/row['path']
        assert p.stat().st_size == row['bytes'] and digest(p) == row['sha256'], str(p)
        checked.append(row)
    mapped = 0
    for row in load(PACKAGE/'PACKAGE_MAP.json'):
        src, dst = EXTERNAL/row['external_path'],PACKAGE/row['package_path']
        if row['mode'] == 'lossless JSONL records as JSON array':
            assert [json.loads(s) for s in src.read_text().splitlines()] == load(dst)
        elif 'CRLF' in row['mode']:
            assert src.read_bytes().replace(b'\r\n',b'\n') == dst.read_bytes()
        elif row['mode'] == 'byte-identical copy':
            assert src.read_bytes() == dst.read_bytes()
        else:
            # Derived summaries have their own package digest, not a copy assertion.
            continue
        mapped += 1
    base = EXTERNAL/'baseline-707ea9cda051-20261016T060147Z-68fb3429/frames'
    target = EXTERNAL/'candidate-f8c088dc4f32-20261016T073403Z-4b64ec55/frames'
    counts, fields_count, datasets = Counter(),Counter(),Counter()
    unexpected, witness = [],None
    for path in sorted(base.glob('*.jsonl')):
        with path.open() as left,(target/path.name).open() as right:
            for index,(la,lb) in enumerate(itertools.zip_longest(left,right)):
                assert la and lb
                a,b = json.loads(la),json.loads(lb)
                assert a['key'] == b['key']
                ra,rb = normalized(a['raw']),normalized(b['raw'])
                sa,sb = normalized(a['serialized']),normalized(b['serialized'])
                counts['frames'] += 1
                datasets[path.name] += 1
                drift = rb['track']['wall_drift']
                counts['finite_drift'] += drift < 1e9
                for representation,old,new in (('raw',ra,rb),('serialized',sa,sb)):
                    assert old['obstacle'] == new['obstacle'] and old['warning'] == new['warning']
                    assert old['nearest_distance'] == new['nearest_distance']
                    assert old['detections'] == new['detections'] and old['warnings'] == new['warnings']
                    for key in ('monitored_range','clear_distance'):
                        assert new['health'][key] == round(max(0.,min(old['health'][key],drift)),1)
                        counts['formula_checks'] += 1
                    assert new['clear_distance'] == round(max(0.,min(old['clear_distance'],drift)),1)
                    counts['formula_checks'] += 1
                    for key,old_value,new_value in diffs(old,new,representation):
                        field = re.sub(r'\[\d+\]','[]',key)
                        fields_count[field] += 1
                        allowed = (key in {representation+'.clear_distance', representation+'.health.clear_distance',representation+'.health.monitored_range',representation+'.track.wall_drift',representation+'.health.wall_drift'}
                                   or re.fullmatch(r'raw\.candidates\[\d+\]\.(cut|spared)',key))
                        if not allowed: unexpected.append(dict(file=path.name,row=index,key=key,before=old_value,after=new_value))
                for va,vb in numbers(ra,rb):
                    counts['common_raw_numbers'] += 1
                    counts['unequal_raw_numbers'] += va != vb
                assert ra['corridor_idx'] == rb['corridor_idx']
                counts['monitored_reduced'] += sb['health']['monitored_range'] < sa['health']['monitored_range']
                counts['clear_reduced'] += sb['clear_distance'] < sa['clear_distance']
                for cl in rb['candidates']:
                    counts['candidates'] += 1
                    counts['cut_true'] += cl['cut']; counts['spared_true'] += cl['spared']
                if path.name == 'new_data_1.jsonl' and index == 1354:
                    witness = dict(key=a['key'],old=ra['candidates'][8],new=rb['candidates'][8],
                                   obstacle=rb['obstacle'],clear=rb['clear_distance'])
    assert counts['frames'] == 18329 and counts['formula_checks'] == 109974
    assert counts['finite_drift'] == 2422 and counts['monitored_reduced'] == 2131 and counts['clear_reduced'] == 1834
    assert counts['candidates'] == 25706 and counts['cut_true'] == 0 and counts['spared_true'] == 6
    assert counts['common_raw_numbers'] == 2432861 and counts['unequal_raw_numbers'] == 5799
    assert len(unexpected) == 2 and all(r['file'] == 'new_data_1.jsonl' and r['row'] == 1354 for r in unexpected)
    assert {r['key'] for r in unexpected} == {'raw.candidates[8].reason','raw.candidates[8].zone'}
    trace = load(PACKAGE/'analysis/promotion_interpretation.json')
    assert witness['new'] == trace['candidate']
    assert trace['matched_tracks'][0]['column_held'] and trace['matched_tracks'][0]['zone'] == 'warning'
    assert not trace['matched_tracks'][0]['reported'] and not witness['obstacle']
    assert trace['spare_observation']['before']['prior_spare_hist'] == [False,False,True,False]
    answer = dict(package_hashes=len(package_files),external_hashes=len(checked),copy_mappings=mapped,
                  external_inventory=checked,counts=dict(counts),field_counts=dict(fields_count),datasets=dict(datasets),
                  classified_non_axis_changes=unexpected,promotion_witness=witness,failures=[])
    OUT.write_text(json.dumps(answer,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:v for k,v in answer.items() if k not in ('external_inventory','field_counts','datasets','promotion_witness')},indent=2))


if __name__ == '__main__': main()
