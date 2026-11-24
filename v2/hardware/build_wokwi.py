"""Generate board-labelled Wokwi harness and reuse the V1 PCA/RTC functional models."""
from pathlib import Path
import json
import shutil

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'wokwi'
SHARED=ROOT.parents[1]/'electronics/wokwi'
source=(SHARED/'pca9685.chip.c').read_text().replace('[3]', '[8]').replace('i<3','i<8')
source=source.replace('"PWM0","PWM1","PWM2"',','.join(f'"PWM{i}"' for i in range(8)))
(OUT/'pca9685.chip.c').write_text(source)
pca=json.loads((SHARED/'pca9685.chip.json').read_text())
pca['pins']=pca['pins'][:6]+[f'PWM{i}' for i in range(8)]
(OUT/'pca9685.chip.json').write_text(json.dumps(pca,indent=2))
for ext in ('.c','.json'):
    shutil.copyfile(SHARED/f'ds3231.chip{ext}',OUT/f'ds3231.chip{ext}')
body_pins=['VCC','GND','SDA','SCL','TALK','CROWN_L','CROWN_R','ARM','STOP','LOW_BAT','TILT']
(OUT/'body.chip.json').write_text(json.dumps({'name':'Dizzy body I²C sensor surrogate','author':'Dizzy V2','pins':body_pins},indent=2))
parts=[
    {'type':'board-esp32-s3-devkitc-1','id':'s3','top':-96,'left':-180,'attrs':{}},
    {'type':'chip-pca9685','id':'pwm','top':-86,'left':110,'attrs':{}},
    {'type':'chip-ds3231','id':'rtc','top':190,'left':-155,'attrs':{}},
    {'type':'chip-body','id':'body','top':175,'left':85,'attrs':{}},
    {'type':'wokwi-logic-analyzer','id':'logic','top':-212,'left':-18,'attrs':{}}]
connections=[]
def route(a,b,c):connections.append([a,b,c,[]])
for part in ('pwm','body','rtc'):
    route('s3:17',part+':SDA','green')
    route('s3:18',part+':SCL','blue')
    route('s3:3V3',part+':VCC','red')
    route('s3:GND.1',part+':GND','black')
route('s3:16','pwm:OE','orange')
route('s3:5V','pwm:VPLUS','red')
route('s3:GND.1','logic:GND','black')
route('s3:16','logic:D0','orange')
for i,label in enumerate(('Yaw','Pitch','Left arm','Right arm','Left hip','Right hip','Left ankle','Right ankle')):
    name='servo'+str(i)
    parts.append({'type':'wokwi-servo','id':name,'top':-167+67*i,'left':320,'attrs':{'label':label}})
    route(name+':PWM',f'pwm:PWM{i}','orange')
    route(name+':V+','s3:5V','red')
    route(name+':GND','s3:GND.1','black')
for i,pin in enumerate(body_pins[4:]):
    name=f'button{i}'
    parts.append({'type':'wokwi-pushbutton','id':name,'top':300+(i//5)*60,'left':-190+(i%5)*68,
                  'attrs':{'color':'red' if pin in ('STOP','LOW_BAT','TILT') else 'blue','label':pin,'key':str(i+1)}})
    route(f'body:{pin}',name+':1.l','purple')
    route(name+':2.l','s3:GND.1','black')
route('pwm:PWM0','logic:D1','orange')
route('pwm:PWM4','logic:D2','orange')
route('s3:17','logic:D3','green')
(OUT/'diagram.json').write_text(json.dumps({'version':1,'author':'Dizzy V2','editor':'wokwi','parts':parts,'connections':connections},indent=2))
