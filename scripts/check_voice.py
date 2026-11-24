"""Exercise a real microphone capture using a spoken phrase from the Mac speaker."""
import asyncio
import json
from pathlib import Path
import sys

import aiohttp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dizzy.voice import Voice


async def main():
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as client:
        async def post(endpoint, data):
            async with client.post('http://127.0.0.1:8765' + endpoint, json=data) as response:
                result = await response.json()
                assert result['ok'], result
                return result
        await post('/api/action', {'action': 'head_turn', 'args': {'degrees': 0}})
        await post('/api/action', {'action': 'alarm_dismiss'})
        await post('/api/action', {'action': 'music_control', 'args': {'command': 'pause'}})
        started = await post('/api/record', {'device': 'dizzy-a'})
        assert started.get('recording'), started
        await asyncio.sleep(.5)
        try:
            await Voice().speak('Look left.', .65)
            await asyncio.sleep(.5)
        finally:
            result = await post('/api/record', {'device': 'dizzy-a'})
        async with client.get('http://127.0.0.1:8765/api/status') as response:
            status = await response.json()
        transcript = next(e['text'] for e in reversed(status['events']) if e['event'] == 'transcript' and e['device'] == 'dizzy-a')
        assert 'left' in transcript.lower(), transcript
        assert status['devices']['dizzy-a']['target_degrees'] < 0
        assert 'speech_error' not in result, result
        evidence = {'check': 'Real microphone to whisper to Gemini tool to Piper speaker', 'status': 'PASS', 'spoken_test_phrase': 'Look left.', 'transcript': transcript, 'reply': result['reply'], 'head_target': status['devices']['dizzy-a']['target_degrees']}
        (ROOT / 'reports/microphone-check.json').write_text(json.dumps(evidence, indent=2))
        print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as exc:
        (ROOT / 'reports/voice-loopback.json').write_text(json.dumps({'check': 'Automatic speaker-to-microphone loopback', 'status': 'FAIL', 'details': str(exc)}, indent=2))
        raise
