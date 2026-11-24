"""Acceptance checks against running Webots controllers and the local service."""
import asyncio
import base64
from datetime import datetime, timedelta
import json
from pathlib import Path
import sys
import time
from zoneinfo import ZoneInfo

import aiohttp

ROOT = Path(__file__).resolve().parents[1]


async def main():
    results = []
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as client:
        async def action(name, args=None, device='dizzy-a', required=True):
            async with client.post('http://127.0.0.1:8765/api/action', json={'device': device, 'action': name, 'args': args or {}}) as response:
                result = await response.json()
            if required:
                assert result['ok'], result
                return result['result']
            return result

        async def status(device='dizzy-a'):
            return await action('status', device=device)

        async def check(name, fn):
            try:
                details = await fn()
                results.append({'check': name, 'status': 'PASS', 'details': details})
                print('PASS', name, flush=True)
            except Exception as exc:
                results.append({'check': name, 'status': 'FAIL', 'details': repr(exc)})
                print('FAIL', name, repr(exc), flush=True)

        async def wait_for(predicate, device='dizzy-a', timeout=5):
            end = time.monotonic() + timeout
            while time.monotonic() < end:
                s = await status(device)
                if predicate(s):
                    return s
                await asyncio.sleep(.15)
            raise AssertionError('Expected state did not arrive')

        async def reset():
            for device in ('dizzy-a', 'dizzy-b'):
                await action('alarm_dismiss', device=device)
                await action('timer_cancel', device=device)
                await action('quiet_set', {'enabled': False}, device)
                await action('tracking_set', {'enabled': False}, device)
                await action('head_turn', {'degrees': 0}, device)
                await action('voice_state', {'state': 'idle'}, device)
        await reset()

        async def petting():
            await action('touch', {'phase': 'tap'})
            s = await wait_for(lambda s: s['expression'] == 'happy')
            assert s['delivery'] != 'sending'
            return {'expression': s['expression'], 'delivery': s['delivery']}
        await check('Single tap pets locally', petting)

        async def gesture():
            await wait_for(lambda s: s['partner_online'])
            await action('touch', {'phase': 'tap'})
            await action('touch', {'phase': 'tap'})
            s = await wait_for(lambda s: s['delivery'] == 'delivered')
            other = await status('dizzy-b')
            assert other['expression'] == 'heart'
            return {'delivery': s['delivery'], 'partner_expression': other['expression']}
        await check('Double tap reaches the partner and is acknowledged', gesture)

        async def head():
            await action('head_turn', {'degrees': -45})
            s = await wait_for(lambda s: abs(s['measured_head_degrees'] + 45) < 1)
            invalid = await action('head_turn', {'degrees': 60}, required=False)
            assert not invalid['ok']
            await action('head_turn', {'degrees': 0})
            return {'measured_degrees': s['measured_head_degrees'], 'invalid_angle_rejected': True}
        await check('Servo reaches limit and rejects excessive angles', head)

        async def tracking():
            await action('target_move', {'x': -.18})
            await action('head_turn', {'degrees': 0})
            await asyncio.sleep(1)
            await action('tracking_set', {'enabled': True})
            await action('target_move', {'x': .04})
            s = await wait_for(lambda s: abs(s['measured_head_degrees']) > 12)
            assert abs(s['head_degrees']) <= 45
            await action('tracking_set', {'enabled': False})
            fixed = await status()
            await action('target_move', {'x': -.4})
            await asyncio.sleep(.5)
            stopped = await status()
            assert abs(stopped['target_degrees'] - fixed['target_degrees']) < .1
            await action('head_turn', {'degrees': 0})
            return {'tracked_degrees': s['measured_head_degrees'], 'recognized_targets': s['camera_objects'], 'stopped': True}
        await check('Camera follows a moving target and stops on command', tracking)

        async def photo():
            s = await action('photo_capture')
            image = base64.b64decode(s['image'])
            assert image.startswith(b'\x89PNG')
            (ROOT / 'reports' / 'camera.png').write_bytes(image)
            return {'file': s['file'], 'bytes': len(image)}
        await check('Camera captures a real simulation image', photo)

        async def music():
            await action('phone_connect', {'connected': True})
            await action('music_control', {'command': 'play'})
            a = await status()
            await action('music_control', {'command': 'next'})
            b = await status()
            assert b['track_index'] != a['track_index']
            await action('voice_state', {'state': 'speaking'})
            ducked = await status()
            assert ducked['music_gain'] < a['music_gain']
            await action('voice_state', {'state': 'idle'})
            recovered = await status()
            assert recovered['music_gain'] == a['music_gain']
            await action('phone_connect', {'connected': False})
            failure = await action('music_control', {'command': 'play'}, required=False)
            assert not failure['ok']
            return {'ducked_gain': ducked['music_gain'], 'restored_gain': recovered['music_gain'], 'disconnect_error': failure['error']}
        await check('Music playback, skipping, ducking, and disconnect errors', music)

        async def alarm():
            now = datetime.now(ZoneInfo('Asia/Kolkata'))
            created = await action('alarm_set', {'at': (now + timedelta(seconds=2)).isoformat(), 'label': 'Acceptance alarm'})
            s = await wait_for(lambda s: bool(s['ringing']))
            await action('touch', {'phase': 'tap'})
            snoozed = await status()
            assert snoozed['ringing'] is None
            assert any(a['enabled'] and a['label'] == 'Acceptance alarm' for a in snoozed['alarms'])
            for a in snoozed['alarms']:
                if a['label'] == 'Acceptance alarm':
                    await action('alarm_cancel', {'id': a['id']})
            return {'alarm_id': created['id'], 'ringing': s['ringing'], 'snoozed': True}
        await check('Alarm rings and a head tap snoozes it', alarm)

        async def quiet():
            await action('phone_connect', {'connected': True})
            await action('music_control', {'command': 'play'})
            await action('quiet_set', {'enabled': True})
            s = await status()
            assert s['music_gain'] == 0
            await action('quiet_set', {'enabled': False})
            assert (await status())['music_gain'] > 0
            await action('music_control', {'command': 'pause'})
            return {'muted_gain': s['music_gain'], 'restored': True}
        await check('Quiet mode suppresses sound and restores playback', quiet)

        async def chat(text):
            async with client.post('http://127.0.0.1:8765/api/chat', json={'text': text, 'speak': False}) as response:
                return await response.json()

        async def ambiguity():
            before = len((await status())['alarms'])
            r = await chat('Set an alarm for seven.')
            assert r['ok'], r
            assert 'am' in r['reply'].lower() and 'pm' in r['reply'].lower(), r
            assert len((await status())['alarms']) == before
            return r
        await check('Gemini asks AM or PM for an ambiguous alarm', ambiguity)

        async def llm_actions():
            details = []
            await action('phone_connect', {'connected': True})
            await action('music_control', {'command': 'play'})
            for request, predicate in [
                ('Forget the previous alarm request. Look left.', lambda s: s['target_degrees'] < 0),
                ('Pause music.', lambda s: not s['playing']),
            ]:
                pending = asyncio.create_task(chat(request))
                observed = False
                while not pending.done():
                    observed = predicate(await status()) or observed
                    await asyncio.sleep(.15)
                r = await pending
                assert r['ok'], r
                assert observed or predicate(await status()), r
                details.append({'request': request, 'reply': r['reply'], 'action_observed': True})
            for request in ('Take a photo.', 'Send a wave to the other Dizzy.'):
                r = await chat(request)
                assert r['ok'], r
                details.append({'request': request, 'reply': r['reply']})
            await wait_for(lambda s: s['delivery'] == 'delivered')
            return details
        await check('Gemini executes head, music, photo, and partner tools', llm_actions)
        await reset()
        await action('expression_set', {'expression': 'happy'})
        await action('expression_set', {'expression': 'heart'}, 'dizzy-b')
        await action('screenshot')

    (ROOT / 'reports' / 'simulation-checks.json').write_text(json.dumps(results, indent=2))
    return sum(r['status'] == 'FAIL' for r in results)


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
