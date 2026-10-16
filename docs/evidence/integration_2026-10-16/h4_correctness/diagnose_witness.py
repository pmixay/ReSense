"""Investigate retained raw-versus-compact witness schema before altering its oracle."""
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
root = Path(r'C:\Users\alikh\AppData\Local\Temp\opencode\resense-integration-20261016-runs')
path = root/'candidate-f8c088dc4f32-20261016T073403Z-4b64ec55/frames/new_data_1.jsonl'
with path.open() as f:
    for i,line in enumerate(f):
        if i == 1354:
            row = json.loads(line)
            break
raw = row['raw']['candidates'][8]
trace = json.loads((HERE.parent/'h3/analysis/promotion_interpretation.json').read_text())['candidate']
answer = dict(argv=sys.argv,raw_path=str(path),row=1354,key=row['key'],
              raw_only={k:v for k,v in raw.items() if k not in trace},
              trace_only={k:v for k,v in trace.items() if k not in raw},
              unequal_common={k:[raw[k],trace[k]] for k in set(raw)&set(trace) if raw[k] != trace[k]},
              raw_candidate=raw)
with (HERE/'retained_witness_diagnosis.json').open('x') as f: json.dump(answer,f,indent=2); f.write('\n')
print(json.dumps({k:v for k,v in answer.items() if k != 'raw_candidate'},indent=2))
