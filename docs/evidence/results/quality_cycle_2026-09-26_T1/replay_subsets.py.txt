"""Observe exact recorded header subsets; no detector/config edits or candidate rule."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
from datetime import datetime,timezone

p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
a=p.parse_args();sys.path.insert(0,str(a.repo));sys.path.insert(1,'/home/resense/ReSense/scripts')
import numpy as np
from rosbags.rosbag2 import Reader
from rosbags.typesys import Stores,get_typestore
from resense.config import DetectorConfig
from resense.frame import Frame,axis_matrix
from resense.pointcloud import pointcloud2_to_arrays
from resense.gauge import corridor_coordinates
from trace_detector_stages import TraceDetector
from check_dry_run import cdr_stamp
import resense.detector,resense._native

T=946692947.533395
ROOT=Path('/home/resense/validation')
SOURCES={'failed_clear':ROOT/'quality_cycle/freshness/original_clear/status.jsonl',
 'old_stock':ROOT/'console_stock/roundT_doubleT.jsonl','old_pass':ROOT/'dry_clear/status.jsonl'}

def read(path):
 rows=[]
 for line in path.read_text().splitlines():
  try:r=json.loads(line)
  except json.JSONDecodeError:continue
  if 'frames' in r.get('node',{}) and r.get('snapshot_kind','frame')=='frame':rows.append(r)
 return rows

def key(stamp):return round(stamp*1e6)

def track_record(t):
 c=t.last
 return {'id':t.id,'reported':t.reported,'zone':t.zone,'vote_zone':t.vote_zone,'hits':t.hits,'misses':t.misses,
  'age':t.age,'zone_hist':t.zone_hist.copy(),'column_hist':t.column_hist.copy(),'near_hist':t.near_hist.copy(),
  'hit_hist':t.hit_hist.copy(),'column_held':t.column_held,'near_escalated':t.near_escalated,'kept':t.kept,
  'cluster':None if c is None else {'n_raw':int(c.n_raw),'n_vox':int(c.n),'n_gauge':int(c.n_gauge),'zone':c.zone,
  'reason':c.reason,'thin':c.thin,'centroid':c.centroid.tolist(),'bbox_min':c.bbox_min.tolist(),'bbox_max':c.bbox_max.tolist(),
  'distance':float(c.distance),'lateral':float(c.lateral),'height_min':float(c.height_min),'height_max':float(c.height_max)}}

cfg=DetectorConfig.from_yaml(str(a.repo/'configs/default.yaml'))
state={name:{'reference':{key(r['stamp']):r for r in read(path)},'detector':TraceDetector(cfg),'rows':[],'trace':[],'mismatches':[]} for name,path in SOURCES.items()}
for s in state.values():assert len(s['reference'])==len(set(s['reference']))
a.out.mkdir(parents=True,exist_ok=True);(a.out/'points').mkdir(exist_ok=True)
typestore=get_typestore(Stores.ROS2_HUMBLE)
raw_receipt=[]
with Reader(Path('/home/resense/data/for_hackathon/roundT_doubleT')) as reader:
 conns=[c for c in reader.connections if c.msgtype=='sensor_msgs/msg/PointCloud2']
 for index,(conn,receive,raw) in enumerate(reader.messages(connections=conns)):
  stamp=cdr_stamp(raw[:12]);k=key(stamp)
  names=[name for name,s in state.items() if k in s['reference']]
  raw_receipt.append({'raw_index':index,'header_stamp':stamp,'receive_stamp_ns':receive,'processed_by':names,'cdr_sha256':hashlib.sha256(raw).hexdigest()})
  if not names:continue
  msg=typestore.deserialize_cdr(raw,conn.msgtype)
  xyz,intensity,ring,nraw,nnear=pointcloud2_to_arrays(msg,cfg.sensor.min_range,cfg.sensor.max_range)
  xyz=xyz @ axis_matrix(cfg.sensor).T.astype(np.float32)
  frame=Frame(xyz=xyz,intensity=intensity,ring=ring,stamp=stamp,frame_id=msg.header.frame_id,meta={'n_raw':nraw,'n_near':nnear})
  active=abs(stamp-T)<2.0
  x=54.94+17.5*(T-stamp)
  region=np.flatnonzero((np.abs(xyz[:,0]-x)<6)&(xyz[:,1]>-12)&(xyz[:,1]<2)&(xyz[:,2]>-3)&(xyz[:,2]<7)) if active else np.empty(0,dtype=int)
  for name in names:
   s=state[name];det=s['detector'];ref=s['reference'][k]
   result=det.process_target(frame,region);row=result.to_dict();row['stamp']=stamp;row['raw_index']=index
   s['rows'].append(row)
   fields=['detections','warnings','n_candidates','n_points','n_corridor']
   # Invalid output policy may suppress displayed detector fields; compare valid snapshots.
   if ref.get('freshness',{}).get('valid',True):
    changed={field:{'reference':ref.get(field),'replay':row.get(field)} for field in fields if ref.get(field)!=row.get(field)}
    if changed:s['mismatches'].append({'raw_index':index,'stamp':stamp,'fields':changed})
   if active:
    target_id=45 if name=='old_stock' else 40
    targets=[t for t in det.tracker.tracks if t.id==target_id]
    record={'raw_index':index,'stamp':stamp,'output':row,'tracks':[track_record(t) for t in targets],'stages':det.trace}
    if targets and targets[0].last is not None and targets[0].misses==0 and abs(stamp-T)<.151:
     track=targets[0];center=track.centroid;processed=result.xyz
     dy,h=corridor_coordinates(processed,result.track)
     ids=np.flatnonzero((np.abs(processed[:,0]-center[0])<12)&(np.abs(processed[:,1]-center[1])<5)&(processed[:,2]>-4)&(processed[:,2]<9))
     filename=f'{name}_{index:03d}.npz'
     np.savez_compressed(a.out/'points'/filename,xyz=processed[ids],dy=dy[ids],h=h[ids],target=np.isin(ids,track.last.points_idx),intensity=intensity[ids],indices=ids)
     record['point_snapshot']=filename
    s['trace'].append(record)
  if index%50==0:print('raw frame',index,flush=True)
report={'created_utc':datetime.now(timezone.utc).isoformat(),'detector_module':resense.detector.__file__,'native_library':resense._native.LIBRARY,
 'detector_sha256':hashlib.sha256(Path(resense.detector.__file__).read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 'raw_receipt':raw_receipt,'subsets':{}}
for name,s in state.items():
 assert len(s['rows'])==len(s['reference']),(name,len(s['rows']),len(s['reference']))
 with gzip.open(a.out/f'{name}_outputs.jsonl.gz','wt') as f:
  f.write(''.join(json.dumps(r)+'\n' for r in s['rows']))
 report['subsets'][name]={'capture':str(SOURCES[name]),'capture_sha256':hashlib.sha256(SOURCES[name].read_bytes()).hexdigest(),
  'frames':len(s['rows']),'alarm_frames':sum(r['obstacle'] for r in s['rows']),'mismatches':s['mismatches'],'trace':s['trace']}
 print(name,len(s['rows']),'alarms',sum(r['obstacle'] for r in s['rows']),'mismatches',len(s['mismatches']),flush=True)
with gzip.open(a.out/'report.json.gz','wt') as f:json.dump(report,f)
