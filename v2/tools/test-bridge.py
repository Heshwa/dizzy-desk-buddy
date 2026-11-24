"""Exercise the device RPC and bidirectional partner transport with a firmware stand-in."""
import asyncio
import json
import os
import tempfile
from pathlib import Path
import time

from aiohttp.test_utils import TestServer, TestClient
from v2.app.server import Bridge, create_app, PHYSICAL
from v2.app.voice import Gemini

async def main():
    headers={'Authorization':'Bearer test-rpc-token'}
    with tempfile.TemporaryDirectory() as folder:
        async with TestClient(TestServer(create_app(Bridge(Path(folder),Gemini(),'test-rpc-token')))) as c:
            assert (await c.get('/api/device/next')).status==401
            seen=[]
            async def device():
                while True:
                    env=await (await c.get('/api/device/next',headers=headers)).json()
                    assert abs(env['epoch']-time.time())<2
                    if 'id' in env:
                        seen.append(env['action'])
                        body={'id':env['id'],'response':{'ok':True,'result':env['args']}}
                        await c.post('/api/device/result',json=body,headers=headers)
                    await asyncio.sleep(.025)

            task=asyncio.create_task(device())
            async def execute(action,args=None,pet=PHYSICAL):
                response=await c.post('/api/action',json={'device':pet,'action':action,'args':args or {}})
                return await response.json()
            async def await_condition(name,pet):
                for _ in range(20):
                    status=await execute('partner_status',pet=pet)
                    assert status['ok']
                    if status['result'].get(name) in (True,'delivered'):
                        return
                    await asyncio.sleep(.08)
                raise AssertionError(status)
            try:
                await asyncio.sleep(.12)
                assert (await execute('motion_arm',{'local':True}))['ok'] is False
                target=await execute('head_turn',{'degrees':-24})
                assert target=={'ok':True,'result':{'degrees':-24}}
                await await_condition('online',PHYSICAL)
                assert (await execute('gesture_send',{'gesture':'wave'}))['ok']
                await await_condition('delivery',PHYSICAL)
                partner='dizzy-v2-partner'
                assert (await execute('gesture_send',{'gesture':'goodnight'},partner))['ok']
                await await_condition('delivery',partner)
                assert seen.count('receive_greeting')==1,seen
                print(json.dumps({'test':'PASS','hardware':'HTTP firmware stand-in',
                    'checks':['auth','local arm rejection','command acknowledgment','both directions through MQTT']},indent=2))
            finally:
                task.cancel()
                await asyncio.gather(task,return_exceptions=True)

if __name__=='__main__':
    asyncio.run(main())
