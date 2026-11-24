"""Run the V2 desk demo, voice bridge, and local firmware gateway."""
import argparse
import asyncio
from collections import deque
import json
import hmac
import os
from pathlib import Path
import time
import uuid

from aiohttp import web
import paho.mqtt.client as mqtt

from dizzy.core import DeviceError
from .native import CATALOG, frame
from .pet import Pet
from .voice import ALLOWED, Gemini, Ollama, Speech, shortcut

ROOT = Path(__file__).resolve().parents[1]
PHYSICAL = 'dizzy-v2-hardware'


def load_environment():
    file = ROOT.parent / '.env'
    if file.exists():
        for line in file.read_text().splitlines():
            key, sep, value = line.partition('=')
            if sep and key.strip().isidentifier():
                os.environ.setdefault(key.strip(), value.strip().strip("'\x22"))


class Bridge:
    def __init__(self, storage, provider, token=''):
        self.pets = {name: Pet(name, storage / (name + '.json')) for name in ('dizzy-v2', 'dizzy-v2-partner')}
        self.storage = storage
        self.provider = provider
        self.speech = Speech()
        self.token = token
        self.audio = {}
        self.voice_release = {}
        self.busy = set()
        self.clarifying = {}
        self.queue = deque(maxlen=24)
        self.pending = {}
        self.physical_seen = 0.
        self.physical_status = {}
        self.last = {}
        self.telemetry_at = None
        self.telemetry = {}
        self.mqtt = []
        self.physical_pending = {}
        self.physical_ack = {}
        self.physical_inflight = set()
        self.loop = None

    @staticmethod
    def fail(message):
        return {'ok':False, 'error':message}

    async def external(self, action, args):
        if time.monotonic()-self.physical_seen > 3:
            return self.fail('The physical Dizzy is offline.')
        if len(self.queue) >= self.queue.maxlen:
            return self.fail('The robot command queue is full.')
        request_id = uuid.uuid4().hex
        future = asyncio.get_running_loop().create_future()
        self.pending[request_id] = future
        self.queue.append({'id':request_id, 'action':action, 'args':args})
        try:
            return await asyncio.wait_for(future, 6)
        except asyncio.TimeoutError:
            return self.fail('Dizzy did not acknowledge the command.')
        finally:
            self.pending.pop(request_id, None)

    async def action(self, device, action, args):
        try:
            if device == PHYSICAL:
                if action in ('floor_select', 'motion_arm', 'phone_connect', 'local_pair'):
                    return self.fail('Use the physical controls for this operation.')
                if action == 'gesture_send':
                    return self.send_physical_gesture(args)
                if action == 'partner_status':
                    online = self.pets['dizzy-v2'].partner_online
                    last = next(reversed(self.physical_ack.values()), 'idle')
                    return {'ok': True, 'result': {'online': online, 'delivery': last}}
                return await self.external(action, args)
            pet = self.pets.get(device)
            if pet is None:
                return self.fail('Unknown Dizzy.')
            result = pet.execute(action, args)
            if action in ('head_turn', 'head_pitch'):
                axis = 0 if action=='head_turn' else 1
                target = pet.target if axis==0 else pet.pitch_target
                # Voice confirmations wait for the simulated joint to reach its target.
                deadline = time.monotonic()+2
                while abs(pet.angles[axis]-target)>.15 and time.monotonic()<deadline:
                    await asyncio.sleep(.025)
                if abs(pet.angles[axis]-target)>.15:
                    return self.fail('The head did not reach the requested angle.')
                result = {'degrees':round(pet.angles[axis],1),'target_degrees':target}
            return {'ok': True, 'result': result, 'state': pet.status()}
        except (DeviceError, ValueError, TypeError) as exc:
            return self.fail(str(exc))

    def send_physical_gesture(self, args):
        gesture = args.get('gesture')
        if gesture not in ('wave', 'goodnight'):
            return self.fail('Choose wave or good night.')
        if not self.mqtt or not self.pets['dizzy-v2'].partner_online:
            return self.fail('The paired Dizzy is offline.')
        event_id = uuid.uuid4().hex
        expires = time.time()+10
        self.physical_pending[event_id] = expires
        self.physical_ack[event_id] = 'sending'
        self.mqtt[0].publish('dizzy/v2/dizzy-v2-partner/gesture', json.dumps(
            {'id':event_id,'sender':PHYSICAL,'gesture':gesture,'expires':expires}), qos=1)
        return {'ok':True, 'result':{'event_id':event_id,'delivery':'sending'}}

    async def turn(self, device, text='', pcm=None):
        if device in self.busy:
            return self.fail('Dizzy is already processing a request.')
        if device != PHYSICAL and device not in self.pets:
            return self.fail('Unknown Dizzy.')
        self.busy.add(device)
        async def state(name):
            await self.action(device,'voice_state', {'state':name})
        async def execute(name, args):
            if name not in ALLOWED:
                return self.fail('This action is unavailable to voice.')
            report = await self.action(device,name,args)
            return {key:report[key] for key in ('ok','result','error') if key in report}
        try:
            await state('thinking')
            if pcm is not None:
                text = await self.speech.pcm_to_text(pcm)
            text = text.strip()
            if not text or len(text) > 420:
                raise RuntimeError('Say or type a request of up to 420 characters.')
            pending = self.clarifying.pop(device, None)
            if pending and time.monotonic()-pending[1] < 90 and text.lower().strip(' .?!') in ('am','pm','a.m','p.m','morning','evening'):
                text = pending[0]+' '+text
            handled = shortcut(text)
            if handled:
                action, args, answer = handled
                if answer == 'Do you mean AM or PM?':
                    self.clarifying[device] = (text,time.monotonic())
                if action:
                    result = await execute(action,args)
                    if not result['ok']:
                        answer = result['error']
            else:
                answer = await self.provider.reply(device,text,execute)
            audio = await self.speech.render(answer)
            audio_id = uuid.uuid4().hex
            self.audio[audio_id] = (time.monotonic()+60, audio)
            await state('speaking')
            if device in self.pets:
                import io
                import wave
                with wave.open(io.BytesIO(audio)) as sample:
                    self.voice_release[device] = time.monotonic()+sample.getnframes()/sample.getframerate()+2
            output = {'ok':True,'text':text,'answer':answer,'audio':'/api/audio/'+audio_id}
        except Exception as exc:
            detail = str(exc)
            secret = os.getenv('GEMINI_API_KEY')
            if secret:
                detail = detail.replace(secret,'[key]')
            await state('fault')
            output = {**self.fail(detail[:360] or 'Dizzy could not process the request.'),'text':text}
        finally:
            self.busy.discard(device)
        self.last[device] = output
        return output

    def setup_mqtt(self):
        for own, other in [('dizzy-v2','dizzy-v2-partner'),('dizzy-v2-partner','dizzy-v2')]:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id=own)
            client.will_set(f'dizzy/v2/{own}/presence','false',qos=1,retain=True)
            def connected(c, _, flags, reason, properties, own=own, other=other):
                if not reason.is_failure:
                    physical_topics=[(f'dizzy/v2/{PHYSICAL}/{kind}',1) for kind in ('ack','gesture')]
                    c.subscribe([(f'dizzy/v2/{own}/gesture',1),(f'dizzy/v2/{own}/ack',1),
                        (f'dizzy/v2/{other}/presence',1)] + (physical_topics if own=='dizzy-v2' else []))
                    c.publish(f'dizzy/v2/{own}/presence','true',qos=1,retain=True)
            def message(c, _, msg, own=own, other=other):
                try:
                    data = json.loads(msg.payload)
                    self.loop.call_soon_threadsafe(self.receive,c,own,other,msg.topic,data)
                except ValueError:
                    pass
            client.on_connect,client.on_message = connected,message
            def disconnected(*_, own=own):
                self.loop.call_soon_threadsafe(setattr,self.pets[own],'partner_online',False)
            client.on_disconnect = disconnected
            client.connect_async('127.0.0.1',int(os.getenv('DIZZY_V2_MQTT_PORT','18886')),10)
            client.loop_start()
            self.mqtt.append(client)

    async def receive_on_robot(self, client, data):
        event_id=data.get('id')
        expiry=data.get('expires')
        if (not isinstance(event_id,str) or not isinstance(expiry,(int,float)) or
            not time.time()<expiry<=time.time()+15 or data.get('sender')!='dizzy-v2-partner' or
            data.get('gesture') not in ('wave','goodnight')):
            return
        if event_id in self.physical_inflight:
            return
        self.physical_inflight.add(event_id)
        try:
            memo=self.storage/'physical-gesture-seen.json'
            seen=json.loads(memo.read_text()) if memo.exists() else {}
            seen={k:v for k,v in seen.items() if v>time.time()}
            if event_id not in seen:
                result=await self.external('receive_greeting',{'gesture':data['gesture']})
                if not result.get('ok'):
                    return
                self.storage.mkdir(parents=True,exist_ok=True)
                seen[event_id]=expiry
                journal=memo.with_suffix('.tmp')
                journal.write_text(json.dumps(seen))
                journal.replace(memo)
            client.publish('dizzy/v2/dizzy-v2-partner/ack', json.dumps({'id':event_id}),qos=1)
        finally:
            self.physical_inflight.discard(event_id)

    def receive(self, client, own, other, topic, data):
        receiver, kind = topic.split('/')[-2:]
        pet = self.pets[own]
        if kind == 'presence':
            pet.partner_online = data is True
        elif kind == 'ack' and isinstance(data,dict) and isinstance(data.get('id'),str):
            if receiver == PHYSICAL:
                if self.physical_pending.pop(data['id'],0) > time.time():
                    self.physical_ack[data['id']] = 'delivered'
            else:
                pet.acknowledge(data['id'])
        elif kind == 'gesture' and receiver == PHYSICAL and isinstance(data,dict):
            asyncio.create_task(self.receive_on_robot(client,data))
        elif kind == 'gesture' and isinstance(data,dict) and data.get('sender') in (other,PHYSICAL):
            try:
                accepted = pet.receive_gesture(data)
            except (ValueError,TypeError):
                accepted = False
            if accepted:
                client.publish(f"dizzy/v2/{data['sender']}/ack",json.dumps({'id':data['id']}),qos=1)

    async def tick(self):
        while True:
            for index, pet in enumerate(self.pets.values()):
                pet.tick()
                pet.events.clear()
                deadline=self.voice_release.get(pet.device_id)
                if deadline is not None and time.monotonic()>=deadline:
                    self.voice_release.pop(pet.device_id)
                    if pet.voice=='speaking':
                        pet.voice='idle'
                while pet.outgoing and self.mqtt:
                    event = pet.outgoing.pop(0)
                    other = list(self.pets)[1-index]
                    if index==1 and time.monotonic()-self.physical_seen<3:
                        other=PHYSICAL
                    self.mqtt[index].publish(f'dizzy/v2/{other}/gesture',json.dumps(event),qos=1)
            for key,(expires,_) in list(self.audio.items()):
                if expires < time.monotonic():
                    del self.audio[key]
            for key, expires in list(self.physical_pending.items()):
                if expires < time.time():
                    self.physical_pending.pop(key)
                    self.physical_ack[key] = 'unconfirmed'
            while len(self.physical_ack) > 32:
                self.physical_ack.pop(next(iter(self.physical_ack)))
            await asyncio.sleep(.025)

    async def lifecycle(self, app):
        self.loop = asyncio.get_running_loop()
        self.setup_mqtt()
        task = asyncio.create_task(self.tick())
        try:
            yield
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            for own, client in zip(self.pets,self.mqtt):
                client.publish(f'dizzy/v2/{own}/presence','false',qos=1,retain=True)
                client.disconnect()
                client.loop_stop()
            if hasattr(self.provider,'close'):
                await self.provider.close()


def create_app(bridge):
    app = web.Application(client_max_size=1_000_000)
    app.cleanup_ctx.append(bridge.lifecycle)

    def protected(req):
        if not bridge.token or not hmac.compare_digest(req.headers.get('Authorization',''), 'Bearer '+bridge.token):
            raise web.HTTPUnauthorized()

    async def index(_):
        return web.FileResponse(ROOT/'app/index.html')

    async def catalog(_):
        return web.json_response(CATALOG[:24])

    async def status(req):
        device = req.query.get('device','dizzy-v2')
        if device == PHYSICAL:
            return web.json_response({'state':bridge.physical_status,
                'online':time.monotonic()-bridge.physical_seen < 3, 'last':bridge.last.get(device)})
        pet = bridge.pets.get(device)
        if not pet:
            raise web.HTTPNotFound()
        return web.json_response({'state':pet.status(), 'telemetry':bridge.telemetry,
            'last':bridge.last.get(device)})

    async def action(req):
        if req.remote not in ('127.0.0.1','::1'):
            protected(req)
        data = await req.json()
        return web.json_response(await bridge.action(data.get('device','dizzy-v2'), data.get('action',''),data.get('args',{})))

    async def conversation(req):
        if req.remote not in ('127.0.0.1','::1'):
            protected(req)
        data = await req.json()
        return web.json_response(await bridge.turn(data.get('device','dizzy-v2'),text=data.get('text','')))

    async def speech(req):
        if req.remote not in ('127.0.0.1','::1'):
            protected(req)
        device = req.query.get('device','dizzy-v2')
        if device == PHYSICAL:
            protected(req)
        return web.json_response(await bridge.turn(device,pcm=await req.read()))

    async def audio(req):
        item = bridge.audio.get(req.match_info['id'])
        if item is None:
            raise web.HTTPNotFound()
        return web.Response(body=item[1], content_type='audio/wav')

    async def renderer(req):
        face = int(req.query.get('id',24))
        ms = min(120000, max(0,int(req.query.get('ms',0))))
        return web.json_response(frame(face,ms))

    async def robot_next(req):
        protected(req)
        bridge.physical_seen = time.monotonic()
        while bridge.queue:
            envelope = bridge.queue.popleft()
            if envelope['id'] in bridge.pending:
                return web.json_response({**envelope,'epoch':time.time()})
        return web.json_response({'epoch':time.time()})

    async def robot_result(req):
        protected(req)
        data = await req.json()
        bridge.physical_seen = time.monotonic()
        future = bridge.pending.get(data.get('id'))
        if future and not future.done():
            future.set_result(data.get('response',{}))
        if isinstance(data.get('state'),dict):
            bridge.physical_status = data['state']
        return web.json_response({'ok':True})

    async def robot_gesture(req):
        protected(req)
        return web.json_response(bridge.send_physical_gesture(await req.json()))

    async def telemetry(req):
        if req.remote not in ('127.0.0.1','::1'):
            raise web.HTTPForbidden()
        bridge.telemetry = await req.json()
        bridge.telemetry_at = time.monotonic()
        primary=bridge.pets['dizzy-v2']
        if bridge.telemetry.get('fallen') is True and primary.leg_armed:
            primary.execute('motion_fault', {'reason':'Webots fall detected'})
        return web.json_response({'ok':True})

    app.router.add_static('/assets', ROOT.parent/'assets')
    app.add_routes([web.get('/',index),web.get('/api/catalog',catalog),web.get('/api/status',status),
        web.post('/api/action',action),web.post('/api/voice',conversation),web.post('/api/speech',speech),
        web.get('/api/audio/{id}',audio),web.get('/api/frame',renderer),web.get('/api/device/next',robot_next),
        web.post('/api/device/result',robot_result),web.post('/api/device/gesture',robot_gesture),
        web.post('/api/telemetry',telemetry)])
    return app


def main():
    load_environment()
    parser = argparse.ArgumentParser()
    parser.add_argument('--port',default=8875,type=int)
    parser.add_argument('--bind',default='127.0.0.1')
    parser.add_argument('--provider',choices=['gemini','ollama'],default='gemini')
    parser.add_argument('--storage',type=Path,default=ROOT/'.work/state')
    args = parser.parse_args()
    token = os.getenv('DIZZY_V2_DEVICE_TOKEN','')
    if args.bind not in ('127.0.0.1','::1') and not token:
        parser.error('Set DIZZY_V2_DEVICE_TOKEN before binding to the robot LAN.')
    provider = Ollama() if args.provider=='ollama' else Gemini()
    web.run_app(create_app(Bridge(args.storage,provider,token)),host=args.bind,port=args.port)


if __name__ == '__main__':
    main()
