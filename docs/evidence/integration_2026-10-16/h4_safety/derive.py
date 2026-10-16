"""Correct STOP counts from immutable raw component tracker snapshots."""
import argparse,json
from pathlib import Path
ap=argparse.ArgumentParser(); ap.add_argument('root'); a=ap.parse_args(); root=Path(a.root)
for source in ['sealed','candidate']:
    d=root/('components-'+source+'-all')
    for kind in ['physical','surface']:
        original=json.loads((d/(kind+'-summary.json')).read_text())
        out=[]
        with (d/(kind+'.jsonl')).open() as f:
            for old,line in zip(original,f,strict=True):
                row=json.loads(line)
                assert old['case']==row['case']
                stops={k:[] for k in old['matched_stop_frames']}
                background=[]
                for state in row['frames']:
                    matched=set(t['physical_label'] for t in state['tracks'] if t['reported'] and t['zone']=='gauge')
                    for k in stops:
                        if int(k) in matched: stops[k].append(state['frame'])
                    if 0 in matched: background.append(state['frame'])
                revised=dict(old,matched_stop_frames=stops,derived_from='raw tracks: reported and zone==gauge')
                if kind=='physical': revised['background_stop_frames']=background
                out.append(revised)
        (d/(kind+'-derived-summary.json')).write_text(json.dumps(out,indent=2)+'\n')
        print(source,kind,len(out),'derived')
