"""Direct NumPy field views of original CDR, independent of the native cloud decoder."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
DATA=Path('/tmp/opencode/resense-b4-data')
sys.path.insert(0,str(ROOT/'ros2_ws/src/resense_ros'))
from resense_ros import fastcloud  # noqa: E402
sys.path.insert(0,str(ROOT/'scripts'))
from p4_linux_intake import windows_npz_bytes  # noqa: E402

types={1:'i1',2:'u1',3:'i2',4:'u2',5:'i4',6:'u4',7:'f4',8:'f8'}
result={}
for bag in ['doubleT_obstacle','squareT_platform_squareT_switch','roundT_squareT_pressureGate_squareT','cloud_with_fake_obj']:
    cache=DATA/'decoded'/bag
    meta=json.loads((cache/'meta.json').read_text())
    raw_dir=DATA/bag if bag=='cloud_with_fake_obj' else DATA/'for_hackathon'/bag
    dbs=sorted(raw_dir.glob('*.db3'))
    assert dbs
    stamps=[]
    samples={0,len(meta)//2,len(meta)-1}
    if bag=='cloud_with_fake_obj':
        samples|={332,777,778,786}
    checks=[]
    for db in dbs:
        con=sqlite3.connect(f'file:{db}?mode=ro',uri=True)
        topic=con.execute('SELECT id FROM topics WHERE name=?',[meta[0]['topic']]).fetchone()[0]
        ss=[r[0] for r in con.execute('SELECT timestamp FROM messages WHERE topic_id=? ORDER BY timestamp',[topic])]
        offset=len(stamps)
        stamps.extend(ss)
        for i in sorted(samples):
            if not offset<=i<offset+len(ss):
                continue
            message_id=con.execute('SELECT id FROM messages WHERE topic_id=? ORDER BY timestamp LIMIT 1 OFFSET ?',
                                   [topic,i-offset]).fetchone()[0]
            raw=con.execute('SELECT data FROM messages WHERE id=?',[message_id]).fetchone()[0]
            msg=fastcloud.parse_pointcloud2(raw)
            ff={f.name:f for f in msg.fields}
            names=['x','y','z']+[n for n in ['intensity','ring'] if n in ff]
            endian='>' if msg.is_bigendian else '<'
            dtype=np.dtype(dict(names=names,formats=[endian+types[ff[n].datatype] for n in names],
                                offsets=[ff[n].offset for n in names],itemsize=msg.point_step))
            points=np.ndarray((msg.height,msg.width),dtype=dtype,buffer=msg.data,
                              strides=(msg.row_step,msg.point_step)).reshape(-1)
            xyz=np.column_stack([points[n] for n in ['x','y','z']])
            # Compare squared ranges in float32, as the input contract specifies;
            # sqrt can round a just-outside return back onto a boundary.
            r2=xyz[:,0]**2
            r2+=xyz[:,1]*xyz[:,1]
            r2+=xyz[:,2]*xyz[:,2]
            good=np.isfinite(r2)&(r2>=2.5**2)&(r2<=250.**2)
            arrays=dict(xyz=xyz[good].astype(np.float32),
                        inten=(points['intensity'][good].astype(np.float32) if 'intensity' in ff
                               else np.zeros(int(good.sum()),np.float32)),
                        ring=(points['ring'][good].astype(np.uint16) if 'ring' in ff
                              else np.zeros(int(good.sum()),np.uint16)))
            with np.load(cache/f'f_{i:05d}.npz') as saved:
                assert all(np.array_equal(v,saved[k]) for k,v in arrays.items()),(
                    bag,i,{k:(v.shape,saved[k].shape,np.array_equal(v,saved[k])) for k,v in arrays.items()})
            baseline_hash=hashlib.sha256(windows_npz_bytes(arrays)).hexdigest()
            changed={k:v.copy() for k,v in arrays.items()}
            changed['xyz'][0,0]+=1.
            assert hashlib.sha256(windows_npz_bytes(changed)).hexdigest()!=baseline_hash
            checks.append(dict(frame=i,points=len(arrays['xyz']),xyz_intensity_ring_exact=True,
                               has_ring='ring' in ff,
                               cdr_sha256=hashlib.sha256(raw).hexdigest(),mutation_positive_control=True))
        con.close()
    assert len(stamps)==len(meta)
    assert all(m['bag_t']==stamp/1e9 for m,stamp in zip(meta,stamps))
    result[bag]=dict(raw_messages=len(stamps),all_receive_stamps_exact=True,samples=checks)
    print(bag,len(stamps),'metadata rows,',len(checks),'direct field-view matches',flush=True)
(HERE/'raw-input-check.json').write_text(json.dumps(result,indent=2)+'\n')
print({b:{'frames':v['raw_messages'],'manual_decode_samples':len(v['samples'])} for b,v in result.items()})
