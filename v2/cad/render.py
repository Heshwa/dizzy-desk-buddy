"""Render the FreeCAD export as a labelled montage and reversible assembly animation."""
import json
from pathlib import Path
import struct
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent/'output'
KIND=np.dtype([('normal','<f4',(3,)),('triangle','<f4',(3,3)),('attrs','<u2')])
PARTS=json.loads((ROOT/'parts.json').read_text())
BG=(223,229,225)
W,H=780,680
font_path=Path('/System/Library/Fonts/Supplemental/Arial.ttf')

def font(size):
    return ImageFont.truetype(str(font_path),size) if font_path.exists() else ImageFont.load_default(size=size)

def triangles(path):
    with path.open('rb') as file:
        file.read(80)
        count=struct.unpack('<I',file.read(4))[0]
        return np.fromfile(file,KIND,count=count)['triangle'].astype(float)

def cylinder_face(x,z,rgb):
    verts=[]
    for i in range(64):
        a,b=2*np.pi*i/64,2*np.pi*(i+1)/64
        verts.append([(x,0,z),(x,22*np.cos(a),z+22*np.sin(a)),(x,22*np.cos(b),z+22*np.sin(b))])
    return np.array(verts),np.asarray(rgb)

def ellipsis_on_face(x,y,z,ry,rz):
    verts=[]
    for i in range(30):
        a,b=2*np.pi*i/30,2*np.pi*(i+1)/30
        verts.append([(x,y,z),(x,y+ry*np.cos(a),z+rz*np.sin(a)),(x,y+ry*np.cos(b),z+rz*np.sin(b))])
    return np.array(verts)

FIGURES=[]
for part in PARTS:
    shape=triangles(ROOT/'stl'/f"{part['part']}.stl")
    FIGURES.append((part,shape,np.round(np.array(part['color'])*255)))
panel,color=cylinder_face(34.3,162,(15,25,35))
FIGURES.append(({'part':'Screen','explosion_axis':[1,0,0],'link':'pitch'},panel,color))
for y in (-8,8):
    FIGURES.append(({'part':'Eyes','explosion_axis':[1,0,0],'link':'pitch'},
        ellipsis_on_face(34.6,y,164,3.7,5.5),np.array([126,231,204])))

def transform(direction):
    direction=np.asarray(direction,dtype=float)
    direction/=np.linalg.norm(direction)
    side=np.cross((0,0,1),direction);side/=np.linalg.norm(side)
    up=np.cross(direction,side)
    return np.array([side,up,direction]).T

def render(entries,label,direction=(.94,-.54,.31),frame_size=(W,H),explode=0,individual=False):
    matrix=transform(direction)
    prepared=[]
    foreground=[]
    for slot,(part,geometry,color) in enumerate(entries):
        axis=np.asarray(part['explosion_axis'],dtype=float)
        distance=explode*(28+slot%5*7)
        if part['link']=='pitch' and part['part'] not in ('Screen','Eyes'):
            axis=axis+np.array([0,0,.6])
        if part['part'] in ('Screen','Eyes'):
            distance=explode*73
        if part['part'] in ('Eyes','Screen') and direction[0] <= 0:
            continue
        shape=(geometry+axis*distance)@matrix
        normals=np.cross(shape[:,1]-shape[:,0],shape[:,2]-shape[:,0])
        lengths=np.linalg.norm(normals,axis=1)
        safe=lengths>1e-8
        normals=normals[safe]/lengths[safe,None]
        shape=shape[safe]
        light=np.clip(normals@np.array([-.28,.43,.85]),-.3,1)
        shades=np.clip(color*(.59+.42*light[:,None])+12,0,255).astype('uint8')
        if part['part']=='Eyes':
            foreground.append((shape,shades))
        else:
            prepared.append((shape,shades))
    v=np.concatenate([a for a,_ in prepared])
    c=np.concatenate([b for _,b in prepared])
    lo=v.min(axis=(0,1));hi=v.max(axis=(0,1))
    w,h=frame_size
    scale=min((w-52)/(hi[0]-lo[0]+5),(h-57)/(hi[1]-lo[1]+5)) if individual else 2.50
    center=(lo+hi)/2
    xy=v[:,:,:2]*np.array([scale,-scale])
    xy+=np.array([w/2-center[0]*scale,h/2+center[1]*scale+8])
    xy=np.rint(xy).astype(int)
    target=Image.new('RGB',frame_size,BG)
    pen=ImageDraw.Draw(target)
    for i in np.argsort(v[:,:,2].mean(axis=1)):
        pts=tuple(map(tuple,xy[i]))
        fill=tuple(c[i])
        pen.polygon(pts,fill=fill)
    for eye,colors in foreground:
        points=eye[:,:,:2]*np.array([scale,-scale])
        points+=np.array([w/2-center[0]*scale,h/2+center[1]*scale+8])
        for sector,color in zip(np.rint(points).astype(int),colors):
            pen.polygon(tuple(map(tuple,sector)),fill=tuple(color))
    pen.text((14,12),label,fill=(33,55,59),font=font(16 if individual else 23))
    return target

physical=[a for a in FIGURES if a[0]['link'] not in ('dock','calibration')]
externals=[a for a in physical if not any(marker in a[0]['part'] for marker in ('cassette','clip','Backplane','drawer','support','yoke'))]
standing=render(externals,'Dizzy V2 · standing assembly')
standing.save(ROOT/'standing.png')
render(externals,'Dizzy V2 · rear',direction=(-.94,-.54,.31)).save(ROOT/'rear.png')
render(externals,'Dizzy V2 · front',direction=(1,.02,.06)).save(ROOT/'front.png')
frames=[]
for value in np.r_[np.linspace(1,0,13),[0,0,0],np.linspace(0,1,13)]:
    frames.append(render(physical,'Dizzy V2 · assembly',explode=float(value)).convert('P',palette=Image.Palette.ADAPTIVE))
frames[0].save(ROOT/'assembly.gif',save_all=True,append_images=frames[1:],duration=92,loop=0,optimize=False)
cards=[]
for part,tri,color in FIGURES[:len(PARTS)]:
    card=render([(part,tri,color)],part['part'].replace('_',' '),frame_size=(278,228),individual=True)
    card.save(ROOT/'isolated'/f"{part['part']}.png")
    cards.append(card)
for start in range(0,len(cards),15):
    page=Image.new('RGB',(1390,696),(209,214,208))
    for slot,card in enumerate(cards[start:start+15]):
        page.paste(card,(slot%5*278,slot//5*232))
    page.save(ROOT/f'isolated-parts-{start//15+1}.png')
