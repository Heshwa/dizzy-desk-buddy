"""Generate ESP32 flash-resident face masks from the actual Webots renderer."""
from pathlib import Path
import sys,math,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from PIL import Image,ImageDraw
from dizzy.face import render_face,label_font,BACKGROUND,INK
OUT=ROOT/'electronics/wokwi/face_assets.h'
X,Y,W,H=40,56,160,100
MODES=['idle','happy','sleepy','listening','thinking','speaking','alarm','heart','goodnight','music','blink']
def status(mode):
 return dict(expression=mode,clock='2026-11-19T13:20:00+05:30',voice=mode if mode in ('listening','thinking','speaking') else 'idle',ringing={'id':'demo'} if mode=='alarm' else None,playing=mode=='music')
def mask(image):
 rgb=image.convert('RGB');bg=BACKGROUND[:3]
 return [[rgb.getpixel((x,y))!=bg for x in range(image.width)] for y in range(image.height)]
def packed(bits):
 h=len(bits);w=len(bits[0]);out=[]
 for row in bits:
  for x in range(0,w,8):out.append(sum((128>>i) if x+i<w and row[x+i] else 0 for i in range(8)))
 return out
frames=[];groups=[];previews=[]
closed=render_face(status('blink'),1)
for mode in MODES:
 start=len(frames);count=8 if mode in ('speaking','music') else 1
 for blink in [False,True]:
  for i in range(count):
   t=1+i/16 if mode=='music' else math.tau/12+i*math.tau/(12*count) if mode=='speaking' else 1
   image=render_face(status(mode),t)
   if blink:image.paste(closed.crop((X,Y,X+W,124)),(X,Y))
   crop=image.crop((X,Y,X+W,Y+H));frames.append(packed(mask(crop)))
   if i==0 and not blink:previews.append((mode,image))
 groups.append((start,count))
labels=['GOOD NIGHT','LISTEN','THINKING','TALKING','WAKE UP','POWER LOW','NO CLOCK']
labelbits=[]
for label in labels:
 im=Image.new('RGBA',(240,40),BACKGROUND);d=ImageDraw.Draw(im);font=label_font(21);b=font.getbbox(label);width=b[2]-b[0]
 d.text(((240-width)//2-b[0],-b[1]),label,font=font,fill=INK)
 labelbits.append(packed(mask(im)))
# Glyphs retain the Webots font and text baseline; two 1-bit label buffers cost 2400 bytes.
glyphs=[];glyphdata=[];font=label_font(34);baseline=font.getbbox('00:00')[1]
for ch in '0123456789:':
 b=font.getbbox(ch);w,h=b[2]-b[0],b[3]-b[1]
 im=Image.new('RGBA',(w,h),BACKGROUND);ImageDraw.Draw(im).text((-b[0],-b[1]),ch,font=font,fill=INK)
 glyphs.append((len(glyphdata),w,h,b[0],b[1]-baseline,round(font.getlength(ch)*64)));glyphdata.extend(packed(mask(im)))
lines=['// Generated from dizzy.face.render_face; do not hand-edit.','#pragma once','#include <stdint.h>','#include <pgmspace.h>',f'constexpr int FACE_X={X}, FACE_Y={Y}, FACE_W={W}, FACE_H={H}, FACE_STRIDE={W//8};','constexpr int LABEL_Y=169, LABEL_H=40, LABEL_BYTES=1200;','constexpr uint16_t FACE_BACKGROUND=0x0862, FACE_INK=0x6f7c;','enum FaceMode { '+', '.join('FACE_'+m.upper() for m in MODES)+', FACE_COUNT };',f'static const uint8_t FACE_FRAMES[{len(frames)}][{len(frames[0])}] PROGMEM = {{']
for frame in frames:lines.append('{'+','.join(str(v) for v in frame)+'},')
lines+=['};','struct FaceGroup { uint8_t start,count; };','static const FaceGroup FACE_GROUPS[FACE_COUNT] = {'+','.join('{%d,%d}'%g for g in groups)+'};','static const char *const FACE_NAMES[FACE_COUNT] = {'+','.join(json.dumps(m) for m in MODES)+'};',f'static const uint8_t FACE_LABELS[{len(labels)}][LABEL_BYTES] PROGMEM = {{']
for frame in labelbits:lines.append('{'+','.join(str(v) for v in frame)+'},')
lines+=['};','struct ClockGlyph { uint16_t offset; uint8_t width,height; int8_t left,top; uint16_t advance; };','static const ClockGlyph CLOCK_GLYPHS[11] = {'+','.join('{'+','.join(str(v) for v in g)+'}' for g in glyphs)+'};',f'static const uint8_t CLOCK_BITS[{len(glyphdata)}] PROGMEM = {{'+','.join(str(v) for v in glyphdata)+'};']
OUT.write_text('\n'.join(lines)+'\n')
folder=ROOT/'electronics/reports/face-previews';folder.mkdir(exist_ok=True)
for name,im in previews:im.save(folder/(name+'.png'))
# Round presentation preview with the same active aperture and bezel as the chip model.
canvas=Image.new('RGB',(264*4,300*3),'#333333');d=ImageDraw.Draw(canvas)
for i,(name,im) in enumerate(previews):
 x=(i%4)*264;y=(i//4)*300
 d.ellipse((x+2,y+2,x+261,y+261),fill='#55757c');d.ellipse((x+5,y+5,x+258,y+258),fill='#101b23')
 alpha=Image.new('L',(240,240));ImageDraw.Draw(alpha).ellipse((0,0,239,239),fill=255);canvas.paste(im.convert('RGB'),(x+12,y+12),alpha)
 d.text((x+12,y+270),name,fill='white',font=label_font(18))
canvas.save(ROOT/'electronics/reports/round-face-states.png')
print(f'{len(frames)} shared-renderer masks, {OUT.stat().st_size} source bytes; no full-frame MCU allocation.')
