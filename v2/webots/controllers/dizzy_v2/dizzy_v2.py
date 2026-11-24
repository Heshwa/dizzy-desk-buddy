"""The eight-joint reference receives V2 preview commands or runs a finite gait trial."""
import json
import math
import os
from pathlib import Path
import sys
import threading
import time
from urllib.request import Request, urlopen

from controller import Supervisor

V2 = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(V2.parent))
from v2.app.native import pose

NAMES = ('yaw','pitch','left_arm','right_arm','left_hip','right_hip','left_ankle','right_ankle')
DEMO = os.getenv('DIZZY_V2_WEBOTS_TEST')
URL = os.getenv('DIZZY_V2_PANEL','http://127.0.0.1:8875')
control = {'angles':[0.]*8}
online_at = 0.
telemetry = {}
finished = threading.Event()


def communicate():
    global control, online_at
    while not finished.is_set():
        try:
            with urlopen(URL+'/api/status',timeout=.35) as reply:
                control = json.load(reply)['state']
                online_at = time.monotonic()
            if telemetry:
                req=Request(URL+'/api/telemetry',data=json.dumps(telemetry).encode(),
                    headers={'Content-Type':'application/json'},method='POST')
                with urlopen(req,timeout=.35):
                    pass
        except (OSError,ValueError):
            pass
        time.sleep(.05)


def main():
    global telemetry
    robot = Supervisor()
    step = int(robot.getBasicTimeStep())
    motors = [robot.getDevice(n) for n in NAMES]
    sensors = [robot.getDevice(n+'_angle') for n in NAMES]
    for sensor in sensors:
        sensor.enable(step)
    node = robot.getSelf()
    start = node.getPosition()
    angles = (0.,)*8
    fell = False
    max_tilt = 0.
    samples = []
    if not DEMO:
        threading.Thread(target=communicate,daemon=True).start()
    try:
        while robot.step(step) != -1:
            t=robot.getTime()
            rotation=node.getOrientation()
            tilt=math.degrees(math.acos(max(-1,min(1,rotation[8]))))
            max_tilt=max(max_tilt,tilt)
            pos=node.getPosition()
            displacement=math.hypot(pos[0]-start[0],pos[1]-start[1])
            fell |= (tilt>52 or pos[2]<.041)
            if DEMO == 'limits':
                angles=([0,0,0,0],[-45,-20,70,0],[45,25,0,70],[0,0,0,0])[min(3,int(t/2))]
                angles=[*angles,0,0,0,0]
            elif DEMO:
                angles=pose(DEMO,max(0,t-.8),100)
            else:
                angles=control.get('angles',[0.]*8) if time.monotonic()-online_at<.6 else [0.]*8
            moving=not fell
            if not DEMO and control.get('fault'):
                moving=False
            for i,motor in enumerate(motors):
                motor.setAvailableTorque(motor.getMaxTorque() if moving else 0)
                motor.setPosition(math.radians(angles[i] if moving else 0))
            if int(t*10)!=int((t-step/1000)*10):
                telemetry={'t':round(t,3),'distance':round(displacement,4),'x':round(pos[0]-start[0],4),
                    'y':round(pos[1]-start[1],4),'tilt':round(tilt,1),'fallen':fell,
                    'targets':list(angles),'measured':[round(math.degrees(s.getValue()),2) for s in sensors]}
                samples.append(telemetry)
            deadline=12.804 if DEMO=='shuffle' else 8 if DEMO=='limits' else 61
            if DEMO and t>=deadline:
                report={'motion':DEMO,'distance':displacement,'forward':pos[0]-start[0],
                    'fell':fell,'max_tilt':max_tilt,'cycles':10 if DEMO=='shuffle' else 0 if DEMO=='limits' else 50,
                    'observed_peak_joint_deg':[max(abs(s['measured'][i]) for s in samples) for i in range(8)],
                    'observed_min_joint_deg':[min(s['measured'][i] for s in samples) for i in range(8)],
                    'observed_max_joint_deg':[max(s['measured'][i] for s in samples) for i in range(8)],
                    'samples':samples}
                out=Path(os.environ['DIZZY_V2_WEBOTS_OUT'])
                out.write_text(json.dumps(report,indent=2))
                robot.simulationQuit(0)
                break
    finally:
        finished.set()


if __name__=='__main__':
    main()
