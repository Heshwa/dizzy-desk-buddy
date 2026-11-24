"""Stop the voice service and verify device alarm audio via MQTT telemetry.

Use only with the demo running locally. Starts the service again afterward.
"""
import asyncio
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import queue
import signal
import subprocess
import sys
import time

import aiohttp
import paho.mqtt.client as mqtt

ROOT = Path(__file__).resolve().parents[1]


async def main():
    incoming = queue.Queue()
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id='dizzy-outage-check')
    client.on_connect = lambda c, u, f, r, p: c.subscribe('dizzy/demo/dizzy-a/telemetry', qos=1)
    client.on_message = lambda c, u, m: incoming.put(json.loads(m.payload))
    client.connect('127.0.0.1', 18884, 10)
    client.loop_start()
    alarm_id = None
    restarted = None
    try:
        async with aiohttp.ClientSession() as session:
            async def action(name, args=None):
                async with session.post('http://127.0.0.1:8765/api/action', json={'device': 'dizzy-a', 'action': name, 'args': args or {}}) as r:
                    result = await r.json()
                assert result['ok'], result
                return result['result']
            await action('quiet_set', {'enabled': False})
            await action('phone_connect', {'connected': True})
            await action('music_control', {'command': 'play'})
            await action('voice_state', {'state': 'thinking'})
            alarm = await action('alarm_set', {'at': (datetime.now().astimezone() + timedelta(seconds=4)).isoformat(), 'label': 'Voice outage test'})
            alarm_id = alarm['id']
            pid = int(subprocess.check_output(['lsof', '-t', '-iTCP:8765', '-sTCP:LISTEN'], text=True).strip())
            os.kill(pid, signal.SIGTERM)
            await asyncio.sleep(5)
            evidence = []
            while not incoming.empty():
                evidence.append(incoming.get())
            ringing = [s for s in evidence if s.get('ringing') and s['ringing']['id'] == alarm_id]
            assert ringing, 'Alarm state was not received over MQTT while service was stopped'
            assert ringing[-1]['alarm_audio_active'], 'Device did not activate alarm sound'
            assert ringing[-1]['voice'] == 'idle', 'Disconnected voice service left music ducking active'
            report = {'check': 'Alarm audio runs with voice service stopped; stale voice state clears', 'status': 'PASS', 'details': ringing[-1]}
    finally:
        client.disconnect()
        client.loop_stop()
        # Restart the local service even if an assertion fails.
        log = open(ROOT / 'runtime/service.log', 'a')
        restarted = subprocess.Popen([sys.executable, '-m', 'dizzy.server'], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        log.close()
        await asyncio.sleep(3)
        async with aiohttp.ClientSession() as session:
            for action, args in [('alarm_dismiss', {}), ('music_control', {'command': 'pause'}), ('voice_state', {'state': 'idle'})]:
                async with session.post('http://127.0.0.1:8765/api/action', json={'action': action, 'args': args}) as r:
                    await r.read()
        if 'report' in locals():
            (ROOT / 'reports/service-outage.json').write_text(json.dumps(report, indent=2))
            print('PASS', report['check'])


if __name__ == '__main__':
    asyncio.run(main())
