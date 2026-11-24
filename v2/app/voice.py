"""The same V2 action contract serves recorded speech and typed requests."""
import asyncio
import io
import json
import os
import re
import tempfile
import wave
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path

import aiohttp

from dizzy.providers import GeminiProvider
from dizzy.quick_actions import route
from dizzy.tools import SYSTEM, TOOLS, number, text, tool
from dizzy.voice import Voice

ROOT = Path(__file__).resolve().parents[2]
SYSTEM_V2 = SYSTEM.replace('Camera images come from a simulation.', '') + (
    '\nThis is Dizzy V2. The camera, NFC and distance modules are optional and unavailable in this build. '
    'Walking and standing dances require local arming. Never present a queued action as completed.'
)
TOOLS_V2 = [t for t in TOOLS if t['name'] not in ('photo_capture', 'tracking_set')] + [
    tool('head_pitch', 'Tilt the head up (positive) or down (negative).', {'degrees': number('-20 to 25')}, ['degrees']),
    tool('arm_lift', 'Lift either arm and return to rest.', {'side': text('left or right')}, ['side']),
    tool('motion_play', 'Play a motion. Standing moves require local arming.',
        {'name': {'type':'string', 'enum':['wave','sway','heel','bounce','shuffle']}}, ['name']),
    tool('focus_start', 'Start a local focus timer.', {'minutes': number('1 to 240, default 25')}),
]
ALLOWED = {t['name'] for t in TOOLS_V2}


class Gemini(GeminiProvider):
    def config(self, model):
        from google.genai import types
        config = super().config(model)
        config.system_instruction = config.system_instruction.replace(SYSTEM, SYSTEM_V2)
        config.tools = [types.Tool(function_declarations=[types.FunctionDeclaration(**t) for t in TOOLS_V2])]
        return config


class Ollama:
    def __init__(self):
        self.history = {}

    async def reply(self, device, prompt, execute):
        history = self.history.get(device, [])
        messages = [{'role':'system','content':SYSTEM_V2}, *history, {'role':'user','content':prompt}]
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
            for _ in range(6):
                async with session.post(os.getenv('DIZZY_OLLAMA_URL','http://127.0.0.1:11434')+'/api/chat',
                    json={'model':os.getenv('DIZZY_OLLAMA_MODEL','qwen3:4b'), 'messages':messages,
                        'tools':[{'type':'function','function':t} for t in TOOLS_V2], 'stream':False}) as response:
                    response.raise_for_status()
                    message = (await response.json())['message']
                messages.append(message)
                if not message.get('tool_calls'):
                    answer = message.get('content', '').strip()
                    if not answer:
                        raise RuntimeError('Ollama returned an empty reply.')
                    self.history[device] = (history + [{'role':'user','content':prompt},
                        {'role':'assistant','content':answer}])[-8:]
                    return answer
                for call in message['tool_calls']:
                    fn = call['function']
                    result = await execute(fn['name'], fn.get('arguments', {}))
                    messages.append({'role':'tool','tool_name':fn['name'],'content':json.dumps(result)})
        raise RuntimeError('Please try a shorter request.')


class Speech(Voice):
    def __init__(self):
        super().__init__()
        self.lock = asyncio.Lock()

    async def pcm_to_text(self, pcm):
        if not 3200 <= len(pcm) <= 960000 or len(pcm) % 2:
            raise RuntimeError('Record between 0.1 and 30 seconds of mono 16 kHz audio.')
        with tempfile.TemporaryDirectory(prefix='dizzy-v2-') as folder:
            path = Path(folder) / 'microphone.wav'
            with wave.open(str(path),'wb') as output:
                output.setparams((1,2,16000,0,'NONE','not compressed'))
                output.writeframes(pcm)
            return await self.transcribe(path)

    async def render(self, answer):
        async with self.lock:
            def synthesize():
                from piper import PiperVoice
                if self._piper is None:
                    self._piper = PiperVoice.load(str(ROOT / 'models/en_US-lessac-medium.onnx'))
                buffer = io.BytesIO()
                with wave.open(buffer,'wb') as output:
                    self._piper.synthesize_wav(answer, output)
                return buffer.getvalue()
            return await asyncio.to_thread(synthesize)


def shortcut(prompt):
    normalized = prompt.casefold().strip(' .?!')
    if re.fullmatch(r'set (?:an? )?alarm (?:for|at) (?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|0?[1-9]|1[0-2])(?::[0-5]\d)?',normalized):
        return None, {}, 'Do you mean AM or PM?'
    clock = re.fullmatch(r'set (?:an? )?alarm (?:for|at) (one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|0?[1-9]|1[0-2])(?::([0-5]\d))?\s*(am|pm|a\.m|p\.m|morning|evening)', normalized)
    if clock:
        words = 'one two three four five six seven eight nine ten eleven twelve'.split()
        hour = int(clock[1]) if clock[1].isdigit() else words.index(clock[1])+1
        hour = hour%12 + (12 if clock[3][0]=='p' or clock[3]=='evening' else 0)
        now = datetime.now(ZoneInfo('Asia/Kolkata'))
        due = now.replace(hour=hour, minute=int(clock[2] or 0), second=0, microsecond=0)
        if due <= now:
            due += timedelta(days=1)
        return 'alarm_set', {'at':due.isoformat()}, f'Alarm set for {due.strftime("%I:%M %p on %A").lstrip("0")}.'
    if normalized in ('look up','look down'):
        return 'head_pitch', {'degrees':20 if normalized.endswith('up') else -15}, 'Looking '+normalized.split()[-1]+'.'
    if normalized in ('send a wave','send good night'):
        return 'gesture_send', {'gesture':'wave' if normalized.endswith('wave') else 'goodnight'}, 'Gesture queued for delivery.'
    match = re.fullmatch(r'(?:set|start) (?:a )?timer for (\d+) (seconds?|minutes?)',normalized)
    if match:
        return 'timer_start', {'seconds':int(match[1])*(60 if match[2].startswith('minute') else 1)}, f'Timer set for {match[1]} {match[2]}.'
    return route(prompt)
