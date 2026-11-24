"""Sensitivity checks using the existing illustrative ngspice network."""
import json,subprocess
from pathlib import Path
root=Path(__file__).resolve().parent
out=root/'margins';out.mkdir(exist_ok=True)
baseline=(root/'five_amp.cir').read_text()
cases=[('baseline',.04,2.4,5.1),('double_cable_resistance',.08,2.4,5.1),('three_times_cable_resistance',.12,2.4,5.1),('higher_servo_allowance',.04,3.6,5.1),('five_volt_source',.04,2.4,5.0)]
results=[]
for name,resistance,motors,volts in cases:
 text=baseline.replace('Rlead source wire 0.04',f'Rlead source wire {resistance}').replace('(5.1-v(source))',f'({volts}-v(source))').replace('11m 2.4 70m 2.4',f'11m {motors} 70m {motors}').replace('five_amp.dat',f'{name}.dat')
 (out/(name+'.cir')).write_text(text)
 run=subprocess.run(['ngspice','-b',name+'.cir'],cwd=out,text=True,capture_output=True,check=True)
 (out/(name+'.log')).write_text(run.stdout+run.stderr)
 data=[list(map(float,line.split())) for line in (out/(name+'.dat')).read_text().splitlines()[1:]]
 loaded=[r for r in data if .04<=r[0]<=.05]
 v=sum(r[2] for r in loaded)/len(loaded)
 results.append(dict(case=name,source_V=volts,cable_path_ohms=resistance,servo_allowance_A=motors,requested_load_A=1.85+motors,loaded_servo_V=round(v,4),meets_planning_target_4_75V=v>=4.75))
assert results[0]['meets_planning_target_4_75V']
assert all(not r['meets_planning_target_4_75V'] for r in results[1:])
(out/'results.json').write_text(json.dumps({'model_only':True,'planning_target_V':4.75,'cases':results},indent=2)+'\n')
print(json.dumps(results,indent=2))
