"""Run independent Webots check cases and report their measured outputs."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parent
cmd=os.getenv('DIZZY_WEBOTS','/Applications/Webots.app/Contents/MacOS/webots')
world=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT/'worlds/dizzy_v2.wbt'
output={}
with tempfile.TemporaryDirectory(prefix='dizzy-gait-') as folder:
    for mode in ('shuffle','sway','heel','bounce','limits'):
        path=Path(folder)/f'{mode}.json'
        env={**os.environ,'DIZZY_V2_WEBOTS_TEST':mode,'DIZZY_V2_WEBOTS_OUT':str(path)}
        result=subprocess.run([cmd,'--batch','--mode=fast','--no-rendering',str(world)],
            env=env,capture_output=True,text=True,timeout=100)
        if not path.exists():
            raise RuntimeError(result.stderr[-1500:]+'\n'+result.stdout[-1500:])
        trial=json.loads(path.read_text())
        trial.pop('samples',None)
        peaks=trial['observed_peak_joint_deg']
        low,high=trial['observed_min_joint_deg'],trial['observed_max_joint_deg']
        if mode=='shuffle':
            reached=trial['forward']>=.30 and peaks[4]>=5
        elif mode=='limits':
            reached=low[0]<=-43 and high[0]>=43 and low[1]<=-18 and high[1]>=23 and min(peaks[2:4])>=65 and low[0]>=-45.8 and high[0]<=45.8 and low[1]>=-20.8 and high[1]<=25.8
        else:
            reached=peaks[2]>=8 and peaks[6]>=3
        trial['pass']=not trial['fell'] and reached
        output[mode]=trial
print(json.dumps(output,indent=2))
