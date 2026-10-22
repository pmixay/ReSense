import json,sys
a=[json.loads(l) for l in open(sys.argv[1])]; b=[json.loads(l) for l in open(sys.argv[2])]
from collections import Counter
ca=Counter(r['decision'] for r in a); cb=Counter(r['decision'] for r in b)
print("decisions",dict(ca),"->",dict(cb), "frames",len(a),len(b))
nd=0
for x,y in zip(a,b):
    if x['decision']!=y['decision'] or x['det']!=y['det']:
        nd+=1
        if nd<=40: print(x['i'],x['decision'],'->',y['decision'],[(d['d'],d['lat'],d['zone'],d['reason']) for d in x['det']],'|',[(d['d'],d['lat'],d['w']) for d in y['det']],'added',y['added'],'curve',y['curve'] and round(y['curve']['valid']))
print("frames differing in decision/dets:",nd)
cur=[y for y in b if y['curve']]; print("curve frames",len(cur),"added>0 frames",sum(1 for y in b if y['added']))
