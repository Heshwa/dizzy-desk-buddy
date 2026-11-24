"""Capture genuine Webots frames of the seated hello gesture."""
from pathlib import Path
import sys
import time
import json
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parent))
from check_seated import action, screenshot, ROOT

checks=[]
action('components_view',{'enabled':False})
time.sleep(.25)
assert action('status')['shell_transparency']==0.0
action('view_reset',{'preset':'detail'})
action('head_turn',{'degrees':0})
action('target_move',{'x':-.095})
for _ in range(50):
    st=action('status')
    if abs(st['measured_head_degrees'])<.5:break
    time.sleep(.15)
assert st['camera_objects']>0
assert all(v==0 for v in st['touch_sensors'].values())
checks.append({'name':'Final face-panel camera opening and controls','result':'PASS','camera_objects':st['camera_objects'],'touch_sensors':st['touch_sensors']})
photo=action('photo_capture');assert Path(photo['file']).exists()
action('display_capture')
action('expression_set',{'expression':'happy'})
screenshot('seated-companion.png')
action('arms_pose',{'pose':'hello'})
frames=[];captured=False
for i in range(34):
    action('screenshot')
    frames.append(Image.open(ROOT/'reports/simulation.png').convert('RGB').copy())
    st=action('status')
    if not captured and min(st['measured_arm_degrees'].values())>113:
        screenshot('seated-hands-hello.png');captured=True
    time.sleep(.18)
assert captured
frames[0].save(ROOT/'reports/seated-hand-demo.gif',save_all=True,append_images=frames[1:],duration=240,loop=0,optimize=True)
action('arms_pose',{'pose':'rest'})
action('components_view',{'enabled':True})
time.sleep(.25)
assert action('status')['shell_transparency']>.85
screenshot('seated-components.png')
action('components_view',{'enabled':False})
time.sleep(.25)
assert action('status')['shell_transparency']==0.0
screenshot('seated-companion.png')
checks.append({'name':'Final-model two-hand hello capture','result':'PASS','frames':len(frames)})
(ROOT/'reports/seated-final-visual-checks.json').write_text(json.dumps(checks,indent=2))
print('Saved actual simulation GIF and current views.')
