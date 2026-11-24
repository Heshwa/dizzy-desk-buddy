"""V2 simulator device. The real controller uses a parallel firmware action endpoint."""
import time
from dizzy.core import DeviceError, Dizzy
from .native import MOTION, pose

EVENT_DEFAULTS = {'pet': [0, 1], 'greeting': [7, 15, 23], 'win': [4, 12, 20]}
STATUSES = {'recording': 25, 'thinking': 26, 'speaking': 27, 'alarm': 28, 'fault': 29}


class Pet(Dizzy):
    def __init__(self, *args, motion_now=time.monotonic, **kwargs):
        super().__init__(*args, motion_now=motion_now, **kwargs)
        self.settings.setdefault('favorites', [0, 7, 9, 20])
        self.settings.setdefault('reactions', EVENT_DEFAULTS.copy())
        self.settings.setdefault('tempo', 100)
        self.rotation = {}
        self.reaction = 24
        self.reaction_until = 0.
        self.visual_started = self.motion_now()
        self.last_visual = 24
        self.pitch = 0.
        self.pitch_target = 0.
        self.motion = 'rest'
        self.motion_started = self.motion_until = 0.
        self.leg_armed = self.floor = False
        self.motion_fault = ''
        self.angles = [0.] * 8
        self.time_taps = []
        self.stopwatch_at = None
        self.stopwatch_saved = 0.
        self.track_fault = ''

    def show(self, face, duration=2.0):
        self.reaction = face
        self.reaction_until = self.motion_now() + duration
        self.visual_started = self.motion_now()

    def pick(self, event):
        choices = self.settings['reactions'].get(event) or EVENT_DEFAULTS[event]
        turn = self.rotation.get(event, 0)
        self.rotation[event] = turn + 1
        self.show(choices[turn % len(choices)])

    def react(self, expression, duration=2):
        super().react(expression, duration)
        if expression in ('heart', 'goodnight'):
            self.pick('greeting')
        elif expression == 'happy':
            self.pick('pet')
        elif expression == 'sleepy':
            self.show(5, duration)
        elif expression == 'blink':
            self.show(3, duration)

    def visual(self):
        now = self.motion_now()
        face = STATUSES['alarm'] if self.ringing else STATUSES.get(self.voice)
        if face is None:
            face = 29 if self.motion_fault else self.reaction if now < self.reaction_until else 24
        if face != self.last_visual:
            self.visual_started = now
            self.last_visual = face
        return face, round((now - self.visual_started) * 1000)

    def tick(self, face_offset=None):
        previous = self.last_motion_tick
        try:
            super().tick(face_offset)
        except DeviceError:
            # An offline double tap reports delivery state and must not interrupt the clock.
            pass
        now = self.motion_now()
        if self.settings['quiet'] or self.ringing or now >= self.motion_until:
            self.motion = 'rest'
        dt = min(max(now - previous, 0), 0.1)
        self.pitch += max(-dt*60, min(dt*60, self.pitch_target-self.pitch))
        # The animated robot uses the same joint limits as the firmware.
        target = [self.head, self.pitch, *[min(90, v) for v in self.arms], 0, 0, 0, 0]
        if self.motion != 'rest':
            target = pose(self.motion, now - self.motion_started, self.settings['tempo'])
        if self.motion_fault:
            target = [0.] * 8
        for axis, angle in enumerate(target):
            speed = (75 if axis < 4 else 120) * dt
            self.angles[axis] += max(-speed, min(speed, angle-self.angles[axis]))

    def status(self):
        state = super().status()
        face, phase = self.visual()
        state.update(face=face, phase=phase, favorites=self.settings['favorites'],
            reactions=self.settings['reactions'], angles=self.angles[:], motion=self.motion,
            floor=self.floor, armed=self.leg_armed, fault=self.motion_fault, bpm=self.settings['tempo'],
            stopwatch=self.stopwatch_saved + (self.motion_now()-self.stopwatch_at if self.stopwatch_at is not None else 0))
        return state

    def execute(self, action, args):
        if not isinstance(args, dict):
            raise DeviceError('Supply an object of arguments.')
        if action in ('head_turn','head_pitch','arm_lift','arms_pose'):
            if self.motion_fault:
                raise DeviceError('Clear the motor fault on the local controls.')
            if self.settings['quiet'] or self.ringing:
                raise DeviceError('Stop the alarm or turn off quiet mode first.')
            self.motion = 'rest'
        if action == 'face_preview':
            face = args.get('id')
            if type(face) is not int or face not in range(24):
                raise DeviceError('Choose a reaction from the library.')
            self.show(face, 3)
            return {'face': face}
        if action in ('favorites_set', 'reaction_assign'):
            ids = args.get('ids')
            if not isinstance(ids, list) or any(type(i) is not int or i not in range(24) for i in ids):
                raise DeviceError('Select reactions from the library.')
            ids = list(dict.fromkeys(ids))
            if action == 'favorites_set':
                self.settings['favorites'] = ids
            else:
                event = args.get('event')
                if event not in EVENT_DEFAULTS or not ids:
                    raise DeviceError('Select an event and at least one reaction.')
                self.settings['reactions'][event] = ids
                self.rotation[event] = 0
            self.save()
            return {'ids': ids}
        if action == 'game_win':
            self.pick('win')
            return {'face': self.reaction}
        if action == 'head_pitch':
            self.pitch_target = self.number(args.get('degrees'), -20, 25)
            return {'degrees': self.pitch_target}
        if action == 'arm_lift':
            side = args.get('side')
            if side not in ('left', 'right'):
                raise DeviceError('Choose left or right.')
            angle = self.number(args.get('degrees', 65), 0, 90)
            target = [angle, 0] if side == 'left' else [0, angle]
            now = self.motion_now()
            self.arm_sequence = [(now, *target), (now+2, 0, 0)]
            return {'side': side, 'degrees': angle}
        if action == 'floor_select':
            self.floor = args.get('enabled') is True
            self.leg_armed = False
            self.motion = 'rest'
            return {'floor': self.floor}
        if action == 'motion_arm':
            if not self.floor or not args.get('local'):
                raise DeviceError('Select floor mode and arm on the local controls.')
            self.motion_fault = ''
            self.leg_armed = True
            return {'armed': True}
        if action in ('motion_stop', 'motion_fault'):
            self.motion = 'rest'
            self.leg_armed = False
            self.motion_fault = str(args.get('reason', 'Motor stop')) if action == 'motion_fault' else ''
            return {'armed': False}
        if action == 'motion_play':
            name = args.get('name')
            if name not in MOTION or name == 'rest':
                raise DeviceError('Choose a dance, shuffle or wave.')
            if name != 'wave' and not (self.floor and self.leg_armed and not self.motion_fault):
                raise DeviceError('Arm floor motion locally first.')
            if self.settings['quiet'] or self.ringing:
                raise DeviceError('Stop the alarm or turn off quiet mode first.')
            self.motion = name
            self.motion_started = self.motion_now()
            duration = 1200 / self.settings['tempo'] if name == 'shuffle' else 60 if name != 'wave' else 3
            self.motion_until = self.motion_started + self.number(args.get('seconds', duration), 1, 60)
            return {'motion': name}
        if action == 'tempo_tap':
            now = self.motion_now()
            self.time_taps = [t for t in self.time_taps[-3:] if now-t < 2] + [now]
            if len(self.time_taps) > 1:
                span = self.time_taps[-1]-self.time_taps[0]
                if span > 0.15:
                    self.settings['tempo'] = round(max(60, min(130, 60*(len(self.time_taps)-1)/span)))
                    self.save()
            return {'bpm': self.settings['tempo']}
        if action == 'stopwatch':
            command = args.get('command')
            if command == 'start' and self.stopwatch_at is None:
                self.stopwatch_at = self.motion_now()
            elif command == 'stop' and self.stopwatch_at is not None:
                self.stopwatch_saved += self.motion_now()-self.stopwatch_at
                self.stopwatch_at = None
            elif command == 'reset':
                self.stopwatch_at, self.stopwatch_saved = None, 0.
            elif command not in ('start', 'stop', 'read'):
                raise DeviceError('Choose start, stop, reset or read.')
            return {'seconds': self.status()['stopwatch']}
        if action == 'focus_start':
            return super().execute('timer_start', {'seconds': self.number(args.get('minutes', 25), 1, 240)*60})
        if action == 'phone_forget':
            return super().execute('phone_connect', {'connected': False})
        if action == 'voice_state':
            state = args.get('state')
            if state not in ('idle', 'recording', 'thinking', 'speaking', 'fault'):
                raise DeviceError('Unknown voice state.')
            self.voice = state
            return {'voice': self.voice}
        if action in ('photo_capture', 'tracking_set'):
            raise DeviceError('The optional camera is not installed.')
        if action == 'alarm_add_minutes':
            from datetime import datetime, timedelta
            at = datetime.fromtimestamp(self.now(), self.zone) + timedelta(minutes=self.number(args.get('minutes'), .05, 1440))
            return super().execute('alarm_set', {'at': at.isoformat(), 'label': args.get('label', 'Alarm')})
        return super().execute(action, args)
