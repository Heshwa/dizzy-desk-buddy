"""Run ngspice with explicit, illustrative load and harness assumptions."""
import subprocess,json,csv
from pathlib import Path
root=Path(__file__).resolve().parent
results=[]
for name,limit in [('five_amp',5),('three_amp',3)]:
 net=f'''Dizzy 5V rail / illustrative regulator and harness model, NOT vendor model
* Source droop 20 milliohm; ideal current limit {limit} A.
Breg 0 source I=min({limit},max(0,(5.1-v(source))/0.02))
Csource source 0 47u
Rlead source wire 0.04
Llead wire bus 1u
Rservo bus servo 0.03
Rcapservo1 servo cservo1 .08
Cservo1 cservo1 0 470u
Rcapservo2 servo cservo2 .08
Cservo2 cservo2 0 470u
Rcapamp bus camp .08
Camp camp 0 470u
Rcapmcu bus cmcu .1
Cmcu cmcu 0 100u
Clocal bus 0 100n
* Main MCU .5A + camera .5A + display/other .15A.
Bbase bus 0 I=1.15*min(1,max(0,v(bus)/4.5))
* Three servo allowance .8A each, ramp then hold; no mechanical motor model.
Vmotion motion 0 PWL(0 0 10m 0 11m 2.4 70m 2.4 71m 0 100m 0)
Bmotors servo 0 I=v(motion)*min(1,max(0,v(servo)/4.5))
Vmusic music 0 PWL(0 0 20m 0 21m .7 60m .7 61m 0 100m 0)
Baudio bus 0 I=v(music)*min(1,max(0,v(bus)/4.5))
.control
set wr_singlescale
set wr_vecnames
tran 10u 100m
wrdata {name}.dat v(bus) v(servo) i(Llead)
quit
.endc
.end
'''
 (root/(name+'.cir')).write_text(net)
 run=subprocess.run(['ngspice','-b',name+'.cir'],cwd=root,text=True,capture_output=True,check=True)
 (root/(name+'.log')).write_text(run.stdout+run.stderr)
 rows=[]
 for line in (root/(name+'.dat')).read_text().splitlines()[1:]:
  vals=list(map(float,line.split()))
  if vals[0]>=.005:rows.append(vals)
 steady=[r for r in rows if .04<=r[0]<=.05]
 result={'case':name,'limit_A':limit,'minimum_bus_V':min(r[1] for r in rows),'minimum_servo_V':min(r[2] for r in rows),'loaded_servo_V':sum(r[2] for r in steady)/len(steady),'peak_lead_A':max(r[3] for r in rows),'assumed_design_load_A':4.25}
 results.append(result)
 with (root/(name+'.csv')).open('w') as f:
  w=csv.writer(f);w.writerow(['seconds','bus_volts','servo_volts','lead_amps']);w.writerows(rows[::10])
assert results[0]['loaded_servo_V']>4.75,results
assert results[1]['loaded_servo_V']<4.5,results
(root/'results.json').write_text(json.dumps(results,indent=2)+'\n')
# Standalone SVG plot: exported, labelled and independent of browser runtime.
colors=['#39dab0','#ffae68'];out=['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="480" viewBox="0 0 1000 480"><rect width="1000" height="480" fill="#111b2b"/><g font-family="Arial" fill="#e9f2ff"><text x="50" y="42" font-size="24">Dizzy · simulated supply voltage under load</text><text x="50" y="69" font-size="14">ngspice • assumed loads and cable resistance • physical supply behaviour unverified</text>']
for v in [3,3.5,4,4.5,5]:
 y=390-(v-2.8)/2.5*280;out.append(f'<path d="M80 {y}H940" stroke="#314158"/><text x="25" y="{y+5}" font-size="14">{v:.1f} V</text>')
for case,color in zip(results,colors):
 data=list(csv.reader((root/(case['case']+'.csv')).open()))[1:];pts=' '.join(f'{80+float(r[0])*8600:.1f},{390-(float(r[2])-2.8)/2.5*280:.1f}' for r in data)
 out.append(f'<polyline points="{pts}" stroke="{color}" fill="none" stroke-width="2.5"/>')
for i,(case,color) in enumerate(zip(results,colors)):
 out.append(f'<text x="{80+i*430}" y="445" font-size="16" fill="{color}">{case["limit_A"]} A supply: loaded servo rail {case["loaded_servo_V"]:.2f} V</text>')
out.append('<text x="80" y="414" font-size="13">0 ms</text><text x="880" y="414" font-size="13">100 ms</text></g></svg>');(root/'power-results.svg').write_text(''.join(out))
print(json.dumps(results,indent=2))
