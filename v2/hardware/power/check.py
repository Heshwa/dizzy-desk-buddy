"""Run stated load cases. No converter loop, thermal or BMS behavior is inferred."""
from pathlib import Path
import json
import re
import subprocess
import tempfile

ROOT=Path(__file__).parent
template=(ROOT/'battery.cir').read_text()
CASES=[('fresh',8.4,.06,5),('nominal',7.4,.09,5),('low charge',7.0,.11,5),
       ('aged pack',7.0,.25,5),('undercharged pack',6.7,.13,5)]
report=[]
with tempfile.TemporaryDirectory() as folder:
    for name,voltage,source,cap in CASES:
        content=template.replace('.param P=7.4 RPACK=.09 RMOTOR=.030 RLOGIC=.045 LIM=5',
            f'.param P={voltage} RPACK={source} RMOTOR=.030 RLOGIC=.045 LIM={cap}')
        path=Path(folder)/'power.cir';path.write_text(content)
        run=subprocess.run(['ngspice','-b',str(path)],capture_output=True,text=True,check=True)
        data={key:float(value) for key,value in re.findall(
            r'^(board_min|motor_min|battery_min|input_max|after_cut)\s*=\s*([\d.e+-]+)',run.stdout,re.M)}
        assert len(data)==5,run.stdout
        data['input_max']=abs(data['input_max'])
        voltage_ok=data['board_min']>=4.75 and data['motor_min']>=4.75
        expected=name in ('fresh','nominal','low charge')
        report.append({'case':name,'test':('PASS' if voltage_ok==expected and data['after_cut']<.02 else 'FAIL'),
            'rails_in_bounds':voltage_ok,**data})
print(json.dumps(report,indent=2))
