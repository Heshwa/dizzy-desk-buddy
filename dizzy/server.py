"""Local control panel, WebSocket device hub, and voice service."""
import asyncio
from collections import deque
import json
import os
import time
from pathlib import Path
import uuid

from aiohttp import web, WSMsgType

from .providers import GeminiProvider, OllamaProvider
from .tools import TOOL_NAMES
from .quick_actions import route as quick_route
from .voice import Voice

ROOT = Path(__file__).resolve().parents[1]


def load_env():
    path = ROOT / '.env'
    if path.exists():
        for line in path.read_text().splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip().strip('\"\'')


class Hub:
    def __init__(self, provider=None):
        self.devices = {}
        self.states = {}
        self.pending = {}
        self.logs = deque(maxlen=100)
        self.provider = provider or (OllamaProvider() if os.getenv('DIZZY_PROVIDER') == 'ollama' else GeminiProvider())
        self.voice = Voice()
        self.locks = {}
        self.speech_lock = asyncio.Lock()
        self.record_lock = asyncio.Lock()
        self.microphone_phase = 'idle'
        self.record_session = None
        self.record_requests = {}
        self.record_tasks = {}
        self.last_hardware_press = {}

    def log(self, event, **data):
        self.logs.append({'event': event, **data})

    async def command(self, device, action, args=None):
        ws = self.devices.get(device)
        if not ws or ws.closed:
            return {'ok': False, 'error': f'{device} is disconnected'}
        request_id = uuid.uuid4().hex
        future = asyncio.get_running_loop().create_future()
        self.pending[request_id] = (device, future)
        try:
            await ws.send_json({'request_id': request_id, 'action': action, 'args': args or {}})
            result = await asyncio.wait_for(future, 5)
            self.log('action', device=device, action=action, ok=result['ok'])
            return result
        except (asyncio.TimeoutError, ConnectionError, RuntimeError):
            return {'ok': False, 'error': 'Dizzy did not confirm the action'}
        finally:
            self.pending.pop(request_id, None)

    async def websocket(self, request):
        device = request.match_info['id']
        if device not in ('dizzy-a', 'dizzy-b'):
            raise web.HTTPBadRequest(text='Unknown device')
        ws = web.WebSocketResponse(heartbeat=10)
        await ws.prepare(request)
        old = self.devices.get(device)
        self.devices[device] = ws
        if old is not None:
            await old.close()
        try:
            async for msg in ws:
                if msg.type != WSMsgType.TEXT:
                    continue
                try:
                    message = json.loads(msg.data)
                    if message.get('type') == 'status':
                        self.states[device] = message['state']
                    elif message.get('type') == 'result':
                        entry = self.pending.get(message.get('request_id'))
                        if entry and entry[0] == device and not entry[1].done():
                            entry[1].set_result(message)
                    elif message.get('type') == 'event':
                        self.log('device_event', device=device, details=message)
                        if message.get('event') == 'talk_request':
                            asyncio.create_task(self.hardware_record(device))
                except (ValueError, KeyError, TypeError):
                    self.log('invalid_device_message', device=device)
        finally:
            if self.devices.get(device) is ws:
                self.devices.pop(device, None)
                for owner, future in list(self.pending.values()):
                    if owner == device and not future.done():
                        future.set_result({'ok': False, 'error': 'Dizzy disconnected during the action'})
        return ws

    async def execute_tool(self, device, name, args):
        if name not in TOOL_NAMES:
            return {'ok': False, 'error': 'This tool is unavailable'}
        result = await self.command(device, name, args)
        # Keep image bytes out of model tool responses and conversation history.
        if result.get('ok') and isinstance(result.get('result'), dict) and 'image' in result['result']:
            result = {**result, 'result': {'captured': True, 'file': result['result']['file']}}
        return result

    async def speech_feedback(self, device, text):
        waiting = time.monotonic()
        async with self.speech_lock:
            wait_ms = round((time.monotonic()-waiting)*1000)
            state = self.states.get(device, {})
            if state.get('quiet'):
                return {'spoken': False, 'speech_notice': 'Quiet mode is on. Turn it off to hear replies.'}
            if state.get('volume', .5) == 0:
                return {'spoken': False, 'speech_notice': 'Volume is zero. Raise it to hear replies.'}
            await self.command(device, 'voice_state', {'state': 'speaking'})
            try:
                await self.voice.speak(text, state.get('volume', .5))
                return {'spoken': True, 'speech_timings': {'wait_ms':wait_ms, **getattr(self.voice,'last_speech_timings',{})}}
            except Exception as exc:
                self.log('speech_error', error=str(exc))
                return {'spoken': False, 'speech_error': str(exc)}

    async def chat(self, device, text, speak=True, on_reply=None):
        if not isinstance(text, str) or not text.strip() or len(text) > 4000:
            return {'ok': False, 'error': 'Enter a request between 1 and 4000 characters'}
        lock = self.locks.setdefault(device, asyncio.Lock())
        if lock.locked():
            return {'ok': False, 'error': 'Dizzy is answering another request'}
        async with lock:
            request_started = time.monotonic()
            started = await self.command(device, 'voice_state', {'state': 'thinking'})
            if not started['ok']:
                return started
            response_route='model'
            try:
                load_env()
                direct = quick_route(text)
                if direct is not None:
                    response_route='local'
                    action, args, answer = direct
                    if action:
                        outcome = await self.execute_tool(device, action, args)
                        if not outcome.get('ok'):
                            raise RuntimeError(outcome.get('error','The device command failed.'))
                    remember=getattr(self.provider,'remember',None)
                    if remember: remember(device,text,answer)
                    response_route='local'
                else:
                    answer = await asyncio.wait_for(self.provider.reply(device, text, lambda name, args: self.execute_tool(device, name, args)), 25)
                    response_route='model'
                reply_ms=round((time.monotonic()-request_started)*1000)
                if on_reply:on_reply(answer)
                speech = await self.speech_feedback(device, answer) if speak else {'spoken': False}
                self.log('reply', device=device, text=text, reply=answer)
                return {'ok': True, 'reply': answer, 'route':response_route,
                        'timings':{'reply_ms':reply_ms, 'total_ms':round((time.monotonic()-request_started)*1000),
                                   **speech.get('speech_timings',{})},
                        'model_trace':getattr(self.provider,'last_trace',{}).get(device,{}) if response_route=='model' else {}, **speech}
            except asyncio.TimeoutError:
                message = 'The model took too long to reply. Please try again; device controls are available.'
                self.log('voice_error', device=device, error=message)
                speech = await self.speech_feedback(device, message) if speak else {}
                return {'ok': False, 'error': message, 'route':response_route,
                        'timings':{'total_ms':round((time.monotonic()-request_started)*1000)},
                        'model_trace':getattr(self.provider,'last_trace',{}).get(device,{}), **speech}
            except Exception as exc:
                self.log('voice_error', device=device, error=str(exc))
                speech = await self.speech_feedback(device, str(exc)) if speak else {}
                return {'ok': False, 'error': str(exc), 'route':response_route,
                        'timings':{'total_ms':round((time.monotonic()-request_started)*1000)},
                        'model_trace':getattr(self.provider,'last_trace',{}).get(device,{}) if response_route=='model' else {}, **speech}
            finally:
                await self.command(device, 'voice_state', {'state': 'idle'})

    async def hardware_record(self, device):
        now = time.monotonic()
        if now - self.last_hardware_press.get(device, 0) < .75:
            return
        self.last_hardware_press[device] = now
        operation = 'stop' if self.voice.recording_device == device else 'start'
        await self.record_control(device, operation)

    def recording_response(self, device):
        request = self.record_requests.get(device, {})
        return {
            'ok': True,
            'recording': self.voice.recording_device == device,
            'session_id': self.record_session,
            'job_id': request.get('id'),
            'phase': request.get('phase', 'idle'),
        }

    async def toggle_record(self, device):
        # Preserve the original endpoint for scripts that await the final reply.
        operation = 'stop' if self.voice.recording is not None else 'start'
        result = await self.record_control(device, operation)
        if result['ok'] and operation == 'stop':
            task = self.record_tasks.get(device)
            if task is not None:
                return await asyncio.shield(task)
        return result

    async def record_control(self, device, operation, session_id=None):
        if device not in ('dizzy-a', 'dizzy-b'):
            return {'ok': False, 'error': 'Unknown Dizzy'}
        if operation not in ('start', 'stop'):
            return {'ok': False, 'error': 'Choose start or stop recording'}
        if self.record_lock.locked():
            return {'ok': False, 'error': 'Microphone is starting or stopping. Please wait.'}
        async with self.record_lock:
            owner = self.voice.recording_device
            if owner and owner != device:
                return {'ok': False, 'error': 'The other Dizzy is recording. Stop it first.'}
            if operation == 'stop':
                if owner is None:
                    return self.recording_response(device)
                if session_id is not None and session_id != self.record_session:
                    return {'ok': False, 'error': 'That recording has already ended. Refresh the controls.'}
                self.microphone_phase = 'stopping'
                request = self.record_requests[device]
                try:
                    path = await asyncio.to_thread(self.voice.stop, device)
                except Exception as exc:
                    request.update(phase='done', result={'ok': False, 'error': str(exc)})
                    await self.command(device, 'voice_state', {'state': 'idle'})
                    return request['result']
                finally:
                    self.microphone_phase = 'idle'
                    self.record_session = None
                request['phase'] = 'processing'
                self.record_tasks[device] = asyncio.create_task(self.process_recording(device, path, request))
                return self.recording_response(device)
            if owner == device:
                return self.recording_response(device)
            if any(request.get('phase') == 'processing' for request in self.record_requests.values()):
                return {'ok': False, 'error': 'Dizzy is processing the previous recording. Please wait.'}
            if self.locks.get(device) and self.locks[device].locked():
                return {'ok': False, 'error': 'Dizzy is answering another request'}
            self.microphone_phase = 'starting'
            try:
                ready = await self.command(device, 'voice_state', {'state': 'listening'})
                if not ready['ok']:
                    return ready
                stream = await asyncio.to_thread(self.voice.start, device)
                self.record_session = uuid.uuid4().hex
                self.record_requests[device] = {'id': self.record_session, 'phase': 'recording'}
                self.microphone_phase = 'recording'
                asyncio.create_task(self.stop_recording_after_limit(device, stream, self.record_session))
                return self.recording_response(device)
            except Exception as exc:
                await self.command(device, 'voice_state', {'state': 'idle'})
                self.log('recording_error', error=str(exc))
                return {'ok': False, 'error': str(exc)}
            finally:
                if self.voice.recording is None:
                    self.microphone_phase = 'idle'

    async def process_recording(self, device, path, request):
        try:
            await self.command(device, 'voice_state', {'state': 'thinking'})
            transcribing = time.monotonic()
            request['stage']='transcribing'
            text = await self.voice.transcribe(path)
            transcription_ms=round((time.monotonic()-transcribing)*1000)
            self.log('transcript', device=device, text=text)
            request['transcript'] = text
            request['stage']='reply'
            result = await self.chat(device, text, on_reply=lambda answer:request.update(preview_reply=answer,stage='speaking'))
            result['transcript'] = text
            result.setdefault('timings',{})['transcription_ms']=transcription_ms
        except Exception as exc:
            result = {'ok': False, 'error': str(exc)}
            self.log('recording_error', device=device, error=str(exc))
        finally:
            await self.command(device, 'voice_state', {'state': 'idle'})
        request.update(phase='done', result=result)
        self.log('recording_result', device=device, result=result)
        return result

    async def stop_recording_after_limit(self, device, stream, session_id):
        await asyncio.sleep(30)
        if self.voice.recording is stream:
            await self.record_control(device, 'stop', session_id)


def create_app(hub=None):
    hub = hub or Hub()
    app = web.Application(client_max_size=1_000_000)

    async def home(request):
        return web.FileResponse(ROOT / 'dizzy' / 'panel.html')

    async def status(request):
        load_env()
        return web.json_response({'devices': hub.states, 'connected': list(hub.devices), 'events': list(hub.logs),
            'provider': os.getenv('DIZZY_PROVIDER', 'gemini'), 'key_configured': bool(os.getenv('GEMINI_API_KEY')),
            'recording': hub.voice.recording_device, 'microphone_phase': hub.microphone_phase,
            'recording_session': hub.record_session, 'voice_requests': hub.record_requests})

    async def action(request):
        data = await request.json()
        return web.json_response(await hub.command(data.get('device', 'dizzy-a'), data.get('action'), data.get('args', {})))

    async def chat(request):
        data = await request.json()
        return web.json_response(await hub.chat(data.get('device', 'dizzy-a'), data.get('text', ''), data.get('speak', True)))

    async def record(request):
        data = await request.json()
        device = data.get('device', 'dizzy-a')
        if data.get('operation') is not None:
            result = await hub.record_control(device, data['operation'], data.get('session_id'))
        else:
            result = await hub.toggle_record(device)
        return web.json_response(result)

    async def shutdown(app):
        for ws in list(hub.devices.values()):
            await ws.close(code=1001, message=b'Service shutting down')
        if hub.voice.recording is not None:
            await asyncio.to_thread(hub.voice.cancel)
        for task in hub.record_tasks.values():
            if not task.done():
                task.cancel()
        if hub.record_tasks:
            await asyncio.gather(*hub.record_tasks.values(), return_exceptions=True)
        close=getattr(hub.provider,'close',None)
        if close:await close()

    app.on_shutdown.append(shutdown)
    app.router.add_get('/', home)
    app.router.add_get('/api/status', status)
    app.router.add_post('/api/action', action)
    app.router.add_post('/api/chat', chat)
    app.router.add_post('/api/record', record)
    app.router.add_get('/device/{id}', hub.websocket)
    return app


if __name__ == '__main__':
    load_env()
    (ROOT / 'runtime').mkdir(exist_ok=True)
    web.run_app(create_app(), host='127.0.0.1', port=8765, shutdown_timeout=2, print=lambda s: print(s, flush=True))
