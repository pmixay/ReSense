#!/usr/bin/env python3
"""Actual software RViz expiration evidence; run under xvfb-run, no image alteration."""
import json
import os
from pathlib import Path
import subprocess
import time

import numpy as np
from PIL import ImageGrab

root=Path(__file__).resolve().parents[3]
out=Path('/home/resense/data/n1_marker_expiry')
out.mkdir(parents=True,exist_ok=True)
(out/'phase.json').unlink(missing_ok=True)
command=['docker','run','--rm','--name','resense_marker_expiry','--net=host','--ipc=host',
         '-e','DISPLAY='+os.environ['DISPLAY'],'-e','LIBGL_ALWAYS_SOFTWARE=1','-e','QT_X11_NO_MITSHM=1',
         '-v','/tmp/.X11-unix:/tmp/.X11-unix:rw','-v',str(out)+':/out',
         '-v',str(root/'docs/evidence/n1_n4_2026-10-18/marker_lifetime_probe.py')+':/probe.py:ro']
if os.environ.get('XAUTHORITY'):
    command += ['-e','XAUTHORITY=/tmp/probe.xauth','-v',os.environ['XAUTHORITY']+':/tmp/probe.xauth:ro']
command += ['resense:n1n4-check','python3','/probe.py']
with (out/'container.log').open('w') as log:
    process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
    captures={}
    start=time.monotonic()
    while process.poll() is None and time.monotonic()-start<45:
        time.sleep(.1)
        try:
            phase=json.loads((out/'phase.json').read_text())
        except (FileNotFoundError,json.JSONDecodeError):
            continue
        key=phase['phase']
        age=time.time()-phase['wall']
        if key in ('publishing','silent_no_delete') and age>1.5 and key not in captures:
            screenshot=ImageGrab.grab(xdisplay=os.environ['DISPLAY'])
            screenshot.save(out/(key+'.png'))
            pixels=np.asarray(screenshot)[:,450:,:3]
            green=(pixels[:,:,1]>110)&(pixels[:,:,0]<90)&(pixels[:,:,2]<120)
            captures[key]={'green_pixels':int(green.sum()),'phase_age_s':age}
    if process.poll() is None:
        process.terminate()
    code=process.wait(timeout=15)
report={'scope':'actual node gauge_markers ROS messages and RViz/Xvfb software renderer; publisher stays alive but sends no DELETE',
        'image':subprocess.check_output(['docker','inspect','resense:n1n4-check','--format','{{.Id}}'],text=True).strip(),
        'exit_code':code,'captures':captures}
report['passed']=code==0 and captures.get('publishing',{}).get('green_pixels',0)>50 and captures.get('silent_no_delete',{}).get('green_pixels',1000)<10
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
raise SystemExit(0 if report['passed'] else 1)
