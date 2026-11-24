"""Integrated Mac simulator checks. Cloud checks run only with --live."""
import argparse
import asyncio
import io
import json
import wave
from pathlib import Path
from datetime import datetime, timedelta

import aiohttp
import numpy as np
from v2.app.voice import Speech

async def main(url, live):
    items=[]
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
        async def get(path):
            async with session.get(url+path) as r:
                r.raise_for_status()
                return await r.json()
        async def post(path, payload=None, pcm=None):
            async with session.post(url+path,json=payload if pcm is None else None,
                data=pcm,headers={'Content-Type':'application/octet-stream'} if pcm is not None else None) as r:
                r.raise_for_status()
                return await r.json()
        async def action(name,args=None,ok=True):
            r=await post('/api/action',{'action':name,'args':args or {}})
            assert r['ok']==ok, r
            return r.get('state',r)
        async def check(label, func):
            try:items.append({'check':label,'test':'PASS','data':await func()})
            except Exception as exc:items.append({'check':label,'test':'FAIL','data':str(exc)})
        async def face():
            catalog=await get('/api/catalog')
            assert len({x['name'] for x in catalog})==24
            assert len({x['style'] for x in catalog})==3
            shots=[]
            for i in range(24):
                starts=await get(f'/api/frame?id={i}&ms=200')
                fin=await get(f'/api/frame?id={i}&ms=460')
                assert starts!=fin and len(starts)>8
                shots.append(tuple(tuple(x) for x in starts))
            assert len(set(shots))==24
            await action('favorites_set',{'ids':[2,8,17]})
            await action('reaction_assign',{'event':'pet','ids':[2,8,17]})
            winners=[]
            for _ in range(3):
                await action('touch',{'phase':'stroke'})
                winners.append((await get('/api/status'))['state']['face'])
            assert winners==[2,8,17],winners
            assert await get('/api/frame?id=24&ms=1000')==await get('/api/frame?id=24&ms=1400')
            return {'reactions':len(shots),'pet_rotation':winners}
        await check('24-rendered-reactions and multi-selection',face)
        async def offline():
            at=(datetime.now().astimezone()+timedelta(seconds=3)).isoformat()
            await action('alarm_set',{'at':at,'label':'Demo test'})
            await asyncio.sleep(3.1)
            assert (await get('/api/status'))['state']['ringing']['label']=='Demo test'
            await action('touch',{'phase':'tap'})
            assert not (await get('/api/status'))['state']['ringing']
            await action('timer_start',{'seconds':1})
            await asyncio.sleep(1.1)
            assert (await get('/api/status'))['state']['ringing']['id']=='timer'
            await action('alarm_dismiss')
            return 'Alarm and timer rang without a provider call; touch snoozed.'
        await check('Local alarm, touch snooze and timer',offline)
        async def pair():
            for _ in range(20):
                if (await get('/api/status'))['state']['partner_online']:break
                await asyncio.sleep(.1)
            await action('gesture_send',{'gesture':'wave'})
            await asyncio.sleep(.3)
            assert (await get('/api/status'))['state']['delivery']=='delivered'
            assert (await get('/api/status?device=dizzy-v2-partner'))['state']['face'] in (7,15,23)
            await action('gesture_send',{'gesture':'goodnight'})
            await asyncio.sleep(.3)
            assert (await get('/api/status'))['state']['delivery']=='delivered'
            return 'Both events acknowledged through local Mosquitto.'
        await check('MQTT partner wave and good night',pair)
        async def motion():
            await action('motion_play',{'name':'shuffle'},ok=False)
            await action('floor_select',{'enabled':True})
            await action('motion_arm',{'local':False},ok=False)
            await action('motion_arm',{'local':True})
            await action('motion_play',{'name':'sway'})
            await asyncio.sleep(.7)
            assert (await get('/api/status'))['state']['angles'][6]!=0
            await action('motion_fault',{'reason':'Fall fixture'})
            await action('motion_play',{'name':'shuffle'},ok=False)
            await action('motion_arm',{'local':True})
            await action('floor_select',{'enabled':False})
            await action('head_pitch',{'degrees':26},ok=False)
            return 'Local arm, physical fall fixture, lockout, and joint limits exercised.'
        await check('Motion arming and fault lockout',motion)
        async def music():
            await action('phone_forget')
            await action('music_control',{'command':'play'},ok=False)
            await action('phone_connect',{'connected':True})
            await action('volume_set',{'level':.65})
            assert (await action('music_control',{'command':'play'}))['music_gain']==.65
            await action('music_control',{'command':'next'})
            duck=await action('voice_state',{'state':'speaking'})
            assert abs(duck['music_gain']-.0975)<.001
            full=await action('voice_state',{'state':'idle'})
            assert full['music_gain']==.65
            return {'ducked':duck['music_gain'],'restored':full['music_gain']}
        await check('Simulated phone and music ducking',music)
        async def voice():
            q=await post('/api/voice',{'text':'Set an alarm for seven'})
            assert q['ok'] and 'AM or PM' in q['answer'],q
            follow=await post('/api/voice',{'text':'PM'})
            assert follow['ok'] and '7:00 PM' in follow['answer'],follow
            await action('voice_state',{'state':'idle'})
            voice=Speech()
            output=await voice.render('Look left.')
            with wave.open(io.BytesIO(output),'rb') as wav:
                raw=np.frombuffer(wav.readframes(wav.getnframes()),dtype='<i2')
                resampled=np.interp(np.arange(0,len(raw),wav.getframerate()/16000),np.arange(len(raw)),raw).astype('<i2')
            r=await post('/api/speech',pcm=resampled.tobytes())
            assert r['ok'] and 'look left' in r['text'].casefold() and r['audio'] and 'left' in r['answer'].casefold(),r
            assert abs((await get('/api/status'))['state']['angles'][0]+35)<1
            async with session.get(url+r['audio']) as clip:
                assert (await clip.read())[:4]==b'RIFF'
            await action('voice_state',{'state':'idle'})
            return {'whisper':r['text'],'reply':r['answer'],'fixture':'Piper audio fed to real Whisper; no microphone'}
        await check('Whisper speech input and verified action with Piper reply',voice)
        async def live_llm():
            a=await post('/api/voice',{'text':'Give me one tiny fact about the Moon.'})
            assert a['ok'] and a['audio'],a
            b=await post('/api/voice',{'text':'Turn your head 24 degrees to the right and tell me the angle.'})
            assert b['ok'] and b['audio'],b
            state=(await get('/api/status'))['state']
            assert abs(state['angles'][0]-24)<1 and '24' in b['answer'], b
            return {'answer':a['answer'],'tool_reply':b['answer']}
        if live:await check('Live model conversation and tool call',live_llm)
    print(json.dumps(items,indent=2))
    return any(row['test']=='FAIL' for row in items)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--url',default='http://127.0.0.1:8892')
    parser.add_argument('--live',action='store_true')
    args=parser.parse_args()
    raise SystemExit(asyncio.run(main(args.url,args.live)))
