"""Run each registered combined-candidate original-bag check once; retain every result."""
import datetime, hashlib, importlib.util, json, multiprocessing, os, subprocess, time
from pathlib import Path
ROOT=Path('/home/resense/worktrees/monitoring-quality')
VALID=Path('/home/resense/validation/quality_cycle/freshness')
PROTOCOL=VALID/'combined_runtime_protocol.json'
DATA=Path('/home/resense/data/for_hackathon')
IMAGE='resense:quality-candidate'
spec=importlib.util.spec_from_file_location('bounded_reader', '/home/resense/validation/run_cold_load_final.py')
reader_module=importlib.util.module_from_spec(spec); spec.loader.exec_module(reader_module)

def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def dump(path,data): path.write_text(json.dumps(data,indent=2)+'\n')
def execute(name,command,env,timeout=120):
    started={'name':name,'started_utc':utc(),'command':command,'cwd':str(ROOT),
             'env':{k:env[k] for k in ('IMAGE','SKIP_BUILD','OFFLINE','OUT','PLAYER_DDS','DOCKER_ARGS') if k in env}}
    with (VALID/(name+'_started.json')).open('x') as f: json.dump(started,f,indent=2)
    with (VALID/(name+'.log')).open('w') as out:
        try: rc=subprocess.run(command,cwd=ROOT,env=env,stdout=out,stderr=subprocess.STDOUT,timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            rc='timeout'
            if env.get('DOCKER_ARGS', '').startswith('--name '):
                subprocess.run(['docker','stop','--time','5',env['DOCKER_ARGS'].split()[1]],stdout=out,stderr=subprocess.STDOUT,timeout=15)
    result={**started,'finished_utc':utc(),'exit_code':rc}
    dump(VALID/(name+'_result.json'),result)
    print(json.dumps({'name':name,'exit_code':rc,'finished_utc':result['finished_utc']}),flush=True)
    return result

def cold(name):
    with (VALID/(name+'_cache_before.json')).open('w') as out:
        rc=subprocess.run(['python3',str(VALID/'cold_cache_proof.py')],stdout=out,stderr=subprocess.STDOUT,timeout=15).returncode
    if rc: raise RuntimeError('Cold-cache proof failed for '+name)
    proof=json.loads((VALID/(name+'_cache_before.json')).read_text())
    if not proof or not all(p['bytes']>0 and p['resident_fraction']<=.01 for p in proof):
        raise RuntimeError('Cold-cache proof inventory missing/invalid for '+name)

def dry(name,bag,clear=False):
    env=os.environ.copy();env.update(IMAGE=IMAGE,SKIP_BUILD='1',OFFLINE='1',OUT=str(VALID/name),DOCKER_ARGS='--name resense_quality_'+name)
    args=['--expect-clear'] if clear else ['--expect-obstacle','--distance','50:62']
    return execute(name,[str(ROOT/'scripts/dry_run.sh'),str(DATA/bag),*args,'--max-p95-latency','100','--max-dropped','0'],env)

def load_trial(protocol):
    name='original_cold_load'; stop=multiprocessing.Event(); workers=[]
    report={'started_utc':utc(),'valid':False,'failure':None}
    try:
        for i,path in enumerate(protocol['bounded_workload']['files']):
            ready=multiprocessing.Event()
            worker=multiprocessing.Process(target=reader_module.reader,args=(path,str(VALID/f'{name}_reader{i}.json'),stop,ready))
            worker.start();workers.append((worker,ready))
        if not all(ready.wait(10) for _,ready in workers): raise RuntimeError('Reader failed to establish direct I/O')
        time.sleep(3)
        cold(name)
        result=dry(name,'doubleT_obstacle')
        report['covered_capture']=all(w.is_alive() for w,_ in workers)
        report['dry_run_exit_code']=result['exit_code']
    except Exception as e: report['failure']=repr(e)
    finally:
        stop.set()
        for w,_ in workers:
            w.join(10)
            if w.is_alive(): w.terminate();w.join()
        reports=[json.loads((VALID/f'{name}_reader{i}.json').read_text()) for i in range(len(workers))]
        report.update(readers=reports,finished_utc=utc())
        report['valid']=report['failure'] is None and report.get('covered_capture',False) and all(not r['error'] for r in reports)
        dump(VALID/(name+'_workload_result.json'),report)
        print(json.dumps({'name':name,'workload_valid':report['valid']}),flush=True)

def stock():
    env=os.environ.copy();env.update(IMAGE=IMAGE,PLAYER_DDS='stock',OUT=str(VALID/'stock_switch'))
    execute('stock_switch',[str(ROOT/'scripts/console_test.sh'),str(DATA/'roundT_doubleT'),str(DATA/'doubleT_obstacle'),'--','--expect-obstacle','--obstacle-in','2','--expect-inputs','2','--min-frames','20','--max-p95-latency','1000','--max-dropped','100000'],env,180)
    spec=importlib.util.spec_from_file_location('check_dry_run',ROOT/'scripts/check_dry_run.py')
    checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
    frames,_=checker.load(VALID/'stock_switch/status.jsonl')
    for index,bag in enumerate(['roundT_doubleT','doubleT_obstacle'],1):
        rows=[f for f in frames if f.get('node',{}).get('recording')==index]
        path=VALID/f'stock_switch_recording{index}.jsonl';path.write_text(''.join(json.dumps(x)+'\n' for x in rows))
        flags=['--expect-clear','--max-alarm-frames','2'] if index==1 else ['--expect-obstacle','--distance','50:62']
        execute(f'stock_switch_recording{index}', ['python3',str(ROOT/'scripts/check_dry_run.py'),str(path),'--require-freshness','--bag',str(DATA/bag),*flags,'--max-p95-latency','100','--max-dropped','0'],os.environ.copy(),30)

def main():
    protocol=json.loads(PROTOCOL.read_text())
    with (VALID/'combined_runtime_started.json').open('x') as f:
        json.dump({'started_utc':utc(),'protocol_sha256':hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
                   'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   'reader_sha256':hashlib.sha256(Path('/home/resense/validation/run_cold_load_final.py').read_bytes()).hexdigest()},f,indent=2)
    cold('original_cold');dry('original_cold','doubleT_obstacle')
    dry('original_warm','doubleT_obstacle')
    dry('original_clear','roundT_doubleT',True)
    load_trial(protocol)
    stock()
    dump(VALID/'combined_runtime_finished.json',{'finished_utc':utc()})
if __name__=='__main__': main()
