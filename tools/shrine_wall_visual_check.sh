#!/bin/bash
# Approach -> real lit-barrel throw/blast -> walk through both room-A gaps.
# Owns each render lock; never wrap this script in flock.
set -euo pipefail
cd "$(dirname "$0")/.."
out=${1:-build/round82/doorways}
mkdir -p "$out"
sloppy/bin/sloppy build game/main.jo -o "$out/game"
python3 - "$out" <<'PY'
import json, os, re, subprocess, sys
from pathlib import Path
out=Path(sys.argv[1])
for name,at,script in [
 ('north','0,0,-15.5,0','20:e+,22:e-,40:s+,80:s-,300:w+,450:w-'),
 ('east','5.5,0,-10,1.5707963','20:e+,22:e-,40:s+,80:s-,300:w+,435:w-')]:
 dest=out/name;dest.mkdir(exist_ok=True)
 env={k:v for k,v in os.environ.items() if not k.startswith(('BOTW_','SLOPPY_'))}
 env.update(BOTW_SKIP='1',BOTW_SHRINE='2',BOTW_SHRINE_AT=at,BOTW_SHRINE_CARRY='lit',BOTW_SHRINE_LOG='1',BOTW_CAMDBG='1',BOTW_HOUR='11',BOTW_TIMESCALE='0',BOTW_WEATHER='clear',BOTW_SCALE='1',SLOPPY_PLATFORM='x11',SLOPPY_WINDOW='1280x720',SLOPPY_VSYNC='0',SLOPPY_INPUT=script,SLOPPY_FRAMES='480',BOTW_CAPTURE_DIR=str(dest),BOTW_CAPTURE_EVERY='10',SLOPPY_SCREENSHOT=str(dest/'final.png'))
 with (dest/'run.log').open('w') as log:
  subprocess.run(['flock','/tmp/botw-render.lock','python3','tools/performance_window.py','1280x720','timeout','240',str(out/'game')],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 log=(dest/'run.log').read_text()
 wall='ja_baij_crack_'+('n' if name=='north' else 'e')
 assert 'barrel thrown' in log and f'wall {wall} broken' in log,log[-3000:]
 positions=re.findall(r'^cam .* pl=vec3\(([^)]+)\)',log,re.M)
 assert positions,'missing player trail'
 x,y,z=map(float,positions[-1].split(',')); local=(x+400,y+1,z-2002)
 assert (local[2]<-21.5 if name=='north' else local[0]>11.0),(name,local)
 (dest/'settings.json').write_text(json.dumps({k:v for k,v in env.items() if k.startswith(('BOTW_','SLOPPY_'))},indent=2))
 print(f'PASS {name}: barrel thrown, {wall} blasted, walked through to {local}',flush=True)
PY
