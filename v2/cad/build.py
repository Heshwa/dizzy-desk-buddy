"""Rebuild the first V2 parametric fit study in millimetres."""
import json
from pathlib import Path
import sys
import FreeCAD as App
import Part
import MeshPart

V = App.Vector
ROOT = Path(__file__).resolve().parent
OUT = ROOT/'output'
for directory in ('stl','step','isolated','webots'):
    (OUT/directory).mkdir(parents=True,exist_ok=True)
IVORY=(.88,.82,.70)
CLAY=(.71,.32,.23)
INK=(.09,.16,.18)
CARRIER=(.27,.50,.48)
MANIFEST=json.loads((ROOT/'components.json').read_text())
DOC=App.newDocument('Dizzy_V2')
PRINT=DOC.addObject('App::DocumentObjectGroup','Printable')
BOARDS=DOC.addObject('App::DocumentObjectGroup','Components')
GUIDES=DOC.addObject('App::DocumentObjectGroup','Keepouts')
pieces=[]
parts={}
warnings=[]


def move(s, xyz):
    s=s.copy()
    s.translate(V(*xyz))
    return s


def box(size,center):
    return Part.makeBox(*size,V(*(p-d/2 for p,d in zip(center,size))))


def ellipsoid(radii,center):
    m=App.Matrix()
    m.A11,m.A22,m.A33=radii
    return move(Part.makeSphere(1).transformGeometry(m),center)


def cyl(radius,length,start,axis=(0,0,1)):
    return Part.makeCylinder(radius,length,V(*start),V(*axis))


def ring(ro,ri,length,start,axis=(0,0,1)):
    return cyl(ro,length,start,axis).cut(cyl(ri,length+2,start,axis))


def region(shape, axis,lo,hi):
    size=[800.]*3
    origin=[-400.]*3
    origin[axis]=lo
    size[axis]=hi-lo
    return shape.common(Part.makeBox(*size,V(*origin)))


def tube(ro,ri,length,start,axis=(0,0,1)):
    inner_start=tuple(a-b for a,b in zip(start,axis))
    return cyl(ro,length,start,axis).cut(cyl(ri,length+2,inner_start,axis))


def housing(radii,center,wall=2.0):
    return ellipsoid(radii,center).cut(ellipsoid(tuple(r-wall for r in radii),center))


def add(name,shape,color=IVORY,group=PRINT,axis=(0,0,1),link='body'):
    shape=shape.removeSplitter()
    obj=DOC.addObject('PartDesign::Feature',name)
    obj.Label=name.replace('_',' ')
    obj.Shape=shape
    group.addObject(obj)
    obj.addProperty('App::PropertyString','Revision','Dizzy')
    obj.Revision='V2 provisional fit study'
    obj.addProperty('App::PropertyString','RemovalAxis','Dizzy')
    obj.RemovalAxis=str(axis)
    if obj.ViewObject:
        obj.ViewObject.ShapeColor=color
        if group==GUIDES:obj.ViewObject.Visibility=False
    if group==PRINT:
        pieces.append((name,obj,shape,color,axis,link))
        parts[name]=shape
    return obj


def bolt_cut_x(shape,points,x=-64,length=125,r=1.6):
    for y,z in points:
        shape=shape.cut(cyl(r,length,(x,y,z),(1,0,0)))
    return shape


def vent(shape,points,x,length):
    for y,z in points:
        shape=shape.cut(cyl(1.2,length,(x,y,z),(1,0,0)))
    return shape


def tray(size,center,axis_width=2.6):
    """Open saddle plus two retaining ears."""
    a,b,c=size
    x,y,z=center
    base=box((a,b+2*axis_width,2.2),(x,y,z-c/2-1.1))
    for side in (-1,1):
        wall=box((a,axis_width,7),(x,y+side*(b/2+axis_width/2),z-c/2+1.5))
        base=base.fuse(wall)
    for py in (y-b/2-axis_width/2,y+b/2+axis_width/2):
        base=base.cut(cyl(1.22,15,(x,py,z-c/2-4)))
    return base


# The front shell ends behind the optical face. The rim carries the exposed board.
hc=(0,0,159)
neck_cut=cyl(15,35,(0,0,113))
head_shell=housing((40,46,37),hc,1.64).cut(neck_cut)
optical=cyl(26.6,30,(17,0,161),(1,0,0))
head_front=region(head_shell.cut(optical),0,0.5,40)
head_rear=region(head_shell,0,-40,-0.5)
head_front=vent(head_front,[(-23,144),(-19,141),(19,141),(23,144)],16,30)
head_rear=vent(head_rear,[(y,z) for y in (-16,-8,0,8,16) for z in (146,150)],-44,12)
add('Helmet_front',head_front,axis=(1,0,0),link='pitch')
add('Helmet_rear',head_rear,axis=(-1,0,0),link='pitch')
add('Face_bezel',tube(29.7,23.0,3.2,(31.0,0,162),(1,0,0)),CLAY,axis=(1,0,0),link='pitch')
lcd=tube(27.0,22.1,5,(23,0,162),(1,0,0))
for y in (-26,26):
    pad=box((5,13,13),(25,y,162)).cut(cyl(1.6,8,(22,y,162),(1,0,0)))
    lcd=lcd.fuse(pad)
add('LCD_cassette',lcd,CARRIER,axis=(1,0,0),link='pitch')
for side,y in (('Left',15),('Right',-15)):
    cut=region(ellipsoid((14,12,3.5),(-1,y,194)),2,191.5,198)
    add(side+'_crown_cap',cut,CLAY,link='pitch')
add('Voice_clip',tray((12,26,11),(7,0,144)),CARRIER,axis=(-1,0,0),link='pitch')

# Torso is split into a service hatch and a front shell.
tc=(0,0,85)
shell=housing((35,47,51),tc,1.72)
shell=shell.cut(cyl(16,32,(0,0,116)))
body_front=region(shell,0,2.2,35)
body_back=region(shell,0,-35,1.2)
speaker_hole=cyl(14,18,(22,0,88),(1,0,0))
button_hole=cyl(5,15,(23,0,110),(1,0,0))
battery_cut=box((48,72,25),(-42,0,60))
body_front=body_front.cut(speaker_hole).cut(button_hole)
body_back=body_back.cut(battery_cut).cut(box((19,19,26),(-34,18,104)))
body_back=vent(body_back,[(y,z) for y in (-16,-8,0,8,16) for z in (114,118)],-36,14)
add('Torso_front',body_front,axis=(1,0,0))
add('Torso_back',body_back,axis=(-1,0,0))
grille=cyl(15.8,2.5,(30,0,88),(1,0,0))
grille=vent(grille,[(y,z) for y in (-8,-4,0,4,8) for z in (80,84,88,92,96) if y*y+(z-88)**2<100],29,5)
add('Chest_grille',grille,CLAY,axis=(1,0,0))
add('Music_clip',tray((12,29,22),(18,0,88)),CARRIER,axis=(1,0,0))
add('Talk_guide',tube(7,4.0,7,(26,0,110),(1,0,0)),CLAY,axis=(1,0,0))
add('Talk_button',cyl(3.6,7,(28,0,110),(1,0,0)),INK,axis=(1,0,0))
add('Expansion_blank',box((2.3,16,12),(31,21,85)),CLAY,axis=(1,0,0))
add('Rear_controls',bolt_cut_x(box((3,20,27),(-27,24,104)),[(18,99),(29,109)],-30,8,3.3),INK,axis=(-1,0,0))
add('Backplane',bolt_cut_x(box((3,56,53),(-13,0,97)),[(y,z) for y in (-23,-10,10,23) for z in (77,90,103,116)],-15,4),CARRIER,axis=(-1,0,0))
add('RTC_clip',tray((10,22,15),(-20,-28,105)),CARRIER,axis=(-1,0,0))
add('Battery_drawer',tray((43,69.7,21),(-5,0,59)),CARRIER,axis=(-1,0,0))
door=box((2.6,73,24),(-27.5,0,59)).cut(cyl(4.5,6,(-30,0,59),(1,0,0)))
add('Battery_door',bolt_cut_x(door,[(-32,58),(32,58)],-32,9),CLAY,axis=(-1,0,0))
add('Neck_yaw_cassette',tray((24,13.5,24),(0,0,119)),CARRIER,axis=(-1,0,0))
add('Neck_yaw_support',tube(19.5,10,8,(0,0,128)),CLAY,link='yaw')
add('Neck_pitch_cassette',tray((24,13.5,24),(-4,21,143)),CARRIER,axis=(-1,0,0),link='yaw')
yoke=box((23,51,5),(0,0,137))
for y in (-24,24):
    yoke=yoke.fuse(box((12,5,21),(0,y,145)))
    yoke=yoke.cut(cyl(3.5,8,(0,y-4,149),(0,1,0)))
add('Neck_yoke',yoke,INK,link='yaw')
add('Neck_pitch_pin_gauge',tube(6,3.5,8,(0,0,0)),CARRIER,link='calibration')

for label,sgn in (('Left',1),('Right',-1)):
    y=sgn*63
    sleeve=housing((17,13,23),(-4,y,102),1.8)
    add(label+'_sleeve',region(sleeve,0,-4.75,15),CLAY,axis=(1,sgn,0),link=label.lower()+'_arm')
    add(label+'_sleeve_rear',region(sleeve,0,-23,-5.25),CLAY,axis=(-1,sgn,0),link=label.lower()+'_arm')
    glove=ellipsoid((13,11,13),(3,y,87)).fuse(ellipsoid((7,6,7),(13,y,92)))
    glove=glove.cut(ellipsoid((10,8,10),(3,y,87)))
    add(label+'_mitten',glove,axis=(0,sgn,0),link=label.lower()+'_arm')
    pivot=box((17,20,10),(-1,sgn*49,112))
    pivot=pivot.cut(cyl(3.1,25,(-1,sgn*37,112),(0,sgn,0)))
    add(label+'_shoulder_support',pivot,IVORY,axis=(0,sgn,0))
    disk=cyl(13,3,(-1,y+sgn*9,114),(0,sgn,0))
    add(label+'_shoulder_cap',disk,IVORY,axis=(0,sgn,0),link=label.lower()+'_arm')
    add(label+'_shoulder_cassette',tray((24,13.5,24),(-1,sgn*60,110)),CARRIER,axis=(0,sgn,0))
    y=sgn*43
    calf=housing((18,18,28),(-2,y,43),2.0)
    add(label+'_calf_cover',region(calf,0,-3.75,16),CLAY,axis=(1,0,0),link=label.lower()+'_hip')
    add(label+'_calf_rear',region(calf,0,-20,-4.25),CLAY,axis=(-1,0,0),link=label.lower()+'_hip')
    add(label+'_thigh_cassette',tray((24,13.5,29),(0,y,69)),CARRIER,axis=(-1,0,0))
    add(label+'_ankle_cassette',tray((24,13.5,29),(-3,y,32)),CARRIER,axis=(-1,0,0),link=label.lower()+'_hip')
    shoe=region(ellipsoid((36,25,13),(11,y,9)),2,4,23)
    shoe=shoe.cut(ellipsoid((33,22,11),(11,y,9)))
    shoe=shoe.cut(box((25,17,17),(-4,y,21)))
    add(label+'_foot',shoe,IVORY,axis=(1,0,0),link=label.lower()+'_ankle')
    sole=region(ellipsoid((35,25,11),(11,y,9)),2,0,4)
    sole=sole.cut(box((7,11,7),(21,y,3)))
    add(label+'_sole',sole,INK,axis=(0,0,-1),link=label.lower()+'_ankle')

dock=region(ellipsoid((62,59,12),(-16,0,7)),2,0,4)
dock=dock.cut(cyl(13,20,(-5,27,-3))).cut(cyl(13,20,(-5,-27,-3)))
dock=dock.fuse(box((17,38,13),(-42,0,7)))
backrest=ellipsoid((19,22,23),(-44,0,28)).cut(ellipsoid((17,20,21),(-44,0,28)))
dock=dock.fuse(region(backrest,2,4,48))
add('Seated_dock',dock,IVORY,axis=(0,0,-1),link='dock')

for item in MANIFEST['components']:
    obj=add(item['id'],box(item['size'],item['center']),CARRIER,BOARDS)
    obj.addProperty('App::PropertyString','Mount','Dizzy');obj.Mount=item['mount']
    obj.addProperty('App::PropertyString','Removal','Dizzy');obj.Removal=item['remove']
    if obj.ViewObject:obj.ViewObject.Transparency=65

for name,size,center in [('Camera_expansion',(16,18,14),(16,20,175)),('NFC_expansion',(3,29,32),(29,22,85)),
                        ('ToF_expansion',(5,10,18),(29,22,111)),('Neck_harness_slack',(12,17,29),(-12,-5,135))]:
    add(name,box(size,center),CARRIER,GUIDES)

DOC.recompute()
DOC.saveAs(str(OUT/'Dizzy_V2.FCStd'))
Part.export([o for _,o,_,_,_,_ in pieces if o.Name!='Seated_dock' and 'gauge' not in o.Name],str(OUT/'Dizzy_V2.step'))
audit=[]
parts_metadata=[]
for name,obj,shape,color,axis,link in pieces:
    mesh=MeshPart.meshFromShape(Shape=shape,LinearDeflection=.16,AngularDeflection=.27,Relative=False)
    bounds=mesh.BoundBox
    mesh.write(str(OUT/'stl'/f'{name}.stl'))
    Part.export([obj],str(OUT/'step'/f'{name}.step'))
    thickness='provisional'
    valid=shape.isValid() and len(shape.Solids)>0 and shape.Volume>0
    boxdims=[round(bounds.XLength,2),round(bounds.YLength,2),round(bounds.ZLength,2)]
    audit.append({'part':name,'valid':valid,'watertight':mesh.isSolid(),'solids':len(shape.Solids),'build_volume':max(boxdims)<=180,
        'size_mm':boxdims,'solid_equivalent_g':round(shape.Volume*.00127,2),'wall_check':thickness})
    parts_metadata.append({'part':name,'color':color,'explosion_axis':axis,'link':link})
(OUT/'parts.json').write_text(json.dumps(parts_metadata,indent=2))

interferences=[]
for i,a in enumerate(MANIFEST['components']):
    for b in MANIFEST['components'][i+1:]:
        overlap=box(a['size'],a['center']).common(box(b['size'],b['center'])).Volume
        if overlap>.5:
            interferences.append({'a':a['id'],'b':b['id'],'overlap_mm3':round(overlap,1)})
(OUT/'fit-report.json').write_text(json.dumps({'parts':audit,'component_box_conflicts':interferences,
    'status':MANIFEST['status'],'wall_and_harness_sweep':'Needs measured component CAD and physical mounting checks'},indent=2))
print(f'{len(audit)} printable parts, {len(interferences)} provisional component-box conflicts')
