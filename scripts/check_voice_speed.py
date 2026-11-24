import asyncio,json,time,sys
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dizzy.voice import Voice
URL='http://127.0.0.1:8765'
async def main():
 for _ in range(60):
  try:
   s=requests.get(URL+'/api/status',timeout=1).json()
   if len(s['connected'])==2:break
  except requests.RequestException:pass
  await asyncio.sleep(.2)
 report={'tests':[]}
 record=max(Path('runtime').glob('recording-*.wav'),key=lambda p:p.stat().st_mtime)
 start=time.monotonic();transcript=await Voice().transcribe(record)
 report['transcription_ms']=round((time.monotonic()-start)*1000);report['speech_detected']=bool(transcript.strip())
 for prompt in ('Who developed you?','Can you rotate your head to the right?','Tell Yoga one cheerful thought for the day.'):
  start=time.monotonic()
  result=await asyncio.to_thread(lambda:requests.post(URL+'/api/chat',json={'device':'dizzy-a','text':prompt,'speak':True},timeout=35).json())
  entry={'prompt':prompt,'elapsed_ms':round((time.monotonic()-start)*1000),**result}
  if result.get('timings'):
   t=result['timings'];entry['estimated_audio_start_ms']=t.get('reply_ms',0)+t.get('wait_ms',0)+t.get('tts_ms',0)
  report['tests'].append(entry);print(json.dumps(entry),flush=True)
  if 'developed' in prompt:
   assert result.get('ok') and 'Heshwa' in result['reply'] and 'Yoga' in result['reply'] and result.get('spoken')
  if 'rotate' in prompt:
   assert result.get('ok') and result.get('route')=='local' and result.get('spoken')
   state=requests.post(URL+'/api/action',json={'device':'dizzy-a','action':'status','args':{}}).json()['result']
   entry['measured_head_degrees']=state['measured_head_degrees'];assert abs(state['measured_head_degrees']-35)<.5
 Path('reports/voice-speed-live-checks.json').write_text(json.dumps(report,indent=2))
asyncio.run(main())
