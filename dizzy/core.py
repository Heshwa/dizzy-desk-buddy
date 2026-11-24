"""Device behavior. Only the controller owns and mutates this state."""
from __future__ import annotations

import json
import math
import os
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


class DeviceError(ValueError):
    pass


class Dizzy:
    def __init__(self, device_id: str, storage: Path, now=time.time, motion_now=None):
        self.device_id = device_id
        self.storage = Path(storage)
        self.now = now
        self.motion_now = motion_now or now
        self.last_motion_tick = self.motion_now()
        self.zone = ZoneInfo('Asia/Kolkata')
        self.settings = {'volume': 0.5, 'quiet': False}
        self.alarms = []
        self.seen = {}
        if self.storage.exists():
            saved = json.loads(self.storage.read_text())
            self.settings.update(saved.get('settings', {}))
            self.alarms = saved.get('alarms', [])
            self.seen = saved.get('seen', {})
        self.expression = 'sleepy'
        self.expression_until = 0
        self.arms = [0., 0.]
        self.arm_targets = [0., 0.]
        self.arm_sequence = []
        self.arm_pose = "rest"
        self.head = 0.0
        self.target = 0.0
        self.return_at = 0
        self.tracking = False
        self.phone = False
        self.playing = False
        self.track = 0
        self.tracks = ['Desk morning', 'Little orbit', 'Evening rain']
        self.voice = 'idle'
        self.ringing = None
        self.timer = None
        self.partner_online = False
        self.delivery = 'idle'
        self.pending = {}
        self.outgoing = []
        self.events = []
        self.last_tick = self.now()
        self.last_activity = self.now()
        self.tap_at = None
        self.touch_down = None
        self.stroke_at = None
        self.touch_stroked = False

    def save(self):
        self.storage.parent.mkdir(parents=True, exist_ok=True)
        saved = {'settings': self.settings, 'alarms': self.alarms, 'seen': self.seen}
        temp = self.storage.with_suffix('.tmp')
        temp.write_text(json.dumps(saved, indent=2))
        os.replace(temp, self.storage)

    def emit(self, event, **data):
        self.events.append({'event': event, **data})

    def react(self, expression, duration=2):
        self.expression = expression
        self.expression_until = self.now() + duration

    def pose_arms(self, pose, autonomous=False):
        patterns = {
            'rest': [(0,0,0)],
            'lift': [(0,118,118),(3,0,0)],
            'wave': [(0,0,118),(2.2,0,75),(3.1,0,118),(4.0,0,75),(4.9,0,118),(5.8,0,0)],
            'hello': [(0,118,118),(2.2,80,80),(3.1,118,118),(4.2,0,0)],
            'happy': [(0,40,40),(1.2,0,0)],
            'goodnight': [(0,20,20),(1,0,0)],
        }
        if pose not in patterns:
            raise DeviceError('Choose rest, lift, wave, hello, happy, or goodnight')
        if autonomous and (self.settings['quiet'] or self.ringing):
            return
        self.arm_pose = pose
        self.arm_sequence = [(self.motion_now()+t,left,right) for t,left,right in patterns[pose]]

    def status(self):
        ducked = self.voice != 'idle' or self.ringing is not None
        return {
            'id': self.device_id, 'clock': datetime.fromtimestamp(self.now(), self.zone).isoformat(),
            'expression': self.face(), 'head_degrees': round(self.head, 2),
            'arm_degrees': dict(zip(('left','right'), map(lambda n: round(n,2), self.arms))),
            'arm_pose': self.arm_pose,
            'target_degrees': self.target, 'tracking': self.tracking,
            'quiet': self.settings['quiet'], 'volume': self.settings['volume'],
            'phone_connected': self.phone, 'playing': self.playing,
            'track': self.tracks[self.track], 'track_index': self.track,
            'music_gain': 0 if self.settings['quiet'] or not self.playing else self.settings['volume'] * (0.15 if ducked else 1),
            'voice': self.voice, 'ringing': self.ringing,
            'alarms': [dict(a) for a in self.alarms],
            'timer_remaining': max(0, self.timer - self.now()) if self.timer else None,
            'partner_online': self.partner_online, 'delivery': self.delivery,
        }

    def face(self):
        if self.ringing:
            return 'alarm'
        if self.voice != 'idle':
            return self.voice
        if self.now() < self.expression_until:
            return self.expression
        if self.playing:
            return 'music'
        return 'idle' if self.tracking or self.now() - self.last_activity < 30 else 'sleepy'

    def touch(self, phase, zone='left'):
        now = self.now()
        self.last_activity = now
        if phase == 'down':
            if self.touch_down is None:
                self.touch_down = now
                self.touch_stroked = False
        elif phase == 'up' and self.touch_down is not None:
            held = now - self.touch_down
            self.touch_down = None
            if self.ringing:
                self.execute('alarm_snooze', {})
            elif self.touch_stroked:
                self.touch_stroked = False
            elif held >= 1.2:
                self.tap_at = None
                self.send_gesture('goodnight')
            else:
                self.touch('tap', zone)
        elif phase == 'stroke':
            self.tap_at = None
            self.touch_stroked = True
            self.react('happy', 3)
            self.pose_arms('happy', autonomous=True)
            self.emit('chirp')
        elif phase == 'tap':
            if self.ringing:
                self.execute('alarm_snooze', {})
            elif self.tap_at is not None and now - self.tap_at <= 0.35:
                self.tap_at = None
                self.send_gesture('wave')
            else:
                self.tap_at = now
        elif phase == 'zone':
            if self.stroke_at and self.stroke_at[0] != zone and now - self.stroke_at[1] < 0.8:
                self.touch('stroke')
                self.stroke_at = None
            else:
                self.stroke_at = (zone, now)
        elif phase not in ('down', 'up'):
            raise DeviceError('Unknown touch gesture')

    def send_gesture(self, gesture):
        if gesture not in ('wave', 'goodnight'):
            raise DeviceError('Choose wave or goodnight')
        if not self.partner_online:
            self.delivery = 'offline'
            raise DeviceError('The other Dizzy is offline')
        event = {'id': uuid.uuid4().hex, 'sender': self.device_id,
                 'gesture': gesture, 'expires': self.now() + 10}
        self.pending[event['id']] = event['expires']
        self.delivery = 'sending'
        self.outgoing.append(event)
        self.pose_arms(gesture, autonomous=True)
        return {'event_id': event['id'], 'delivery': 'sending'}

    def receive_gesture(self, event):
        if event.get('gesture') not in ('wave', 'goodnight') or not isinstance(event.get('id'), str):
            return False
        expiry = float(event.get('expires', 0))
        if expiry <= self.now() or expiry > self.now() + 15:
            return False
        if event['id'] in self.seen:
            return True  # acknowledge duplicates without another reaction
        self.seen = {k: v for k, v in self.seen.items() if v > self.now()}
        self.seen[event['id']] = expiry
        self.save()
        self.react('heart' if event['gesture'] == 'wave' else 'goodnight', 4)
        if not self.settings['quiet']:
            self.target = -30
            self.return_at = self.now() + 1.2
        self.pose_arms(event['gesture'], autonomous=True)
        self.emit('greeting', gesture=event['gesture'])
        return True

    def acknowledge(self, event_id):
        if event_id in self.pending and self.pending.pop(event_id) > self.now():
            self.delivery = 'delivered'
            self.react('heart', 2)

    def tick(self, face_offset=None):
        now = self.now()
        dt = min(max(now - self.last_tick, 0), 0.1)
        self.last_tick = now
        if self.tap_at is not None and now - self.tap_at > 0.35:
            self.tap_at = None
            self.react('happy')
            self.pose_arms('happy', autonomous=True)
            self.emit('chirp')
        if self.tracking and face_offset is not None and not self.settings['quiet']:
            self.target = max(-45, min(45, self.head + face_offset * 12))
        if self.return_at and now >= self.return_at:
            self.target = 0
            self.return_at = 0
        if self.ringing:
            self.arm_sequence = []
            self.arm_targets = [0., 0.]
            self.arm_pose = 'rest'
        motion_now = self.motion_now()
        arm_dt = min(max(motion_now-self.last_motion_tick, 0), .1)
        self.last_motion_tick = motion_now
        while self.arm_sequence and self.arm_sequence[0][0] <= motion_now:
            _, left, right = self.arm_sequence.pop(0)
            self.arm_targets = [left, right]
        for i in range(2):
            self.arms[i] += max(-65*arm_dt, min(65*arm_dt, self.arm_targets[i]-self.arms[i]))
        if not self.arm_sequence and self.arm_targets == [0,0] and max(self.arms) < .01:
            self.arm_pose = 'rest'
        speed = 60 * dt
        self.head += max(-speed, min(speed, self.target - self.head))
        for alarm in self.alarms:
            if alarm['enabled'] and alarm['at'] <= now:
                # Fire recent alarms once. Advance repeating alarms past downtime.
                due = alarm['at']
                if alarm.get('weekdays'):
                    next_date = datetime.fromtimestamp(due, self.zone) + timedelta(days=1)
                    while next_date.weekday() not in alarm['weekdays'] or next_date.timestamp() <= now:
                        next_date += timedelta(days=1)
                    alarm['at'] = next_date.timestamp()
                else:
                    alarm['enabled'] = False
                if now - due < 60:
                    self.ringing = {'id': alarm['id'], 'label': alarm['label']}
                self.save()
        if self.timer is not None and now >= self.timer:
            self.timer = None
            self.ringing = {'id': 'timer', 'label': 'Timer finished'}
        for event_id, expiry in list(self.pending.items()):
            if now >= expiry:
                self.pending.pop(event_id)
                self.delivery = 'unconfirmed'

    def execute(self, action, args):
        if action not in ('status', 'voice_state'):
            self.last_activity = self.now()
        if not isinstance(args, dict):
            raise DeviceError('Tool arguments must be an object')
        if action == 'clock_read':
            return {'time': self.status()['clock']}
        if action == 'alarm_set':
            text = str(args.get('at', ''))
            try:
                date = datetime.fromisoformat(text)
            except ValueError as exc:
                raise DeviceError('Specify an exact date, AM or PM, and time') from exc
            if date.tzinfo is None:
                date = date.replace(tzinfo=self.zone)
            if date.timestamp() <= self.now():
                raise DeviceError('Choose a future alarm time')
            weekdays = args.get('weekdays', [])
            if not isinstance(weekdays, list) or any(type(d) is not int or d not in range(7) for d in weekdays):
                raise DeviceError('Weekdays must be numbers from 0 for Monday to 6 for Sunday')
            if weekdays and date.weekday() not in weekdays:
                raise DeviceError('The first alarm must fall on a selected weekday')
            alarm = {'id': uuid.uuid4().hex[:8], 'at': date.timestamp(),
                     'label': str(args.get('label', 'Alarm'))[:60], 'enabled': True, 'weekdays': weekdays}
            self.alarms.append(alarm)
            self.save()
            return dict(alarm)
        if action == 'alarm_list':
            return {'alarms': [dict(a) for a in self.alarms]}
        if action == 'alarm_cancel':
            alarm = next((a for a in self.alarms if a['id'] == args.get('id')), None)
            if not alarm:
                raise DeviceError('Alarm not found')
            alarm['enabled'] = False
            if self.ringing and self.ringing['id'] == alarm['id']:
                self.ringing = None
            self.save()
        elif action == 'alarm_snooze':
            if not self.ringing:
                raise DeviceError('No alarm is ringing')
            minutes = self.number(args.get('minutes', 5), 1, 60)
            self.alarms.append({'id': uuid.uuid4().hex[:8], 'at': self.now() + minutes * 60,
                                'label': self.ringing['label'], 'enabled': True, 'weekdays': []})
            self.ringing = None
            self.save()
        elif action == 'alarm_dismiss':
            self.ringing = None
        elif action == 'timer_start':
            self.timer = self.now() + self.number(args.get('seconds'), 1, 86400)
        elif action == 'timer_cancel':
            self.timer = None
        elif action == 'timer_check':
            return {'seconds_remaining': max(0, self.timer - self.now()) if self.timer else None}
        elif action == 'phone_connect':
            connected = args.get('connected', True)
            if type(connected) is not bool:
                raise DeviceError('connected must be true or false')
            self.phone = connected
            if not self.phone:
                self.playing = False
        elif action == 'music_control':
            if not self.phone:
                raise DeviceError('Connect the simulated phone first')
            command = args.get('command')
            if command in ('play', 'resume', 'pause'):
                self.playing = command != 'pause'
            elif command in ('next', 'previous'):
                self.track = (self.track + (1 if command == 'next' else -1)) % len(self.tracks)
            else:
                raise DeviceError('Choose play, pause, next, or previous')
        elif action == 'volume_set':
            self.settings['volume'] = self.number(args.get('level'), 0, 1)
            self.save()
        elif action == 'arms_pose':
            self.pose_arms(args.get('pose'))
        elif action == 'head_turn':
            self.tracking = False
            self.target = self.number(args.get('degrees'), -45, 45)
            self.return_at = self.now() + 2 if args.get('temporary', False) else 0
        elif action == 'expression_set':
            expression = args.get('expression')
            if expression not in ('happy', 'sleepy', 'heart', 'goodnight', 'blink'):
                raise DeviceError('Unknown expression')
            self.react(expression, 4)
        elif action == 'quiet_set':
            if type(args.get('enabled')) is not bool:
                raise DeviceError('enabled must be true or false')
            self.settings['quiet'] = args['enabled']
            if args['enabled']:
                self.pose_arms('rest')
                self.target = self.head
                self.return_at = 0
            self.save()
        elif action == 'tracking_set':
            if type(args.get('enabled')) is not bool:
                raise DeviceError('enabled must be true or false')
            self.tracking = args['enabled']
        elif action == 'partner_status':
            return {'online': self.partner_online, 'delivery': self.delivery}
        elif action == 'gesture_send':
            return self.send_gesture(args.get('gesture', 'wave'))
        elif action == 'voice_state':
            state = args.get('state')
            if state not in ('idle', 'listening', 'thinking', 'speaking'):
                raise DeviceError('Unknown voice state')
            self.voice = state
        elif action == 'touch':
            self.touch(args.get('phase', 'tap'), args.get('zone', 'left'))
        elif action == 'status':
            pass
        else:
            raise DeviceError(f'Unknown action: {action}')
        return self.status()

    @staticmethod
    def number(value, low, high):
        if isinstance(value, bool):
            raise DeviceError('Expected a number')
        try:
            value = float(value)
        except (TypeError, ValueError) as exc:
            raise DeviceError('Expected a number') from exc
        if not math.isfinite(value) or not low <= value <= high:
            raise DeviceError(f'Choose a number between {low} and {high}')
        return value
