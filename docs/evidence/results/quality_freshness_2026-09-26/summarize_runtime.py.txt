import collections, importlib.util, json, re
from pathlib import Path
v=Path('/home/resense/validation/quality_cycle/freshness')
spec=importlib.util.spec_from_file_location('checker','/home/resense/worktrees/monitoring-quality/scripts/check_dry_run.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
rows=[]
for name in ['original_cold','original_warm','original_clear','original_cold_load','stock_switch_recording1','stock_switch_recording2']:
 path=v/(name+'.jsonl') if name.startswith('stock_switch_recording') else v/name/'status.jsonl'
 if not path.exists(): continue
 frames,_=c.load(path)
 if not frames: continue
 positive=[f for f in frames if c.detected_obstacle(f)]
 valid=[f for f in frames if f['freshness']['valid']]
 f0=frames[0]['stamp']
 log=(v/(name+'.log')).read_text()
 losses=re.search(r'(\d+) of its messages not processed',log)
 item={'name':name,'frames':len(frames),'detector_positive_frames':len(positive),
       'exposed_stop_frames':sum(f['obstacle'] for f in frames),'held_stop_frames':sum(f['stop_held'] for f in frames),
       'valid_frames':len(valid),'invalid_reasons':dict(collections.Counter(f['freshness']['reason'] for f in frames if not f['freshness']['valid'])),
       'first_detector_stop_s':positive[0]['stamp']-f0 if positive else None,
       'latency_p95_ms':c.percentile([f['node']['latency_ms'] for f in frames],95),
       'fps_last':frames[-1]['node']['fps'],'postsettle_recorded_messages_missed':int(losses.group(1)) if losses else None,
       'freshness_violations':c.freshness_failures(frames),'valid_source_age_p95_s':c.percentile([f['freshness']['source_age_s'] for f in valid],95),
       'valid_source_age_max_s':max([f['freshness']['source_age_s'] for f in valid],default=None),
       'valid_residence_age_p95_s':c.percentile([f['freshness']['residence_age_s'] for f in valid],95),
       'exit_code':json.loads((v/(name+'_result.json')).read_text())['exit_code']}
 if not name.startswith('stock'):
  item['scene_resets']=len(re.findall(r'scene state reset',(v/name/'node.log').read_text()))
 rows.append(item)
report={'image_id':json.loads((v/'candidate_image_receipt.json').read_text())['Id'],
        'source_commit':'0145cbb8dd26b3777084aedb3945f49dda741caf','runs':rows,
        'all_registered_per_bag_criteria_pass':len(rows)==6 and all(x['exit_code']==0 for x in rows),
        'release_hold':True}
(v/'combined_runtime_summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
