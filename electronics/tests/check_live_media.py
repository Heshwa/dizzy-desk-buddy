"""Check Webots snapshot and typed-request Piper playback; no microphone/webcam capture."""
import asyncio,base64,json,sys,time,wave,shutil
from pathlib import Path
import aiohttp,numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
async def main():
 async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=40)) as s:
  async def action(name,args=None):
   async with s.post('http://127.0.0.1:8765/api/action',json={'action':name,'args':args or {}}) as r:d=await r.json()
   assert d['ok'],d
   return d['result']
  await action('tracking_set',{'enabled':False});await action('head_turn',{'degrees':0});await action('target_move',{'x':-.095})
  await asyncio.sleep(1)
  photo=await action('photo_capture');image=base64.b64decode(photo['image']);folder=ROOT/'electronics/reports';(folder/'camera-simulation-2026-11-19.png').write_bytes(image)
  from PIL import Image
  im=Image.open(folder/'camera-simulation-2026-11-19.png');assert np.asarray(im).std()>1
  started=time.time()
  async with s.post('http://127.0.0.1:8765/api/chat',json={'text':'Who developed you?','speak':True}) as r:voice=await r.json()
  assert voice.get('ok') and voice.get('spoken'),voice
  assert 'Heshwa' in voice['reply'] and 'Yoga' in voice['reply'],voice
  paths=[p for p in (ROOT/'runtime').glob('reply-*.wav') if p.stat().st_mtime>=started]
  assert paths,'No new synthesized audio file'
  audio=max(paths,key=lambda p:p.stat().st_mtime)
  with wave.open(str(audio),'rb') as wav:
   rate=wav.getframerate();duration=wav.getnframes()/rate;samples=np.frombuffer(wav.readframes(wav.getnframes()),dtype='<i2');assert duration>.3 and np.max(np.abs(samples.astype(float)))>100
  shutil.copyfile(audio,folder/'spoken-reply-2026-11-19.wav')
  result={'camera':{'status':'PASS','source':'Webots camera; no Mac camera used','size':list(im.size),'bytes':len(image)},'speech':{'status':'PASS','source':'Piper output through Mac speakers; not simulated I2S amplifier','reply':voice['reply'],'duration_seconds':round(duration,2),'sample_rate':rate,'route':voice.get('route'),'playback_completed':voice.get('spoken')}}
  (folder/'media-checks-2026-11-19.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
asyncio.run(main())
