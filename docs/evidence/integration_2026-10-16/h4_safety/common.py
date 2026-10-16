"""Independent H4 evidence helpers. No production source writes."""
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import subprocess
import numpy as np

ROOT = Path(os.environ['RESENSE_REPO'])
OUT = Path(os.environ['H4_OUT'])
OUT.mkdir(parents=True, exist_ok=True)
SEALED = '707ea9cda051369326fb9407c42488c1033dad76'
H3 = 'f8c088dc4f3243fbd15a3aae9be0459e8a0aa941'
TARGET = '7cc640fb39698b1fe45bc6ab069eab68ad4ac6ae'

def plain(x):
    if dataclasses.is_dataclass(x):
        return {f.name: plain(getattr(x, f.name)) for f in dataclasses.fields(x)}
    if isinstance(x, np.ndarray): return x.tolist()
    if isinstance(x, np.generic): return x.item()
    if isinstance(x, dict): return {str(k): plain(v) for k,v in x.items()}
    if isinstance(x, (list, tuple)): return [plain(v) for v in x]
    return x

def sha(x): return hashlib.sha256(x).hexdigest()
def arrid(x): return dict(shape=list(x.shape), dtype=str(x.dtype), sha256=sha(x.tobytes()))
def save(name,x): (OUT/name).write_text(json.dumps(plain(x), indent=2, allow_nan=True)+'\n')
def emit(f,x): f.write(json.dumps(plain(x), separators=(',',':'), allow_nan=True)+'\n')

def git(*args):
    return subprocess.check_output(['git','-c',f'safe.directory={ROOT}', '-C',str(ROOT),*args])

def identity():
    import resense
    from resense import _native
    from resense.config import DetectorConfig
    import yaml
    assert Path(resense.__file__).resolve() == ROOT/'resense/__init__.py'
    assert os.environ['PYTHONPATH'].split(':')[0] == str(ROOT)
    head=git('rev-parse','HEAD').decode().strip()
    assert head == (SEALED if os.environ['H4_SOURCE']=='sealed' else H3)
    manifest=json.loads((ROOT/'docs/evidence/detector_freeze_2026-09-29_shell_off.json').read_text())
    files={p:sha((ROOT/p).read_bytes()) for p in sorted(manifest['files'])}
    assert len(files)==36
    for p,h in files.items():
        assert sha(git('show',f'{head}:{p}'))==h, p
        assert b'\r\n' not in (ROOT/p).read_bytes(), p
        if head==H3: assert sha(git('show',f'{TARGET}:{p}'))==h, p
    assert _native.enabled(), _native.status()
    cfg=DetectorConfig.from_dict(yaml.safe_load((ROOT/'configs/default.yaml').read_text())['resense'])
    native={str(p):sha(p.read_bytes()) for p in (ROOT/'resense').glob('*.so')}
    assert len(native)==1
    assert list(native.values())==['b5a5c2dc08be8fa1ab00e27dee7662d31413a99f819a760d2d2d4b16b93e8534']
    d=dict(head=head,target=TARGET,import_path=resense.__file__,files=files,
           source_sha256=sha(json.dumps(files,sort_keys=True,separators=(',',':')).encode()),
           native=native,native_status=_native.status(),config=cfg.to_dict(),
           effective_config_sha256=sha(json.dumps(cfg.to_dict(),sort_keys=True,separators=(',',':')).encode()),
           environment={k:os.environ.get(k) for k in ['PYTHONPATH','RESENSE_REPO','OMP_NUM_THREADS',
               'OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','PYTHONHASHSEED']})
    save('identity.json',d)
    return cfg

def cluster_desc(c):
    return {f.name:(arrid(c.points_idx) if f.name=='points_idx' else plain(getattr(c,f.name)))
            for f in dataclasses.fields(c)}

def track_desc(t):
    keys=['id','hits','misses','age','confidence','history','zone_hist','column_hist','spare_hist',
          'hit_hist','thin_hist','near_hist','explained_hist','clean_run','reported','seen_reported',
          'column_held','vote_zone','rule_zone','zone','span_s','approach_block','far_evidence',
          'fresh_blocked','stop_earned','withheld','since_clean','hold']
    return {k:plain(getattr(t,k)) for k in keys if hasattr(t,k)}

def normalize(d):
    import copy,re
    d=copy.deepcopy(d)
    d.pop('timing_ms',None)
    h=d.get('health',{})
    for k in ['latency_p95_ms','latency_basis','latency_sample_age_frames']: h.pop(k,None)
    old=h.get('messages',[])
    h['messages']=[m for m in old if not re.fullmatch(r'latency p95 \d+ ms over the \d+ ms budget',m)]
    if h.get('level')=='warn' and h.get('decision_level')=='ok' and old and not h['messages']:
        h['level']='ok'
    return d
