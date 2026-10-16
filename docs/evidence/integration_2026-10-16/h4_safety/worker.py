import hashlib,json,os,sys,time,traceback
from pathlib import Path
out=Path(os.environ['H4_OUT']); out.mkdir(parents=True,exist_ok=False)
start=time.time()
(out/'reviewer_code_hashes.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest()
    for p in Path('/review').glob('*.py')},indent=2)+'\n')
with (out/'worker.txt').open('w',buffering=1) as log:
    sys.stdout=sys.stderr=log
    try:
        if sys.argv[1]=='replay':
            import replay
            replay.main(sys.argv[2:])
        else:
            import components
            components.main(sys.argv[2:])
    except BaseException:
        traceback.print_exc()
        (out/'completion.json').write_text(json.dumps(dict(ok=False,wall_s=time.time()-start)))
        raise
    (out/'completion.json').write_text(json.dumps(dict(ok=True,wall_s=time.time()-start)))
