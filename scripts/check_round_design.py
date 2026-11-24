"""Verify the fitted model against the running Webots devices and export previews."""
import json
import math
from pathlib import Path
import shutil
import time
import requests
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
URL='http://127.0.0.1:8765/api/action'


def action(name,args=None,device='dizzy-a'):
    response=requests.post(URL,json={'device':device,'action':name,'args':args or {}},timeout=10).json()
    if not response.get('ok'):raise RuntimeError(response.get('error','No controller confirmation'))
    return response['result']


def wait_for(predicate,timeout=8):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        state=action('status')
        if predicate(state):return state
        time.sleep(.15)
    raise AssertionError('Expected simulated state did not arrive')


def main():
    original={device:action('status',device=device) for device in ('dizzy-a','dizzy-b')}
    report={'head':[],'hardware':'Electrical performance, PD negotiation and actual servo loads are not tested in Webots.'}
    try:
        action('quiet_set',{'enabled':False})
        action('tracking_set',{'enabled':False})
        action('view_reset',{'preset':'detail'})
        for angle in (-45,45,0):
            action('head_turn',{'degrees':angle})
            state=wait_for(lambda state:abs(state['measured_head_degrees']-angle)<.5)
            assert state['display_pixels']==[240,240]
            assert all(v==0 for v in state['touch_sensors'].values())
            assert math.isclose(state['camera_fov_degrees'],120,abs_tol=.1)
            report['head'].append({k:state[k] for k in ('measured_head_degrees','display_pixels','touch_sensors','camera_fov_degrees')})
            action('screenshot')
            shutil.copy(ROOT/'reports/simulation.png',ROOT/f'reports/round-yaw-{angle}.png')
        action('target_move',{'x':-.095})
        wait_for(lambda state:state['camera_objects']>0)
        action('tracking_set',{'enabled':True})
        action('target_move',{'x':.04})
        tracked=wait_for(lambda state:12<abs(state['measured_head_degrees'])<=45)
        action('tracking_set',{'enabled':False})
        fixed=action('status')
        action('target_move',{'x':-.4})
        time.sleep(.4)
        assert abs(action('status')['target_degrees']-fixed['target_degrees'])<.1
        report['tracking']={'measured_degrees':tracked['measured_head_degrees'],'recognized_objects':tracked['camera_objects'],'stops_on_command':True}
        action('head_turn',{'degrees':0})
        wait_for(lambda state:abs(state['measured_head_degrees'])<.5)
        action('target_move',{'x':-.095})
        wait_for(lambda state:state['camera_objects']>0)
        action('photo_capture')
        action('display_capture')
        frame=Image.open(ROOT/'reports/dizzy-a-display.png').convert('RGB')
        assert frame.size==(240,240)
        for y in range(240):
            for x in range(240):
                if frame.getpixel((x,y))!=(5,13,18):
                    assert (x-119.5)**2+(y-119.5)**2<=108**2
        report['display_pixels_inside_circle']='PASS'
        action('expression_set',{'expression':'happy'})
        action('expression_set',{'expression':'heart'},'dizzy-b')
        time.sleep(.5)
        action('screenshot')
        shutil.copy(ROOT/'reports/simulation.png',ROOT/'reports/round-design-detail.png')
        action('view_reset')
        time.sleep(.5)
        action('screenshot')
        (ROOT/'reports/round-design-checks.json').write_text(json.dumps(report,indent=2))
        print('PASS: ±45 degree yaw, five resting pads, round LCD pixels, wide camera, tracking/stop, capture and previews')
    finally:
        action('tracking_set',{'enabled':False})
        for device,state in original.items():
            action('quiet_set',{'enabled':state['quiet']},device)
            action('volume_set',{'level':state['volume']},device)


if __name__=='__main__':main()
