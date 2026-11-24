"""Webots adapter. All device API calls stay on the simulation thread."""
import base64
import json
import math
import os
from pathlib import Path
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
# Webots selects Python through runtime.ini, pointing at the project environment.
from controller import Supervisor, Speaker
from dizzy.core import Dizzy, DeviceError
from dizzy.face import render_face
from dizzy.transport import Link

robot = Supervisor()
step = int(robot.getBasicTimeStep())
identity = sys.argv[1] if len(sys.argv) > 1 else robot.getName()
partner = sys.argv[2] if len(sys.argv) > 2 else 'dizzy-b'
state = Dizzy(identity, ROOT / 'runtime' / f'{identity}.json', motion_now=robot.getTime)
link = Link(identity, partner)
face = robot.getDevice('face')
neck = robot.getDevice('neck')
neck.setVelocity(1.05)
neck_position = robot.getDevice('neck_position')
neck_position.enable(step)
arms = {side: robot.getDevice(side+'_shoulder') for side in ('left','right')}
arm_sensors = {side: robot.getDevice(side+'_shoulder_position') for side in arms}
for motor in arms.values(): motor.setVelocity(1.2)
for sensor in arm_sensors.values(): sensor.enable(step)
camera = robot.getDevice('camera')
camera.enable(step)
camera.recognitionEnable(step)
light = robot.getDevice('camera_light')
speaker = robot.getDevice('speaker')
keyboard = robot.getKeyboard()
keyboard.enable(step)
sensors = {name: robot.getDevice(name) for name in ('pet_left', 'pet_right', 'talk', 'volume_down', 'volume_up')}
for sensor in sensors.values():
    sensor.enable(step)
previous_sensors = dict.fromkeys(sensors, False)
target_node = robot.getFromDef('FACE_TARGET')
# Keep the camera test target visible to robot cameras without blocking the desk view.
target_node.setVisibility(robot.getFromDef('MAIN_VIEW'), False)
last_draw = 0
last_gain = None
last_track = None
last_alarm = False
last_presence = 0
last_partner = 0
camera_until = 0
restart_at = 0
last_telemetry = 0


def draw():
    frame = render_face(state.status(), time.time())
    image = face.imageNew(frame.tobytes(), face.RGBA, frame.width, frame.height)
    face.imagePaste(image, 0, 0, False)
    face.imageDelete(image)


def handle(action, args):
    global camera_until, restart_at
    if action == 'design_inspect':
        children=robot.getSelf().getBaseNodeField('children')
        joints=[]
        for i in range(children.getCount()):
            node=children.getMFNode(i)
            if node.getTypeName()!='HingeJoint': continue
            endpoint=node.getField('endPoint').getSFNode()
            joints.append({'name':endpoint.getField('name').getSFString(),
                'translation':endpoint.getField('translation').getSFVec3f(),
                'position':endpoint.getPosition(), 'rotation':endpoint.getField('rotation').getSFRotation(),
                'anchor':node.getField('jointParameters').getSFNode().getField('anchor').getSFVec3f()})
        return {'joints':joints, 'shell_transparency':robot.getSelf().getField('shellTransparency').getSFFloat()}
    if action == 'components_view':
        enabled = args.get('enabled', True)
        if type(enabled) is not bool: raise DeviceError('enabled must be true or false')
        robot.getSelf().getField('shellTransparency').setSFFloat(.86 if enabled else 0.0)
        return {'components_visible': enabled, 'model': 'assembly envelopes, not measured component CAD'}
    if action == 'controller_restart':
        restart_at = time.time() + .7
        return {'restarting': True}
    if action == 'photo_capture':
        path = ROOT / 'runtime' / f'{identity}-photo.png'
        result = camera.saveImage(str(path), 100)
        if result != 0:
            raise DeviceError('Camera capture failed')
        camera_until = time.time() + 2
        return {'file': str(path), 'image': base64.b64encode(path.read_bytes()).decode(), 'mime': 'image/png'}
    if action == 'display_capture':
        path = ROOT / 'reports' / f'{identity}-display.png'
        image = face.imageCopy(0, 0, face.getWidth(), face.getHeight())
        face.imageSave(image, str(path))
        face.imageDelete(image)
        return {'file': str(path)}
    if action == 'screenshot':
        path = ROOT / 'reports' / 'simulation.png'
        robot.exportImage(str(path), 95)
        return {'file': str(path)}
    if action == 'target_move':
        position = target_node.getField('translation').getSFVec3f()
        position[0] = Dizzy.number(args.get('x'), -0.6, 0.6)
        target_node.getField('translation').setSFVec3f(position)
        return {'x': position[0]}
    if action == 'view_reset':
        node = robot.getRoot().getField('children')
        view = next(node.getMFNode(i) for i in range(node.getCount()) if node.getMFNode(i).getTypeName() == 'Viewpoint')
        presets = {'portrait': ([-0.03, -0.42, 1.035], [-0.1902078823507879, 0.18029091742840994, 0.9650472250540131, 1.6598026520988183]), 'overview': ([0.1, -0.72, 1.1], [-0.16319535023462056, 0.14209584013381174, 0.9763073542068941, 1.7325108551347683]), 'detail': ([0.015, -0.56, 1.08], [-0.1902078823507879, 0.18029091742840994, 0.9650472250540131, 1.6598026520988183])}
        view.getField('fieldOfView').setSFFloat(0.9)
        position, rotation = presets.get(args.get('preset'), presets['overview'])
        view.getField('orientation').setSFRotation(rotation)
        view.getField('position').setSFVec3f(position)
        return {'view_reset': True, 'position': position, 'rotation': rotation}
    if action == 'world_reload':
        robot.worldReload()
        return {'reloading': True}
    if action == 'simulation_quit':
        robot.simulationQuit(0)
        return {'quitting': True}
    result = state.execute(action, args)
    if action == 'status':
        result['shell_transparency'] = robot.getSelf().getField('shellTransparency').getSFFloat()
        result['simulation_time'] = robot.getTime()
        result['measured_arm_degrees'] = {side: round(math.degrees(sensor.getValue()),2) for side,sensor in arm_sensors.items()}
        result['measured_head_degrees'] = round(math.degrees(neck_position.getValue()), 2)
        result['camera_objects'] = camera.getRecognitionNumberOfObjects()
        result['camera_fov_degrees'] = round(math.degrees(camera.getFov()), 2)
        result['display_pixels'] = [face.getWidth(), face.getHeight()]
        result['alarm_audio_active'] = bool(state.ringing) and not state.settings['quiet']
        result['camera_active'] = bool(state.tracking or time.time() < camera_until)
        result['touch_sensors'] = {name: sensor.getValue() for name, sensor in sensors.items()}
    return result


try:
    while robot.step(step) != -1:
        now = time.time()
        while not link.inbox.empty():
            kind, message = link.inbox.get_nowait()
            try:
                if kind == 'command':
                    try:
                        result = handle(message['action'], message.get('args', {}))
                        reply = {'type': 'result', 'request_id': message['request_id'], 'ok': True, 'result': result}
                    except (DeviceError, ValueError, KeyError, TypeError) as exc:
                        reply = {'type': 'result', 'request_id': message.get('request_id'), 'ok': False, 'error': str(exc)}
                    link.responses.put(reply)
                elif kind == 'service_offline':
                    state.voice = 'idle'
                elif kind == 'presence':
                    state.partner_online = message
                    if message:
                        last_partner = now
                elif kind == 'gesture' and message.get('sender') == partner:
                    if state.receive_gesture(message):
                        link.publish('ack', {'id': message['id']}, target=partner)
                elif kind == 'ack':
                    state.acknowledge(message.get('id'))
            except (DeviceError, ValueError, TypeError) as exc:
                state.emit('notice', message=str(exc))
        if restart_at and now >= restart_at:
            link.close()
            robot.getSelf().restartController()
            break
        if now - last_presence > 2:
            link.publish('presence', {'online': True, 'at': now}, retain=True)
            last_presence = now
        if now - last_partner > 8:
            state.partner_online = False
        readings = {name: sensor.getValue() > 0 for name, sensor in sensors.items()}
        try:
            was_pet_down = any(previous_sensors[n] for n in ('pet_left', 'pet_right'))
            is_pet_down = any(readings[n] for n in ('pet_left', 'pet_right'))
            if is_pet_down and not was_pet_down:
                state.touch('down')
            for name in ('pet_left', 'pet_right'):
                if readings[name] and not previous_sensors[name]:
                    state.touch('zone', 'left' if name == 'pet_left' else 'right')
            if was_pet_down and not is_pet_down:
                state.touch('up')
            for name in ('talk', 'volume_down', 'volume_up'):
                if readings[name] and not previous_sensors[name]:
                    if name == 'talk':
                        state.emit('talk_request')
                    else:
                        change = .05 if name == 'volume_up' else -.05
                        state.execute('volume_set', {'level': max(0, min(1, state.settings['volume'] + change))})
        except DeviceError as exc:
            state.emit('notice', message=str(exc))
        previous_sensors = readings
        key = keyboard.getKey()
        while key != -1:
            if identity == 'dizzy-a':
                try:
                    if key == ord('T'): state.touch('tap')
                    elif key == ord('S'): state.touch('stroke')
                    elif key == ord('H'): state.pose_arms('hello')
                    elif key == ord('W'): state.pose_arms('wave')
                    elif key == ord('G'): state.send_gesture('wave')
                    elif key == ord('N'): state.send_gesture('goodnight')
                    elif key == ord('V'): state.emit('talk_request')
                    elif key == ord('Q'): state.execute('quiet_set', {'enabled': not state.settings['quiet']})
                    elif key == ord('A'): state.execute('timer_start', {'seconds': 5})
                    elif key == ord('C'): handle('photo_capture', {})
                    elif key == ord('F'): state.tracking = not state.tracking
                    elif key == ord('P'): state.execute('phone_connect', {'connected': not state.phone})
                    elif key in (ord('+'), ord('=')):
                        state.execute('volume_set', {'level': min(1, state.settings['volume'] + .05)})
                    elif key == ord('-'):
                        state.execute('volume_set', {'level': max(0, state.settings['volume'] - .05)})
                    elif key == ord('M'): state.execute('music_control', {'command': 'pause' if state.playing else 'play'})
                except DeviceError as exc:
                    state.emit('notice', message=str(exc))
            key = keyboard.getKey()
        offset = None
        objects = camera.getRecognitionObjects()
        if objects:
            offset = -(objects[0].getPositionOnImage()[0] - camera.getWidth() / 2) / (camera.getWidth() / 2)
        state.tick(offset)
        neck.setPosition(math.radians(state.head))
        for i, motor in enumerate(arms.values()): motor.setPosition(math.radians(max(0., min(120., state.arms[i]))))
        light.set(1 if state.tracking or now < camera_until else 0)
        current = state.status()
        track_path = str(ROOT / 'assets' / f'music-{state.track}.wav')
        if current['music_gain'] != last_gain or track_path != last_track:
            if last_track and track_path != last_track:
                speaker.stop(last_track)
            if current['music_gain']:
                Speaker.playSound(speaker, speaker, track_path, current['music_gain'], 1, 0, True)
            else:
                speaker.stop(track_path)
            last_gain, last_track = current['music_gain'], track_path
        alarm_audible = bool(state.ringing) and not state.settings['quiet']
        if alarm_audible != last_alarm:
            path = str(ROOT / 'assets' / 'alarm.wav')
            if alarm_audible:
                Speaker.playSound(speaker, speaker, path, state.settings['volume'], 1, 0, True)
            else:
                speaker.stop(path)
            last_alarm = alarm_audible
        while state.outgoing:
            link.publish('gesture', state.outgoing.pop(0), target=partner)
        while state.events:
            event = state.events.pop(0)
            if event['event'] in ('chirp', 'greeting') and not state.settings['quiet']:
                Speaker.playSound(speaker, speaker, str(ROOT / 'assets' / 'chirp.wav'), state.settings['volume'], 1, 0, False)
            link.responses.put({'type': 'event', **event})
        current['measured_arm_degrees'] = {side: round(math.degrees(sensor.getValue()),2) for side,sensor in arm_sensors.items()}
        current['measured_head_degrees'] = round(math.degrees(neck_position.getValue()), 2)
        current['camera_objects'] = camera.getRecognitionNumberOfObjects()
        current['alarm_audio_active'] = alarm_audible
        current['camera_active'] = bool(state.tracking or now < camera_until)
        link.snapshot = current
        if now - last_telemetry > .5:
            link.publish('telemetry', current)
            last_telemetry = now
        if now - last_draw > 0.08:
            draw()
            last_draw = now
except Exception:
    traceback.print_exc()
finally:
    link.close()
