"""Check restart and MQTT retransmission against running simulation adapters."""
import asyncio
from datetime import datetime, timedelta
import json
from pathlib import Path
import time

import aiohttp
import paho.mqtt.client as mqtt

ROOT = Path(__file__).resolve().parents[1]


async def main():
    results = []
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id='dizzy-acceptance')
    client.connect('127.0.0.1', 18884, 10)
    client.loop_start()
    try:
        async with aiohttp.ClientSession() as session:
            async def action(name, args=None, device='dizzy-a'):
                async with session.post('http://127.0.0.1:8765/api/action', json={'device': device, 'action': name, 'args': args or {}}) as r:
                    data = await r.json()
                assert data['ok'], data
                return data['result']

            async def status():
                return await action('status')

            async def wait_state(predicate, timeout=8):
                end = time.monotonic() + timeout
                while time.monotonic() < end:
                    try:
                        state = await status()
                        if predicate(state): return state
                    except AssertionError:
                        pass
                    await asyncio.sleep(.2)
                raise AssertionError('Expected state did not arrive')

            await wait_state(lambda s: s['voice'] == 'idle')
            for old in (await status())['alarms']:
                if old['label'] == 'Restart test':
                    await action('alarm_cancel', {'id': old['id']})
            await action('alarm_dismiss')
            future = datetime.now().astimezone() + timedelta(seconds=8)
            alarm = await action('alarm_set', {'at': future.isoformat(), 'label': 'Restart test'})
            await action('volume_set', {'level': .35})
            await action('controller_restart')
            await asyncio.sleep(2)
            state = await wait_state(lambda s: any(a['id'] == alarm['id'] for a in s['alarms']))
            assert state['volume'] == .35
            state = await wait_state(lambda s: s['ringing'] and s['ringing']['id'] == alarm['id'], timeout=10)
            assert state['alarm_audio_active']
            await action('alarm_dismiss')
            results.append({'check': 'Controller restart preserves alarm and volume; alarm subsequently rings', 'status': 'PASS', 'details': {'alarm_id': alarm['id'], 'volume': state['volume']}})

            event = {'id': 'acceptance-' + str(time.time_ns()), 'sender': 'dizzy-b', 'gesture': 'wave', 'expires': time.time() + 10}
            client.publish('dizzy/demo/dizzy-a/gesture', json.dumps(event), qos=1)
            await wait_state(lambda s: s['expression'] == 'heart')
            saved = json.loads((ROOT / 'runtime/dizzy-a.json').read_text())
            assert event['id'] in saved['seen']
            await action('controller_restart')
            await asyncio.sleep(2)
            client.publish('dizzy/demo/dizzy-a/gesture', json.dumps(event), qos=1)
            await asyncio.sleep(.5)
            assert (await status())['expression'] in ('idle', 'sleepy')
            results.append({'check': 'Repeated MQTT gesture stays deduplicated after controller restart', 'status': 'PASS', 'details': event['id']})
            event['id'] += '-expired'
            event['expires'] = time.time() - 1
            client.publish('dizzy/demo/dizzy-a/gesture', json.dumps(event), qos=1)
            await asyncio.sleep(.5)
            assert (await status())['expression'] in ('idle', 'sleepy')
            results.append({'check': 'Expired MQTT event produces no greeting', 'status': 'PASS'})
            await action('volume_set', {'level': .5})
            await action('head_turn', {'degrees': 0})
    finally:
        client.disconnect()
        client.loop_stop()
        (ROOT / 'reports/recovery-checks.json').write_text(json.dumps(results, indent=2))
    for r in results:
        print(r['status'], r['check'])


if __name__ == '__main__':
    asyncio.run(main())
