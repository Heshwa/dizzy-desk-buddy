"""Draw the dimensioned assembly allowance views used for the fit review."""
from pathlib import Path
import sys
import math
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dizzy import design as d

image=Image.new('RGB',(1500,900),'#eef3f5'); draw=ImageDraw.Draw(image)
font=ImageFont.load_default(size=19); title=ImageFont.load_default(size=27)
draw.text((35,25),'Dizzy · component layout',font=title,fill='#18343c')
draw.text((35,65),'Millimetres · reserved assembly volumes · verify actual boards before manufacturing',font=font,fill='#49636b')
colours=['#83cfc6','#edc88a','#a6bbdf','#c2b3dc','#db9ab0','#96c7a3','#b7c8cf','#f0b894','#d3c99d','#98bfd1']
scale=2.9

def frame(left,heading):
 draw.rounded_rectangle((left,110,left+460,850),radius=20,fill='white',outline='#cfdbdf',width=2)
 draw.text((left+20,128),heading,font=title,fill='#18343c')

def component_rect(component,axes,origin,colour):
 a,b=axes;cx,cy=origin;centre=component['center'];size=component['size']
 bounds=(cx+(centre[a]-size[a]/2)*scale,cy-(centre[b]+size[b]/2)*scale,
         cx+(centre[a]+size[a]/2)*scale,cy-(centre[b]-size[b]/2)*scale)
 draw.rectangle(bounds,fill=colour,outline='#36545e',width=2)

def legend(left,group):
 for i,name in enumerate(group):
  x=left+20;y=560+i*26
  draw.rectangle((x,y+3,x+14,y+17),fill=colours[i%len(colours)],outline='#36545e')
  draw.text((x+23,y),name.replace('_',' '),font=font,fill='#36545e')

frame(20,'Head · side section')
cx,cy=250,350; w,h=d.HEAD_SIZE[1],d.HEAD_SIZE[2]
outline=[(w/2*math.cos(2*math.pi*i/256),h/2*math.sin(2*math.pi*i/256)) for i in range(256)]
for axis,minimum in ((0,d.HEAD_FRONT_Y),(1,d.HEAD_BOTTOM_Z)):
 clipped=[]
 for a,b in zip(outline,outline[1:]+outline[:1]):
  if a[axis]>=minimum:clipped.append(a)
  if (a[axis]>=minimum)!=(b[axis]>=minimum):
   t=(minimum-a[axis])/(b[axis]-a[axis]);clipped.append(tuple(x+(y-x)*t for x,y in zip(a,b)))
 outline=clipped
draw.polygon([(cx+y*scale,cy-z*scale) for y,z in outline],outline='#6c858e',width=5)

for i,c in enumerate(d.HEAD_KEEPOUTS.values()):component_rect(c,(1,2),(cx,cy),colours[i])
draw.text((45,510),'Front (left)    curved shell, 69 mm deep',font=font,fill='#49636b');legend(20,d.HEAD_KEEPOUTS)
draw.text((45,690),'75 mm camera flex routes to upper lens.',font=font,fill='#49636b')
draw.text((45,725),'LCD PCB bound is provisional.',font=font,fill='#49636b')
frame(520,'Torso + shoulders · front')
cx,cy=750,350
points=[]
for i in range(181):
 t=2*math.pi*i/180;c=math.cos(t)
 points.append((cx+d.BODY_RADII[0]*(1-.22*c)*math.sin(t)*scale,cy-d.BODY_RADII[2]*c*scale))
draw.line(points,fill='#6c858e',width=5)
for sign in (-1,1):
 draw.rounded_rectangle((cx+(sign*36-20)*scale,cy-(94+15-d.BODY_CENTER_Z)*scale,cx+(sign*36+20)*scale,cy-(94-15-d.BODY_CENTER_Z)*scale),radius=14,outline='#ba9179',width=3)
body_parts={**d.BODY_KEEPOUTS,**d.SHOULDER_KEEPOUTS}
for i,c in enumerate(body_parts.values()):component_rect(c,(0,2),(cx,cy+d.BODY_CENTER_Z*scale),colours[i])
legend(520,body_parts)
draw.text((545,740),'Front projection; depth differs by part.',font=font,fill='#49636b')
draw.text((545,770),'18 assembly envelopes checked in 3D.',font=font,fill='#49636b')
frame(1020,'Seated hips · top projection')
cx,cy=1250,350;r=d.HIP_RADII[0]*scale
ry=d.HIP_RADII[1]*scale
draw.ellipse((cx-r,cy-ry,cx+r,cy+ry),outline='#6c858e',width=5)
for i,c in enumerate(d.BASE_KEEPOUTS.values()):component_rect(c,(0,1),(cx,cy),colours[i%len(colours)])
legend(1020,d.BASE_KEEPOUTS)
draw.text((35,867),'Physical fit, cable bends, torque, audio quality and touch sensitivity remain prototype checks.',font=font,fill='#49636b')
image.save(ROOT/'reports/component-layout.png')
