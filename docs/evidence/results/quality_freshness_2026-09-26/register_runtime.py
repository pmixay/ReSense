import datetime, hashlib, json
from pathlib import Path
root=Path('/home/resense/worktrees/monitoring-quality')
v=Path('/home/resense/validation/quality_cycle/freshness')
p={
 'protocol':'quality_combined_runtime_2026-09-26',
 'registered_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'source_commit':'0145cbb8dd26b3777084aedb3945f49dda741caf', 'image':'resense:quality-candidate',
 'image_identity':'candidate_image_receipt.json recorded after build, before replay',
 'sources':{str(f):hashlib.sha256((root/f).read_bytes()).hexdigest() for f in ['ros2_ws/src/resense_ros/resense_ros/detector_node.py','resense/health.py','resense/detector.py','scripts/dry_run.sh','scripts/check_dry_run.py']},
 'prerequisites':['M2 gate146gated/199total unchanged','M2 stress/raw checks completed; no heavy workers active','native AVAILABLE and enabled in candidate runtime','node and detector source hashes match worktree'],
 'mode':'replay explicitly; publisher UTC, unknown original acquisition age; strict freshness schema required',
 'runs':[
  {'name':'original_cold','bag':'doubleT_obstacle','cold':True,'expect_obstacle':True},
  {'name':'original_warm','bag':'doubleT_obstacle','cold':False,'expect_obstacle':True},
  {'name':'original_clear','bag':'roundT_doubleT','cold':False,'expect_clear':True,'max_alarm_frames':0},
  {'name':'original_cold_load','bag':'doubleT_obstacle','cold':True,'expect_obstacle':True,'workload':'two bounded readers specified below'},
  {'name':'stock_switch','bags':['roundT_doubleT','doubleT_obstacle'],'player':'stock Fast DDS uid1000','transport_smoke_limits':{'p95_ms':1000,'counter_drops':100000},'additional_checks':'split captures by recording; original header inventory per bag with p95<=100ms and zero postsettle messages unprocessed; first stock clear recording retains prior allowance2 exposed alarms, second requires detector-positive obstacle'}
 ],
 'data_root':'/home/resense/data/for_hackathon', 'run_count_per_name':1,
 'retry_policy':'No retry-to-green; preserve failure and validity evidence. Any correction requires a recorded reason and distinct follow-up identifier.',
 'strict_per_bag_limits':{'p95_ms':100,'post_settle_recorded_messages_unprocessed':0,'minimum_frames':50,'minimum_detector_alarm_frames':3,'obstacle_distance_m':[50,62],'settle_s':5,'max_settle_s':15},
 'cold_proof':{'method':'file-local POSIX_FADV_DONTNEED then mincore; cold_cache_proof.py','max_resident_fraction':0.01,'global_cache_drop':False},
 'bounded_workload':{'files':['/home/resense/data/new_data/new_data_0.db3','/home/resense/data/new_data/new_data_1.db3'],'readers':2,'read_only':True,'direct_io':True,'buffer_mib':1,'per_reader_mib_per_s_cap':64,'lead_in_s':3,'max_duration_s':120,'replay_timeout_s':110},
 'report':['image/source hashes','commands and cold proof','checker result and all failures','processed/current/invalid/heldSTOP counts','p95 source/residence ages','first detector STOP offset','latency and message inventory losses','reader coverage and rates'],
 'limitations':['Replay publication freshness does not prove original acquisition age.','Wall clocks must be synchronized.','Single-thread watchdog cannot run while callbacks are blocked; consumers must enforce expiry.','One bounded load does not establish arbitrary overload tolerance.'],
 'release_hold':True
}
with (v/'combined_runtime_protocol.json').open('x') as f:
 json.dump(p,f,indent=2); f.write('\n')
print(hashlib.sha256((v/'combined_runtime_protocol.json').read_bytes()).hexdigest())
