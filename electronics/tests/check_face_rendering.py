"""Compare the real sketch renderer to Webots, plus round-aperture bounds."""
from pathlib import Path
import subprocess,tempfile,sys,math
from PIL import Image
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from dizzy.face import render_face,BACKGROUND
MODES=['idle','happy','sleepy','listening','thinking','speaking','alarm','heart','goodnight','music','blink']
INK=(106,238,230)
with tempfile.TemporaryDirectory() as temp:
 folder=Path(temp);exe=folder/'faces'
 subprocess.run(['clang++','-std=c++17','-I'+str(ROOT/'electronics/tests/firmware_api'),str(ROOT/'electronics/tests/face_render.cpp'),'-o',str(exe)],check=True,capture_output=True,text=True)
 subprocess.run([str(exe),str(folder)],check=True,capture_output=True,text=True)
 unique={}
 for mode in MODES:
  count=8 if mode in ('music','speaking') else 1;unique[mode]=set()
  for phase in range(count):
   timestamp=1+phase/16 if mode=='music' else math.tau/12+phase*math.tau/(12*count) if mode=='speaking' else 1
   status=dict(expression=mode,clock='2026-11-19T13:20:00+05:30',voice=mode if mode in ('listening','thinking','speaking') else 'idle',ringing={'id':'test'} if mode=='alarm' else None,playing=mode=='music')
   ref=render_face(status,timestamp).convert('RGB');got=Image.open(folder/f'{mode}-{phase}.ppm')
   a=got.load();b=ref.load();bits=[]
   for y in range(56,156):
    for x in range(40,200):
     actual=a[x,y]==INK;expected=b[x,y]!=BACKGROUND[:3]
     assert actual==expected,(mode,phase,x,y,a[x,y],b[x,y]);bits.append(actual)
   for y in range(240):
    for x in range(240):
     if a[x,y]==INK:assert (x-119.5)**2+(y-119.5)**2<=108**2,(mode,x,y)
   unique[mode].add(bytes(bits))
 assert len(unique['speaking'])>=4,unique
 assert len(unique['music'])>=5,unique
print('PASS actual sketch artwork matches all 11 Webots states; speaking/music animate and every lit pixel fits the round safe area')
