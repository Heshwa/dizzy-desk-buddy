"""Generate simulator wiring and a readable pin-to-pin connection list."""
import json,csv
from pathlib import Path
root=Path(__file__).parent
parts=[];connections=[]
def part(id,type,x,y,**attrs):
 parts.append(dict(id=id,type=type,left=x,top=y,attrs=attrs))
def wire(a,b,color='green'):
 connections.append([a,b,color,[]])
def text(id,x,y,value):part(id,'wokwi-text',x,y,text=value)
part('esp','board-esp32-devkit-c-v4',0,80)
part('pd','chip-husb238',-330,80,currentAmps='5')
part('rtc','chip-ds3231',-330,260)
part('pwm','chip-pca9685',350,90)
part('lcd','chip-gc9a01',370,-230)
part('amp','chip-max98357',-330,450)
part('mic','chip-inmp441',-330,620)
part('cam','chip-esp32cam',350,430)
for id,x,name in [('neck',660,'Neck'),('left',810,'Left hand'),('right',960,'Right hand')]:
 part(id,'wokwi-servo',x,100)
 text(id+'label',x,75,name)
for id,x,pin,name in [('talk',-220,34,'Talk'),('down',-80,35,'Vol −'),('up',60,39,'Vol +'),('petL',200,13,'Crown L*'),('petR',340,14,'Crown R*')]:
 part(id,'wokwi-pushbutton',x,820,color='blue',label=name,key={'talk':'T','down':'J','up':'K','petL':'P','petR':'O'}[id])
 part(id+'pull','wokwi-resistor',x,740,value='10000')
 wire('esp:3V3',id+'pull:1','red');wire(id+'pull:2',id+':1.l');wire('esp:'+('VN' if pin==39 else str(pin)),id+':1.l');wire(id+':2.l','esp:GND.1','black')
for id,x,pin in [('sdaPull',-140,21),('sclPull',-70,22),('oePull',230,16)]:
 part(id,'wokwi-resistor',x,-90,value='10000' if id=='oePull' else '4700')
 wire('esp:3V3',id+':1','red');wire(id+':2','esp:'+str(pin))
wire('pd:V+','esp:5V','red');wire('pd:GND','esp:GND.1','black')
for id in ['rtc','pwm','lcd']:
 wire('esp:3V3',id+':VCC','red');wire('esp:GND.1',id+':GND','black')
for id in ['rtc','pwm','pd']:
 wire('esp:21',id+':SDA','green');wire('esp:22',id+':SCL','blue')
for pin,n in [('SCK',18),('SDA',23),('CS',19),('DC',27),('RST',4)]:wire('esp:'+str(n),'lcd:'+pin,'orange')
wire('esp:16','pwm:OE','purple');wire('pd:V+','pwm:VPLUS','red')
for i,id in enumerate(['neck','left','right']):
 wire('pwm:PWM'+str(i),id+':PWM','orange');wire('pd:V+',id+':V+','red');wire('esp:GND.1',id+':GND','black')
for id,powerpin in [('amp','VIN'),('cam','5V')]:
 wire('pd:V+',id+':'+powerpin,'red');wire('esp:GND.1',id+':GND','black')
wire('esp:3V3','mic:VDD','red');wire('esp:GND.1','mic:GND','black');wire('esp:GND.1','mic:L/R','black')
for gpio,a,b in [(26,'amp:BCLK','mic:SCK'),(25,'amp:LRC','mic:WS')]:
 wire('esp:'+str(gpio),a);wire('esp:'+str(gpio),b)
wire('esp:32','amp:DIN');wire('mic:SD','esp:33');wire('pd:V+','amp:SD','red')
part('speaker','chip-speaker',-580,480);wire('amp:SPK+','speaker:PLUS');wire('amp:SPK-','speaker:MINUS')
part('cameraLED','wokwi-led',540,450,color='green');part('ledR','wokwi-resistor',490,540,value='330')
wire('esp:17','ledR:1');wire('ledR:2','cameraLED:A');wire('cameraLED:C','esp:GND.1','black')
part('logic','wokwi-logic-analyzer',700,460)
for i,pin in enumerate(['pwm:PWM0','pwm:PWM1','pwm:PWM2','pwm:OE','esp:21','esp:22','esp:34','esp:17']):wire(pin,'logic:D'+str(i),'gray')
wire('esp:GND.1','logic:GND','black')
wire('esp:TX','$serialMonitor:RX','');wire('esp:RX','$serialMonitor:TX','')
text('title',-370,-300,'DIZZY • ELECTRONICS BRING-UP / functional models')
text('audioNote',-540,400,'Audio + camera: wiring only / no capture or sound')
text('ampLabel',-330,425,'SPEAKER AMPLIFIER / MAX98357A')
text('speakerLabel',-620,550,'SPEAKER: 4 ohm / 3 W\nWiring symbol only; no audio output')
text('micLabel',-330,690,'MICROPHONE / INMP441\nI2S pins connected; no audio capture')
text('camLabel',350,575,'CAMERA / ESP32-CAM + OV2640\nSeparate Wi-Fi node; power only here\nGreen LED is only an activity indicator')
text('touchNote',-250,940,'* Digital stand-ins for touch electrodes. External 10k pull-ups.\nRed = supply, black = common ground. Not a breadboard assembly guide.')
text('powerNote',-550,-50,'USB-C: ideal 5V rail; slider changes reported contract.\n5A required for motors. Real PD/voltage/current tested separately.')
text('i2cNote',-460,200,'I²C: 0x08 PD / 0x68 clock / 0x40 PWM\nOne effective pair of 4.7k pull-ups to 3.3V')
doc=dict(version=1,author='Dizzy project',editor='wokwi',parts=parts,connections=connections,dependencies={})
(root/'wokwi/diagram.json').write_text(json.dumps(doc,indent=2)+'\n')
with (root/'connections.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['from','to','colour']);w.writerows(c[:3] for c in connections if not c[0].startswith('$'))
print(f'{len(parts)} parts, {len(connections)} connections generated')
