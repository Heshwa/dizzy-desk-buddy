import asyncio
import pytest
from aiohttp.test_utils import TestClient, TestServer
from dizzy.server import Hub, create_app


class QuotaProvider:
    async def reply(self, device, text, execute):
        raise RuntimeError('Gemini free-tier quota is exhausted. Please try again later.')


@pytest.mark.asyncio
async def test_disconnect_fails_pending_command():
    hub = Hub()
    async with TestClient(TestServer(create_app(hub))) as client:
        ws = await client.ws_connect('/device/dizzy-a')
        pending = asyncio.create_task(hub.command('dizzy-a', 'head_turn', {'degrees': 20}))
        await ws.receive_json()
        await ws.close()
        result = await pending
        assert not result['ok']
        assert 'disconnected' in result['error']


@pytest.mark.asyncio
async def test_quota_failure_restores_idle_and_reports_error():
    hub = Hub(QuotaProvider())
    actions = []
    async def command(device, action, args=None):
        actions.append((action, args))
        return {'ok': True, 'result': {}}
    hub.command = command
    result = await hub.chat('dizzy-a', 'Hello', speak=False)
    assert not result['ok']
    assert 'quota' in result['error']
    assert actions[-1] == ('voice_state', {'state': 'idle'})


@pytest.mark.asyncio
async def test_model_cannot_invoke_internal_debug_tools():
    result = await Hub().execute_tool('dizzy-a', 'simulation_quit', {})
    assert not result['ok']


@pytest.mark.asyncio
async def test_recording_controls_reject_concurrent_start_and_wrong_device():
    hub = Hub()
    class TestVoice:
        recording = None
        recording_device = None
        def start(self, device):
            import time
            time.sleep(.03)
            self.recording = object()
            self.recording_device = device
            return self.recording
    hub.voice = TestVoice()
    async def command(device, action, args=None):
        return {'ok': True, 'result': {}}
    hub.command = command
    started, other = await asyncio.gather(hub.toggle_record('dizzy-a'), hub.toggle_record('dizzy-a'))
    assert started['recording']
    assert not other['ok']
    wrong = await hub.toggle_record('dizzy-b')
    assert not wrong['ok']
    assert hub.voice.recording_device == 'dizzy-a'


@pytest.mark.asyncio
async def test_stop_acknowledges_before_transcription_and_cannot_restart_capture(tmp_path):
    finished = asyncio.Event()
    class ControlledVoice:
        recording = None
        recording_device = None
        starts = 0
        stops = 0
        def start(self, device):
            self.starts += 1
            self.recording = object()
            self.recording_device = device
            return self.recording
        def stop(self, device):
            assert self.recording_device == device
            self.stops += 1
            self.recording = None
            self.recording_device = None
            return tmp_path / 'recorded.wav'
        async def transcribe(self, path):
            await finished.wait()
            return 'Hello'
        async def speak(self, text, volume):
            pass
        def cancel(self):
            self.recording = None
            self.recording_device = None
    class ReplyProvider:
        async def reply(self, device, text, execute):
            return 'Ready.'
    hub = Hub(ReplyProvider())
    hub.voice = ControlledVoice()
    async def command(device, action, args=None):
        return {'ok': True, 'result': {}}
    hub.command = command
    async with TestClient(TestServer(create_app(hub))) as client:
        response = await client.post('/api/record', json={'device': 'dizzy-a', 'operation': 'start'})
        started = await response.json()
        assert started['recording']
        response = await client.post('/api/record', json={'device': 'dizzy-a', 'operation': 'start'})
        assert (await response.json())['session_id'] == started['session_id']
        stop_request = client.post('/api/record', json={
            'device': 'dizzy-a', 'operation': 'stop', 'session_id': started['session_id']})
        response = await asyncio.wait_for(stop_request, .5)
        stopped = await response.json()
        assert stopped['ok'] and not stopped['recording']
        assert stopped['phase'] == 'processing'
        status = await (await client.get('/api/status')).json()
        assert status['recording'] is None
        assert status['voice_requests']['dizzy-a']['phase'] == 'processing'
        response = await client.post('/api/record', json={
            'device': 'dizzy-a', 'operation': 'stop', 'session_id': started['session_id']})
        assert (await response.json())['ok']
        assert hub.voice.starts == 1 and hub.voice.stops == 1
        finished.set()
        await hub.record_tasks['dizzy-a']
        status = await (await client.get('/api/status')).json()
        assert status['voice_requests']['dizzy-a']['result']['reply'] == 'Ready.'
        response = await client.post('/api/record', json={'device': 'dizzy-a', 'operation': 'start'})
        new_recording = await response.json()
        assert new_recording['session_id'] != started['session_id']
        response = await client.post('/api/record', json={
            'device': 'dizzy-a', 'operation': 'stop', 'session_id': started['session_id']})
        assert not (await response.json())['ok']
        assert hub.voice.recording_device == 'dizzy-a'
        await client.post('/api/record', json={
            'device': 'dizzy-a', 'operation': 'stop', 'session_id': new_recording['session_id']})
        await hub.record_tasks['dizzy-a']


@pytest.mark.asyncio
async def test_stop_without_recording_never_starts_microphone():
    hub = Hub()
    result = await hub.record_control('dizzy-a', 'stop')
    assert result['ok'] and not result['recording']
    assert result['phase'] == 'idle'
    assert hub.voice.recording is None


@pytest.mark.asyncio
async def test_model_timeout_has_readable_feedback_and_restores_idle():
    class TimeoutProvider:
        async def reply(self, device, text, execute):
            raise asyncio.TimeoutError()
    hub=Hub(TimeoutProvider())
    actions=[]
    async def command(device, action, args=None):
        actions.append((action,args))
        return {'ok': True,'result':{}}
    hub.command=command
    result=await hub.chat('dizzy-a','Tell me a story',speak=False)
    assert not result['ok'] and 'too long' in result['error']
    assert actions[-1]==('voice_state',{'state':'idle'})


@pytest.mark.asyncio
@pytest.mark.parametrize('quiet,volume,notice', [(True,.5,'Quiet mode'),(False,0,'Volume is zero')])
async def test_muted_replies_explain_why_they_are_silent(quiet,volume,notice):
    class Provider:
        async def reply(self,*args):return 'Hello.'
    hub=Hub(Provider());hub.states['dizzy-a']={'quiet':quiet,'volume':volume}
    async def command(*args):return {'ok':True,'result':{}}
    hub.command=command
    class SilentVoice:
        async def speak(self,*args):raise AssertionError('Muted reply must not play')
    hub.voice=SilentVoice()
    result=await hub.chat('dizzy-a','Hello')
    assert result['ok'] and not result['spoken'] and notice in result['speech_notice']


@pytest.mark.asyncio
async def test_provider_failure_is_spoken_and_recorded_transcript_is_preserved(tmp_path):
    class BusyProvider:
        async def reply(self,*args):raise RuntimeError('Gemini is temporarily busy. Please try again.')
    hub=Hub(BusyProvider());hub.states['dizzy-a']={'quiet':False,'volume':.5}
    spoken=[];actions=[]
    async def command(device,action,args=None):
        actions.append((action,args));return {'ok':True,'result':{}}
    hub.command=command
    class Voice:
        async def transcribe(self,path):return 'Hi, how are you?'
        async def speak(self,text,volume):spoken.append(text)
    hub.voice=Voice()
    request={'id':'recording','phase':'processing'}
    result=await hub.process_recording('dizzy-a',tmp_path/'audio.wav',request)
    assert not result['ok'] and result['spoken']
    assert result['transcript']==request['transcript']=='Hi, how are you?'
    assert spoken==[result['error']]
    assert actions[-1]==('voice_state',{'state':'idle'})


@pytest.mark.asyncio
async def test_speaker_failure_does_not_claim_audio_was_played():
    class Provider:
        async def reply(self,*args):return 'Hello.'
    hub=Hub(Provider());hub.states['dizzy-a']={'quiet':False,'volume':.5}
    async def command(*args):return {'ok':True,'result':{}}
    hub.command=command
    class Voice:
        async def speak(self,*args):raise RuntimeError('Speaker unavailable')
    hub.voice=Voice()
    result=await hub.chat('dizzy-a','Hello')
    assert result['ok'] and result['reply']=='Hello.'
    assert not result['spoken'] and result['speech_error']=='Speaker unavailable'
