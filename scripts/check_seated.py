"""Repeatable checks against the running seated Webots controller."""
import json
from pathlib import Path
import shutil
import time
import requests

ROOT=Path(__file__).resolve().parents[1]
URL='http://127.0.0.1:8765'

def action(name,args=None,device='dizzy-a'):
    data=requests.post(URL+'/api/action',json={'device':device,'action':name,'args':args or {}},timeout=12).json()
    if not data.get('ok'):raise RuntimeError(data.get('error',data))
    return data['result']

def screenshot(name):
    action('screenshot')
    shutil.copy(ROOT/'reports/simulation.png',ROOT/'reports'/name)

def main(test_llm=True):
    report={'revision':'Compact Seated Companion', 'checks':[], 'hardware_dependent':[
        'Measured PCB outlines, mounting posts, connector access and cable bends',
        'Servo shaft coupling, load, stall current and mechanical stops',
        'USB-C 5V/5A negotiation and temperature',
        'Acoustics, electrode sensitivity and physical stability',
        'ESP32 firmware, actual phone Bluetooth and real camera performance'],
        'voice_scope':'Existing microphone and Gemini interfaces retained. Optional model check can be skipped for geometry-only revisions.'}
    original={id:action('status',device=id) for id in ('dizzy-a','dizzy-b')}
    def passed(name,**evidence):report['checks'].append({'name':name,'result':'PASS',**evidence})
    try:
        action('view_reset',{'preset':'detail'})
        action('tracking_set',{'enabled':False})
        action('head_turn',{'degrees':0})
        for device in original:
            action('arms_pose',{'pose':'rest'},device)
        time.sleep(.5)
        st=action('status')
        joints=action('design_inspect')['joints']
        for joint in joints:
            if joint['name'] in ('left mitten','right mitten'):
                sign=-1 if joint['name']=='left mitten' else 1
                assert all(abs(x-y)<.0002 for x,y in zip(joint['translation'],[sign*.066,0,.079])),joint
        passed('Live hand roots match compact prototype',joints=joints)
        assert st['display_pixels']==[240,240]
        assert all(n==0 for n in st['touch_sensors'].values())
        passed('Circular screen and no resting button contacts',pixels=st['display_pixels'],sensors=st['touch_sensors'])
        screenshot('seated-companion.png')
        for pose in ('wave','hello','lift'):
            action('arms_pose',{'pose':pose})
            samples=[]
            captured=False
            started=time.monotonic()
            for i in range(250):
                st=action('status');samples.append(st['measured_arm_degrees'])
                assert all(-.5<=v<=120.5 for v in st['measured_arm_degrees'].values())
                if pose=='hello' and 113<min(st['measured_arm_degrees'].values()) and not captured:
                    screenshot('seated-hands-hello.png');captured=True
                if time.monotonic()-started>3 and st['arm_pose']=='rest' and max(st['measured_arm_degrees'].values())<.5:break
                time.sleep(.2)
            peak={side:max(s[side] for s in samples) for side in ('left','right')}
            assert peak['right']>90
            assert (peak['left']<1 if pose=='wave' else peak['left']>90)
            assert all(abs(v)<.5 for v in samples[-1].values())
            passed('Measured '+pose+' and automatic return',peak_degrees=peak,final=samples[-1])
        action('quiet_set',{'enabled':True})
        action('touch',{'phase':'stroke'})
        time.sleep(.5)
        st=action('status')
        assert st['arm_pose']=='rest' and st['expression']=='happy'
        passed('Quiet petting keeps expression and suppresses autonomous arms')
        action('quiet_set',{'enabled':False},'dizzy-b')
        action('gesture_send',{'gesture':'wave'})
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            a=action('status');b=action('status',device='dizzy-b')
            if a['delivery']=='delivered' and b['measured_arm_degrees']['right']>20:break
            time.sleep(.2)
        assert a['delivery']=='delivered' and b['arm_pose']=='wave' and b['measured_arm_degrees']['right']>20
        passed('MQTT wave reaches partner with acknowledgement and hand motion',delivery=a['delivery'],partner_arm=b['measured_arm_degrees'])
        time.sleep(6)
        action('components_view',{'enabled':True})
        time.sleep(.2)
        assert action('status')['shell_transparency']>.85
        screenshot('seated-components.png')
        action('components_view',{'enabled':False})
        time.sleep(.2)
        assert action('status')['shell_transparency']==0.0
        passed('Component inspection opens and closes shell')
        for degrees in (-45,45,0):
            action('head_turn',{'degrees':degrees})
            deadline=time.monotonic()+10
            while time.monotonic()<deadline:
                st=action('status')
                if abs(st['measured_head_degrees']-degrees)<.5:break
                time.sleep(.15)
            assert abs(st['measured_head_degrees']-degrees)<.5
            assert all(v==0 for v in st['touch_sensors'].values())
        passed('Head limits and clear side/crown/chest controls')
        photo=action('photo_capture');assert Path(photo['file']).exists()
        action('display_capture')
        passed('Camera and display capture after helmet redesign')
        if test_llm:
            reply=requests.post(URL+'/api/chat',json={'device':'dizzy-a','text':'Use your arms_pose tool to wave your right hand now.','speak':False},timeout=100).json()
            assert reply.get('ok'),reply
            events=requests.get(URL+'/api/status').json()['events']
            reply_index=max(i for i,e in enumerate(events) if e.get('event')=='reply')
            tool=[e for e in events[max(0,reply_index-3):reply_index] if e.get('event')=='action' and e.get('action')=='arms_pose' and e.get('ok')]
            assert tool, 'Gemini did not execute the hand tool'
            # Core and measured checks above validate the commanded movement.
            passed('Typed Gemini hand command',reply=reply.get('reply'),tool_events=tool)
        else:
            report['checks'].append({'name':'Gemini and real voice','result':'NOT RERUN','reason':'Unchanged voice interface; this run validates compact geometry and measured gestures.'})
        time.sleep(7)
        screenshot('seated-companion.png')
    except Exception as exc:
        report['checks'].append({'name':'live run','result':'FAIL','error':str(exc) or type(exc).__name__})
        raise
    finally:
        for device,st in original.items():
            action('quiet_set',{'enabled':st['quiet']},device)
            action('arms_pose',{'pose':'rest'},device)
        action('components_view',{'enabled':False})
        (ROOT/'reports/seated-checks.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    import sys
    main(test_llm='--skip-llm' not in sys.argv)
