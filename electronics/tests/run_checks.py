from pathlib import Path
import json,subprocess,tempfile
root=Path(__file__).resolve().parents[1];w=root/'wokwi';checks=[]
for name,kind,addr in [('ds3231',1,104),('pca9685',2,64),('husb238',3,8)]:
 with tempfile.TemporaryDirectory() as temp:
  exe=str(Path(temp)/name)
  subprocess.run(['clang','-std=c11',f'-DCHIP_KIND={kind}',f'-DCHIP_ADDRESS={addr}','-I'+str(root/'tests'),str(root/'tests/register_models.c'),'-o',exe],check=True,capture_output=True,text=True)
  result=subprocess.run([exe],check=True,capture_output=True,text=True);checks.append(result.stdout.strip())
with tempfile.TemporaryDirectory() as temp:
 exe=str(Path(temp)/'display')
 subprocess.run(['clang','-std=c11','-I'+str(root/'tests'),str(root/'tests/display_model.c'),'-o',exe],check=True,capture_output=True,text=True)
 checks.append(subprocess.run([exe],check=True,capture_output=True,text=True).stdout.strip())
with tempfile.TemporaryDirectory() as temp:
 exe=str(Path(temp)/'firmware')
 subprocess.run(['clang++','-std=c++17','-I'+str(root/'tests/firmware_api'),str(root/'tests/firmware_behaviour.cpp'),'-o',exe],check=True,capture_output=True,text=True)
 checks.append(subprocess.run([exe],check=True,capture_output=True,text=True).stdout.strip())
diagram=json.loads((w/'diagram.json').read_text());edges=[set(c[:2]) for c in diagram['connections']]
def connected(a,b):assert {a,b} in edges,(a,b)
physical=json.loads((root.parent/'hardware/pinmap.json').read_text())['pins']
for gpio in [34,35,39]:
 id={34:'talk',35:'down',39:'up'}[gpio];connected('esp:'+('VN' if gpio==39 else str(gpio)),id+':1.l');connected('esp:3V3',id+'pull:1');connected(id+':2.l','esp:GND.1')
for device in ['pd','rtc','pwm']:
 connected('esp:21',device+':SDA');connected('esp:22',device+':SCL')
connected('esp:16','pwm:OE');connected('oePull:2','esp:16');connected('esp:3V3','oePull:1')
for i,name in enumerate(['neck','left','right']):connected('pwm:PWM'+str(i),name+':PWM');connected('pd:V+',name+':V+')
for connection in diagram['connections']:
 for endpoint in connection[:2]:
  id,sep,pin=endpoint.partition(':');part=next((p for p in diagram['parts'] if p['id']==id),None)
  if part and part['type'].startswith('chip-'):
   model=json.loads((w/(part['type'][5:]+'.chip.json')).read_text());assert pin in model['pins'],endpoint
checks.append('PASS wiring: external pull-ups, common I2C, OE pull-up, three servo branches, custom-model pin names')
board_pins=json.loads((root/'tests/esp32_board_pins.json').read_text())['pins']
for connection in diagram['connections']:
 for endpoint in connection[:2]:
  if endpoint.startswith('esp:'):assert endpoint[4:] in board_pins,('Unknown Wokwi ESP32 board terminal',endpoint)
assert board_pins['VN']=='GPIO39'
checks.append('PASS native ESP32 terminal names: GPIO39 is VN; every connected board pin exists')
header=(w/'pins.h').read_text()
for name,spec in physical.items():assert f'{name.upper()} = {spec["gpio"]};' in header
signal_targets={
 'lcd_sck':['lcd:SCK'],'lcd_mosi':['lcd:SDA'],'lcd_cs':['lcd:CS'],'lcd_dc':['lcd:DC'],'lcd_reset':['lcd:RST'],
 'rtc_sda':['rtc:SDA','pd:SDA','pwm:SDA'],'rtc_scl':['rtc:SCL','pd:SCL','pwm:SCL'],
 'audio_bclk':['amp:BCLK','mic:SCK'],'audio_lrclk':['amp:LRC','mic:WS'],
 'amplifier_din':['amp:DIN'],'microphone_sd':['mic:SD'],'pet_left':['petL:1.l'],'pet_right':['petR:1.l'],
 'camera_activity_led':['ledR:1'],'talk_button':['talk:1.l'],'volume_down':['down:1.l'],'volume_up':['up:1.l'],
 'servo_outputs_enable':['pwm:OE']}
for name,targets in signal_targets.items():
 terminal=next(pin for pin,target in board_pins.items() if target=='GPIO'+str(physical[name]['gpio']))
 for target in targets:connected('esp:'+terminal,target)
checks.append('PASS every firmware GPIO and signal connection matches the approved hardware pin map')
for result in checks:print(result)
(root/'reports/automated-checks.txt').write_text('\n'.join(checks)+'\n')
