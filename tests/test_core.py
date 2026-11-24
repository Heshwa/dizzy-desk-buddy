from datetime import datetime
import pytest
from dizzy.core import Dizzy, DeviceError


@pytest.fixture
def pet(tmp_path):
    clock = [1800000000.0]
    p = Dizzy('a', tmp_path / 'a.json', now=lambda: clock[0])
    p.test_clock = clock
    return p


def advance(pet, seconds):
    for _ in range(int(seconds * 20)):
        pet.test_clock[0] += .05
        pet.tick()


def test_tap_is_local_and_double_tap_is_one_remote_event(pet):
    pet.partner_online = True
    pet.touch('tap')
    advance(pet, .5)
    assert pet.face() == 'happy'
    assert not pet.outgoing
    pet.touch('tap')
    advance(pet, .1)
    pet.touch('tap')
    advance(pet, .5)
    assert len(pet.outgoing) == 1
    assert pet.outgoing[0]['gesture'] == 'wave'


def test_hold_and_stroke(pet):
    pet.partner_online = True
    pet.touch('down')
    advance(pet, 1.4)
    pet.touch('up')
    assert pet.outgoing[0]['gesture'] == 'goodnight'
    pet.touch('zone', 'left')
    advance(pet, .1)
    pet.touch('zone', 'right')
    assert pet.face() == 'happy'


def test_persistent_alarm_rings_once_and_snoozes(pet):
    at = datetime.fromtimestamp(pet.now() + 2, pet.zone).isoformat()
    alarm = pet.execute('alarm_set', {'at': at})
    restarted = Dizzy('a', pet.storage, pet.now)
    advance(pet, 2.1)
    restarted.tick()
    assert restarted.ringing['id'] == alarm['id']
    restarted.touch('tap')
    assert restarted.ringing is None
    assert restarted.alarms[-1]['at'] == pytest.approx(pet.now() + 300)
    assert not restarted.alarms[0]['enabled']


def test_missed_alarm_expires_after_downtime(pet):
    at = datetime.fromtimestamp(pet.now() + 1, pet.zone).isoformat()
    pet.execute('alarm_set', {'at': at})
    pet.test_clock[0] += 120
    pet.tick()
    assert pet.ringing is None
    assert not pet.alarms[0]['enabled']


def test_ducking_recovers_after_voice_and_alarm(pet):
    pet.execute('phone_connect', {'connected': True})
    pet.execute('music_control', {'command': 'play'})
    normal = pet.status()['music_gain']
    pet.execute('voice_state', {'state': 'listening'})
    assert pet.status()['music_gain'] == pytest.approx(normal * .15)
    pet.execute('voice_state', {'state': 'idle'})
    assert pet.status()['music_gain'] == normal
    pet.execute('timer_start', {'seconds': 1})
    advance(pet, 1.1)
    assert pet.status()['music_gain'] == pytest.approx(normal * .15)
    pet.execute('alarm_dismiss', {})
    assert pet.status()['music_gain'] == normal


def test_music_disconnect_and_skip(pet):
    with pytest.raises(DeviceError, match='Connect'):
        pet.execute('music_control', {'command': 'play'})
    pet.execute('phone_connect', {})
    pet.execute('music_control', {'command': 'previous'})
    assert pet.track == 2
    pet.execute('music_control', {'command': 'play'})
    pet.execute('phone_connect', {'connected': False})
    assert not pet.playing


def test_motor_limits_smooth_motion_and_return(pet):
    pet.execute('head_turn', {'degrees': -45, 'temporary': True})
    advance(pet, .1)
    assert -7 < pet.head < 0
    advance(pet, 3)
    assert pet.head == pytest.approx(0)
    with pytest.raises(DeviceError):
        pet.execute('head_turn', {'degrees': 46})


def test_tracking_stops_and_quiet_holds(pet):
    pet.execute('tracking_set', {'enabled': True})
    for _ in range(100):
        pet.test_clock[0] += .05
        pet.tick(face_offset=1)
    assert pet.head <= 45
    assert pet.head > 40
    pet.execute('tracking_set', {'enabled': False})
    target = pet.target
    pet.tick(face_offset=-1)
    assert pet.target == target
    pet.execute('quiet_set', {'enabled': True})
    assert pet.target == pet.head
    assert pet.status()['music_gain'] == 0


def test_duplicate_and_stale_gestures_survive_restart(pet):
    event = {'id': 'unique', 'gesture': 'wave', 'expires': pet.now() + 10}
    assert pet.receive_gesture(event)
    assert len(pet.events) == 1
    assert pet.receive_gesture(event)
    assert len(pet.events) == 1
    restarted = Dizzy('a', pet.storage, pet.now)
    assert restarted.receive_gesture(event)
    assert not restarted.events
    pet.test_clock[0] += 11
    assert not restarted.receive_gesture(event)


def test_offline_and_acknowledgement_timeout(pet):
    with pytest.raises(DeviceError, match='offline'):
        pet.send_gesture('wave')
    pet.partner_online = True
    event = pet.send_gesture('wave')
    pet.acknowledge(event['event_id'])
    assert pet.delivery == 'delivered'
    pet.send_gesture('wave')
    advance(pet, 11)
    assert pet.delivery == 'unconfirmed'


@pytest.mark.parametrize('action,args', [
    ('head_turn', {'degrees': float('nan')}),
    ('volume_set', {'level': 4}),
    ('timer_start', {'seconds': -1}),
    ('quiet_set', {'enabled': 'false'}),
    ('tracking_set', {'enabled': 'yes'}),
    ('alarm_set', {'at': 'seven'}),
    ('alarm_cancel', {'id': 'missing'}),
    ('not_a_tool', {}),
])
def test_invalid_actions_fail_explicitly(pet, action, args):
    with pytest.raises(DeviceError):
        pet.execute(action, args)


def test_idle_sleep_and_music_expressions(pet):
    assert pet.face() == 'idle'
    advance(pet, 31)
    assert pet.face() == 'sleepy'
    pet.execute('phone_connect', {'connected': True})
    pet.execute('music_control', {'command': 'play'})
    assert pet.face() == 'music'


def test_weekly_alarm_advances_across_downtime(pet):
    first = datetime.fromtimestamp(pet.now() + 1, pet.zone)
    alarm = pet.execute('alarm_set', {'at': first.isoformat(), 'weekdays': [first.weekday()]})
    advance(pet, 1.1)
    assert pet.ringing['id'] == alarm['id']
    assert pet.alarms[0]['at'] == pytest.approx(first.timestamp() + 7 * 86400)
    pet.execute('alarm_dismiss', {})
    pet.test_clock[0] += 8 * 86400
    pet.tick()
    assert pet.ringing is None
    assert pet.alarms[0]['enabled']
    assert pet.alarms[0]['at'] > pet.now()


def test_stroke_release_cannot_send_a_remote_greeting(pet):
    pet.partner_online = True
    pet.touch('tap')
    pet.touch('down')
    pet.touch('zone', 'left')
    advance(pet, .15)
    pet.touch('zone', 'right')
    pet.touch('up')
    advance(pet, .5)
    assert pet.face() == 'happy'
    assert not pet.outgoing
    assert pet.tap_at is None


def test_holding_after_a_stroke_does_not_send_goodnight(pet):
    pet.partner_online = True
    pet.touch('down')
    pet.touch('zone', 'left')
    advance(pet, .15)
    pet.touch('zone', 'right')
    advance(pet, 1.5)
    pet.touch('up')
    assert not pet.outgoing


@pytest.mark.parametrize('pose',['wave','hello','lift','happy','goodnight'])
def test_shoulder_gestures_are_bounded_smooth_and_return(pet,pose):
    pet.execute('arms_pose',{'pose':pose})
    maximum=0
    previous=list(pet.arms)
    for _ in range(180):
        advance(pet,.05)
        assert all(0<=v<=120 for v in pet.arms)
        assert all(abs(a-b)<=3.251 for a,b in zip(pet.arms,previous))
        maximum=max(maximum,*pet.arms)
        previous=list(pet.arms)
    assert maximum>=20
    assert pet.arms==[0,0] and pet.arm_pose=='rest'


def test_arm_bad_pose_quiet_dedup_and_alarm_priority(pet):
    with pytest.raises(DeviceError):pet.execute('arms_pose',{'pose':'spin'})
    pet.execute('quiet_set',{'enabled':True})
    pet.touch('stroke')
    assert all(left==right==0 for _,left,right in pet.arm_sequence)
    pet.execute('quiet_set',{'enabled':False})
    event={'id':'wave-one','gesture':'wave','expires':pet.now()+10}
    pet.receive_gesture(event)
    advance(pet,1)
    sequence=list(pet.arm_sequence)
    pet.receive_gesture(event)
    assert pet.arm_sequence==sequence
    pet.ringing={'id':'test','label':'test'}
    advance(pet,2)
    assert pet.arms==[0,0] and not pet.arm_sequence
