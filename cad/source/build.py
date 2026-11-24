"""FreeCAD solid enclosure builder. Run with bundled FreeCAD Python or Build.FCMacro.
All geometry is in mm. No existing Webots assets are changed.
"""
from pathlib import Path
import json,math,sys,csv,traceback
import FreeCAD as App
import Part,Mesh,MeshPart
ROOT=Path(__file__).resolve().parents[2];CAD=ROOT/'cad';sys.path.insert(0,str(ROOT));sys.path.insert(0,str(Path(__file__).resolve().parent))
from dizzy import design as D
V=App.Vector
IVORY=(.94,.91,.85);ACCENT=(.66,.32,.22);BLACK=(.025,.035,.045);MOUNT=(.28,.49,.47)
OUT=CAD/'output';REPORT=CAD/'reports'
for name in ['stl','step','webots','calibration']:(OUT/name).mkdir(parents=True,exist_ok=True)
MAN=json.loads((CAD/'components.json').read_text());PARAM=json.loads((CAD/'parameters.json').read_text())
WALL=PARAM['wall_mm']; FIT=PARAM['sliding_clearance_per_side_mm']
S=1.;printed=[];hardware=[];shapes={};groups={};results={'checks':[],'failures':[],'provisional':[]}
def record(name,ok,**details):results['checks'].append(dict(name=name,passed=bool(ok),**details));print(('PASS ' if ok else 'REVIEW ')+name,flush=True)
def box(size,center):return Part.makeBox(*size,V(*(c-s/2 for c,s in zip(center,size))))
def cylinder(r,h,center,axis=(0,0,1)):
 return Part.makeCylinder(r,h,V(*center),V(*axis))
def moved(shape,p):q=shape.copy();q.translate(V(*p));return q

def ellipsoid(r,c=(0,0,0)):
 m=App.Matrix();m.A11=r[0];m.A22=r[1];m.A33=r[2]
 return moved(Part.makeSphere(1).transformGeometry(m),c)
def clip(shape,axis,low,high):
 p=[-400.,-400.,-400.];sz=[800.,800.,800.];p[axis]=low;sz[axis]=high-low
 return shape.common(Part.makeBox(*sz,V(*p)))
def ring(ro,ri,h,p,axis=(0,0,1)):return cylinder(ro,h,p,axis).cut(cylinder(ri,h,p,axis))
def ellipse_wire(rx,ry,z,cy=0,cx=0):
 m=App.Matrix();m.A11=rx;m.A22=ry;m.A14=cx;m.A24=cy;m.A34=z
 return Part.Wire(Part.makeCircle(1).transformGeometry(m))
def loft_body(wall=0):
 # Same pear profile as the Webots generator, with dense analytic sections.
 wires=[]
 for i in range(1,60):
  t=math.pi*i/60;c=math.cos(t);f=(1-.22*c)*math.sin(t)
  wires.append(ellipse_wire(max(.05,(45*S-wall)*f),max(.05,(41*S-wall)*f),64.5*S+(49*S-wall)*c))
 wires.reverse()
 # Close at small-radius end sections, away from all visible joining surfaces.
 return Part.makeLoft(wires,True,False)
def add(id,shape,region='fixed',color=IVORY,material='PETG',printable=True,note='',group='Printable',**props):
 shape=shape.removeSplitter()
 if shape.isNull():raise ValueError('Empty part '+id)
 obj=doc.addObject('PartDesign::Feature',id);obj.Label=id.replace('_',' ');obj.Shape=shape
 obj.addProperty('App::PropertyString','Region','Dizzy');obj.Region=region
 obj.addProperty('App::PropertyString','Material','Dizzy');obj.Material=material
 obj.addProperty('App::PropertyString','PrototypeNote','Dizzy');obj.PrototypeNote=note or 'PROVISIONAL — calibrate fit and measure hardware before final printing'
 obj.addProperty('App::PropertyBool','PrintThisPart','Dizzy');obj.PrintThisPart=printable
 for key,value in props.items():
  obj.addProperty('App::PropertyString',key,'Dizzy');setattr(obj,key,str(value))
 if hasattr(obj,'ViewObject') and obj.ViewObject:
  obj.ViewObject.ShapeColor=color
  if group=='Hardware':obj.ViewObject.Transparency=65
 groups[group].addObject(obj);shapes[id]=shape
 entry=dict(id=id,region=region,color=color,material=material,shape=shape,obj=obj,printable=printable)
 (printed if printable else hardware).append(entry)
 return shape

def actual_center(item,scale):
 p=[v*scale for v in item['reference_center_mm']]
 if item['region']=='head':p[2]+=157*scale
 return p

def fit_search():
 trials=[]
 # Assembly envelope expanded by 0.3mm plus a 1.6mm carrier on its bottom face.
 for scale in MAN['scales']:
  failures=[]
  for it in MAN['components']:
   if it['id'].startswith(('crown','camera_lens','camera_LED','decoupling')):continue
   r=it['region'];c=actual_center(it,scale);sz=it['size_mm'];pad=FIT
   for x in (-1,1):
    for y in (-1,1):
     for z in (-1,1):
      q=[c[0]+x*(sz[0]/2+pad),c[1]+y*(sz[1]/2+pad),c[2]+z*(sz[2]/2+pad)-(1.6 if z<0 else 0)]
      if r=='head':
       local=[q[0],q[1],q[2]-157*scale];radii=[v/2*scale-WALL for v in D.HEAD_SIZE]
       valid=sum((a/b)**2 for a,b in zip(local,radii))<=1 and local[1]>=D.HEAD_FRONT_Y*scale+WALL and local[2]>=D.HEAD_BOTTOM_Z*scale+WALL
      elif r=='hips':
       valid=it['id']=='speaker' or sum(((q[i]-(30*scale if i==2 else 0))/(D.HIP_RADII[i]*scale-WALL))**2 for i in range(3))<=1
      elif r=='shoulder':valid=((q[1]/(24*scale-WALL))**2+((q[2]-94*scale)/(15*scale-WALL))**2<=1 and abs(q[0]-math.copysign(36*scale,c[0]))<=20*scale-WALL)
      else:
       rz=49*scale-WALL;t=(q[2]-64.5*scale)/rz
       valid=abs(t)<1 and (q[0]/((45*scale-WALL)*(1-.22*t)))**2+(q[1]/((41*scale-WALL)*(1-.22*t)))**2+t*t<=1
      if not valid:failures.append(it['id']);break
  trial={'scale':scale,'conflicts':sorted(set(failures))};trials.append(trial)
  if not failures:return scale,trials
 return 1.10,trials

def shell_screws(shell,locations,axis=(0,1,0),length=12):
 for p in locations:
  shell=shell.cut(cylinder(1.7,length,p,axis))
 return shell

def build_shells():
 global hip_inner,body_inner,hip_outer,body_outer
 from helmet import helmet_parts
 for name, shape in helmet_parts(sys.modules[__name__]).items():
  is_inlay=name.startswith('Crown_inlay_')
  add(name,shape,'head', ACCENT if is_inlay else IVORY,
      note='Curved crown insert; verify sensor response with the actual copper pad.' if is_inlay else '')
 bezel=ring(34.5*S,28.8*S,1.8,(0,-26*S,157*S),(0,1,0))
 add('Face_bezel',bezel,'head',ACCENT)
 panel=cylinder(28.8*S,1.5,(0,-25.85*S,157*S),(0,1,0))
 panel=panel.cut(cylinder(16.32,5,(0,-27*S,157*S-2.5),(0,1,0)))
 for x,z,rad in [(0,25,3),(10,25,1.6)]:panel=panel.cut(cylinder(rad,6,(x*S,-28*S,(157+z)*S),(0,1,0)))
 add('Face_insert',panel,'head',BLACK)
 # Sliding privacy blade on interior rails, no enlargement of the exterior lens hole.
 lens_z=182*S
 shutter=box((11,1.1,8),(0,-26*S+2.3,lens_z));add('Camera_shutter',shutter,'head',BLACK,OpenTravel_mm=12)
 rail=box((29,2.5,1),(6,-26*S+3.3,lens_z+4.8)).fuse(box((29,2.5,1),(6,-26*S+3.3,lens_z-4.8)))
 rail=rail.fuse(box((2.5,2.5,10.6),(19.25,-26*S+3.3,lens_z)))
 add('Shutter_rails',rail,'head',MOUNT)
 # Torso/hips union removes hidden intersecting skins of the simulation model.
 body_outer=loft_body();body_inner=loft_body(WALL)
 hip_outer=clip(ellipsoid(tuple(a*S for a in D.HIP_RADII),(0,0,30*S)),2,2*S,100)
 hip_inner=clip(ellipsoid(tuple(a*S-WALL for a in D.HIP_RADII),(0,0,30*S)),2,2*S+WALL,100)
 outer=body_outer.fuse(hip_outer);inner=body_inner.fuse(hip_inner);shell=outer.cut(inner)
 # Neck throat, recording switch, acoustic grille, rear inlet and switch.
 shell=shell.cut(cylinder(12,35,(0,0,97*S)))
 shell=shell.cut(box((18,18,6.6),(0,-34*S,94*S)))
 for x in (-8,-4,0,4,8):
  for z in (38,40.5,43):shell=shell.cut(cylinder(.8,24,(x*S,-70*S,z*S),(0,1,0)))
 shell=shell.cut(cylinder(1.2,24,(0,-70*S,48*S),(0,1,0)))
 # The manufacturer socket stays recessed. Clear the entire overmould,
 # not just the metal tip, through the rear wall on the socket's axis.
 from service_layout import pd_socket_position, USB_WELL_WIDTH, USB_WELL_HEIGHT
 pd_center=actual_center(next(c for c in MAN['components'] if c['id']=='usb_c_pd_board'),S)
 px,py,pz=pd_socket_position(pd_center)
 shell=shell.cut(box((USB_WELL_WIDTH,30,USB_WELL_HEIGHT),(px,py+14,pz)))
 shell=shell.cut(box((15,18,10),(0,53*S,14*S)))
 for x in (-25,-15,-5,5,15,25):shell=shell.cut(box((2,22,1.3),(x*S,50*S,43*S)))
 # Open the torso skin beneath each covered shoulder cassette.
 for sign in (-1,1):shell=shell.cut(box((41,36,20),(sign*36*S,0,94*S)))
 # Fastening columns at interfaces; bores pass through mating components.
 for x,y in [(-31,0),(31,0),(0,31)]:
  boss=cylinder(4,14,(x*S,y*S,44*S))
  if x:boss=boss.fuse(box((23,8,14),(math.copysign(40*S,x),0,51*S)))
  else:boss=boss.fuse(box((8,21,14),(0,39*S,51*S)))
  boss=boss.cut(cylinder(1.7,18,(x*S,y*S,42*S)))
  shell=shell.fuse(boss.common(outer))
 upper=clip(shell,2,50*S+.15,160);lower=clip(shell,2,6*S+.15,50*S-.15)
 add('Torso_front',clip(upper,1,-100,8*S-.15),'fixed');add('Torso_rear',clip(upper,1,8*S+.15,100),'fixed')
 add('Hip_front',clip(lower,1,-100,-.15),'fixed');add('Hip_rear',clip(lower,1,.15,100),'fixed')
 bottom=clip(shell,2,2*S,6*S-.15)
 # A bottom insert spans the small ellipsoid cut, not a large false access hatch.
 bottom=bottom.fuse(cylinder(18*S,2,(0,0,2*S)))
 add('Bottom_cover',bottom,'fixed',MOUNT)
 # Separate cosmetic chest applique and record capsule, following the analytic front.
 z=84*S;ap=ellipsoid((23*S,1.5,18*S),(0,D.body_front(0,84)*S-.3,z))
 # Curved patch uses a thin offset of the real body, trimmed to its window.
 patch=body_outer.cut(loft_body(1.1)).common(box((46*S,40,36*S),(0,-38*S,84*S)))
 patch=patch.cut(box((18,20,6.6),(0,-34*S,94*S)))
 add('Chest_inset',patch,'fixed',( .98,.94,.87))
 add('Record_button',box((16.8,2.8,5.7),(0,D.body_front(0,94)*S-.8,94*S)),'fixed',ACCENT,Travel_mm=.8)
 add('Waist_band',body_outer.cut(loft_body(.8)).common(box((150,150,13*S),(0,0,51*S))),'fixed',ACCENT)
 for sign,name in [(-1,'L'),(1,'R')]:
  f=ellipsoid(tuple(a*S for a in D.FOOT_RADII),(sign*28*S,-60*S,30*S))
  f=clip(clip(f,1,-78*S,-45*S),2,2*S,90)
  fi=ellipsoid(tuple(a*S-2.5 for a in D.FOOT_RADII),(sign*28*S,-60*S,30*S))
  fi=clip(fi,1,-78*S+2.5,-45*S+1)
  foot=f.cut(fi)
  add('Foot_'+name,foot,'fixed')
  pad=cylinder(12,2,(sign*28*S,-60*S,0));add('Foot_pad_'+name,pad,'fixed',ACCENT,'TPU')
  add('Volume_cap_'+name,box((2.2,8,8),(sign*49*S,0,157*S)),'head',ACCENT)
 return outer,inner

def arm_profile(profile,sign,wall=0):
 wires=[]
 # Interpolate the same Catmull-Rom section sequence as the Webots hand mesh.
 for i in range(len(profile)-1):
  for j in range(5):
   t=j/5;p0=profile[max(0,i-1)];p1=profile[i];p2=profile[i+1];p3=profile[min(len(profile)-1,i+2)]
   p=[.5*(2*b+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t**3) for a,b,c,d in zip(p0,p1,p2,p3)]
   z,cx,rx,ry=p
   if rx*S-wall<.5 or ry*S-wall<.5:continue
   wires.append(ellipse_wire(rx*S-wall,ry*S-wall,(79+z)*S,(-.2*(17-z))*S,sign*(66+cx)*S))
 return Part.makeLoft(wires,True,False)
def build_arms():
 from scripts.build_hands import PROFILE,CUFF
 for sign,name in [(-1,'L'),(1,'R')]:
  # Original pod has rounded cylindrical ends, reconstructed by profile loft.
  wires=[]
  for i in range(33):
   x=-20+40*i/32;e=max(abs(x)-16,0);inset=4-math.sqrt(max(0,16-e*e))
   w=ellipse_wire((15-inset)*S,(24-inset)*S,0)
   w.rotate(V(0,0,0),V(0,1,0),90);w.translate(V((sign*36+x)*S,0,94*S));wires.append(w)
  pod=Part.makeLoft(wires,True,False)
  cavity=box((34.6,34.6,14.6),(sign*36*S,0,94*S));pod=pod.cut(cavity)
  # Split at the outboard face of the servo bay for independent service.
  pod=pod.cut(cylinder(6.8,80,(-100 if sign<0 else 0,0,94*S),(1,0,0)))
  add('Shoulder_housing_'+name,pod,'fixed')
  sleeve=arm_profile(PROFILE,sign);inner=arm_profile(PROFILE,sign,2.5)
  sleeve=sleeve.cut(inner)
  # Hollow palm is joined to sleeve at the cuff; separate pieces have internal lap rings.
  center=(sign*73*S,-10*S,49*S)
  palm=ellipsoid((10.5*S,10*S,12.5*S),center)
  palm=palm.fuse(ellipsoid((5*S,6.5*S,8*S),(sign*65*S,-13.5*S,53.5*S)))
  palm=palm.cut(ellipsoid((7.5*S,7*S,9.5*S),center))
  add('Forearm_'+name,sleeve,name)
  add('Palm_'+name,palm,name)
  cuff=arm_profile(CUFF,sign).cut(arm_profile(CUFF,sign,1.6));add('Cuff_'+name,cuff,name,ACCENT)
  # Structural bridge reaches shoulder axis without inventing a wrist joint.
  axle_x=sign*56*S
  bridge=box((9,9,25),(sign*65*S,0,85*S)).fuse(cylinder(7,11,(min(axle_x,sign*67*S),0,94*S),(1,0,0)))
  bridge=bridge.cut(cylinder(2.2,24,(sign*56*S-12,0,94*S),(1,0,0)))
  add('Horn_adapter_'+name,bridge,name,MOUNT,note='Use supplied servo horn. Slot/bolt pattern requires physical horn measurement; no printed spline.')
  support=ring(9.5,6.5,5,(sign*56*S-2.5,0,94*S),(1,0,0));add('Shoulder_bearing_seat_'+name,support,'fixed',MOUNT)
 # Independent yaw bearing and hollow cable passage.
 add('Neck_bearing_seat',ring(16,12,6,(0,0,108.5*S)),'fixed',MOUNT)
 add('Neck_hollow_hub',ring(7.5,5.5,13,(0,0,109*S)),'head',MOUNT)
 add('Neck_retaining_ring',ring(13.5,7.8,2,(0,0,117*S)),'head',ACCENT)

def build_carriers():
 global component_shapes
 component_shapes={}
 for it in MAN['components']:
  id=it['id'];size=it['size_mm'];c=actual_center(it,S);region='head' if it['region']=='head' else 'fixed'
  envelope=(cylinder(18,13,(c[0],c[1]-6.5,c[2]),(0,1,0)) if id=='speaker' else box(size,c));component_shapes[id]=envelope
  add('HW_'+id,envelope,region,(.24,.59,.38),'Purchased',False,group='Hardware',ComponentID=id,RemovalDirection=it['removal'])
  if id.startswith(('crown','camera_lens','camera_LED','decoupling')):continue
  if id=='speaker':
   add('Carrier_speaker',ring(19.5,14.3,1.4,(c[0],c[1]+6.8,c[2]),(0,1,0)),region,MOUNT)
   continue
  sx,sy,sz=size;cz=c[2]-sz/2-FIT-1.6/2
  # Offset these two bridges toward the free PCB edge. Their screw lugs
  # follow the same axis so the bridge still removes with its own screws.
  bridge_y=c[1]+{'display_pocket':4.6,'microphone_board':-3.1,'pca9685_driver':.8,'esp32_board':10}.get(id,0)
  base=box((sx+1.2,(10 if 'servo' in id else sy+1.2),1.6),(c[0],c[1],cz))
  # Raised locating ledges, interrupted for connectors and replaceable restraints.
  for sign in (-1,1):
   ledge=box((1.2,max(3,min(sy*.28,8) if 'servo' in id else sy*.28),3.2),(c[0]+sign*(sx/2+.9),c[1],cz+1.6))
   base=base.fuse(ledge)
   # Slotted lugs keep screws outside provisional board/connector boundaries.
   x=c[0]+sign*(sx/2+2.6)
   lug=box((4,7,2.4),(x,bridge_y,cz+.4))
   lug=lug.cut(cylinder(1.7,8,(x,bridge_y,cz-3)))
   base=base.fuse(lug)
  if id=='esp32_board':
   from service_layout import ESP_HEADER_Y
   # Raised end bridges retain the tray while both pin rows have an
   # underside opening for the headers and the mated low-profile plugs.
   for sign in (-1,1):
    base=base.cut(box((49.1,4.1,12),(c[0],c[1]+sign*ESP_HEADER_Y,cz)))
   # Clear the programmer overmould from the left tray lip without
   # losing the floor below it or either retainer screw.
   base=base.cut(box((17,13.4,9),(c[0]-29.5,c[1],cz+4.6)))
  add('Carrier_'+id,base,region,MOUNT,RemovalDirection=it['removal'],ComponentID=id,EdgeGrip='Verify actual bare PCB edge and use insulating pad; retainer height adjustable')
  # One removable bridge per cassette, printable separately.
  length=sx+7.2
  ret=box((length+2.4,9 if id=='neck_servo' else 6,1.6),(c[0],bridge_y,c[2]+sz/2+1.1))
  for sign in (-1,1):ret=ret.cut(cylinder(1.7,6,(c[0]+sign*(sx/2+2.6),bridge_y,c[2]+sz/2-2)))
  if id=='neck_servo':
   ret=ret.cut(cylinder(3.4,8,(c[0]-5,c[1],c[2]+sz/2-2)))
  add('Retainer_'+id,ret,region,MOUNT,note='M3 adjustment screws/spacers and insulating contact pads; final edge contact needs physical board measurement')
 # Small devices retain their own service pockets instead of being glued into shell.
 for name,size,c in [('LED_holder',(7,5,6),(10*S,-19*S,182*S)),('Lens_flex_support',(14,3,13),(0,-10,182*S))]:
  shape=box(size,c)
  if name=='LED_holder':shape=shape.cut(cylinder(1.8,10,(10*S,-25*S,182*S),(0,1,0)))
  else:shape=shape.cut(box((10.6,10,8.6),c))
  add(name,shape,'head',MOUNT)
 # Capacitor clip pairs and independent insulating crown saddles.
 for id in ['servo_470uF_1','servo_470uF_2','audio_capacitor','controller_100uF']:
  it=next(i for i in MAN['components'] if i['id']==id);c=actual_center(it,S);dia=min(it['size_mm'][:2])
  clipper=ring(dia/2+1.4,dia/2+.3,4,(c[0],c[1],c[2]-2))
  clipper=clipper.cut(box((2,20,8),(c[0],c[1]+7,c[2])))
  add('Clip_'+id,clipper,'fixed',MOUNT)
 # Passive strip: individual numbered recesses and underside lead-clearance.
 strip=box((29,4.6,2),(0,-29.5*S,77*S))
 for x in (-10,-6,-2,2,6,10):strip=strip.cut(box((3.3,3.3,8),(x*S,-29.5*S,76*S)))
 add('Passive_strip',strip,'fixed',MOUNT)
 # Rear power inlet support and a screw-on cable saddle.
 saddle=box((20,8,4),(20,35*S,13*S)).cut(cylinder(3,12,(14,35*S,15*S),(1,0,0)))
 add('USB_cable_saddle',saddle,'fixed',MOUNT)
 # Harness clips on each region; openable lips, never fixed across a moving joint.
 for name,c,reg in [('head',(18,14,159),'head'),('neck',(8,0,108),'fixed'),('hips',(-27,-1,10),'fixed')]:
  c=tuple(v*S for v in c);clipper=ring(4.7,3.2,5,c)
  clipper=clipper.cut(box((3,8,9),(c[0],c[1]+5,c[2]+2)))
  add('Harness_clip_'+name,clipper,reg,MOUNT)
 # Separate acoustic gasket; its final seating orientation is provisional.
 add('Speaker_gasket',ring(15.5,12,1.5,(0,-36*S-8.3,30*S),(0,1,0)),'fixed',BLACK,'TPU')

def calibration():
 for gap in (.2,.3,.4):
  suffix=str(gap).replace('.','p')
  # Flat display seat coupon with the actual unscaled active aperture.
  sample=box((57,51,4),(0,0,2)).cut(cylinder(16.2+gap,6,(0,0,-1)))
  sample=sample.cut(box((52+gap*2,46+gap*2,4),(0,0,4)))
  add('CAL_display_'+suffix,sample,'coupon',MOUNT,group='Calibration')
  nutpoints=[V(3.1*math.cos(i*math.tau/6),3.1*math.sin(i*math.tau/6),1) for i in range(7)]
  nut=Part.Face(Part.makePolygon(nutpoints)).extrude(V(0,0,2.6))
  coupon=box((25,16,5),(0,0,2.5)).cut(cylinder(1.5+gap,8,(0,0,-1))).cut(nut)
  add('CAL_screw_nut_'+suffix,coupon,'coupon',MOUNT,group='Calibration')
  rail=box((35,20,4),(0,0,2)).cut(box((25+gap*2,8+gap*2,4),(0,0,3)))
  add('CAL_board_rail_'+suffix,rail,'coupon',MOUNT,group='Calibration')
  joint=ring(10,6.5+gap,5,(0,0,0));add('CAL_shoulder_seat_'+suffix,joint,'coupon',MOUNT,group='Calibration')
  button=box((25,18,4),(0,0,2)).cut(box((16.8+2*gap,5.7+2*gap,8),(0,0,2)))
  add('CAL_button_'+suffix,button,'coupon',MOUNT,group='Calibration')

def validation_and_export():
 rows=[]
 for p in printed:
  id=p['id'];s=p['shape'];helmet=id.startswith(('Helmet_', 'Crown_inlay_'))
  mesh=MeshPart.meshFromShape(Shape=s,LinearDeflection=.035 if helmet else .12,
                             AngularDeflection=.075 if helmet else .15,Relative=False)
  bb=mesh.BoundBox
  p['mesh_bounds']=bb
  valid=s.isValid() and len(s.Solids)==1 and all(t.isClosed() for t in s.Solids)
  record('solid:'+id,valid,solids=len(s.Solids),volume_mm3=round(s.Volume,2))
  bed=max(bb.XLength,bb.YLength,bb.ZLength)<=PARAM['max_print_edge_mm']
  record('print-volume:'+id,bed,size_mm=[round(bb.XLength,2),round(bb.YLength,2),round(bb.ZLength,2)])
  folder='calibration' if p['region']=='coupon' else 'stl'
  mesh.write(str(OUT/folder/(id+'.stl')))
  Part.export([p['obj']],str(OUT/'step'/(id+'.step')))
  rows.append(dict(part=id,material=p['material'],region=p['region'],solid_valid=valid,solid_count=len(s.Solids),volume_mm3=round(s.Volume,2),estimated_mass_g=round(s.Volume*(1.24 if p['material']=='PETG' else 1.2)/1000,2),print_size_mm=f'{bb.XLength:.1f} x {bb.YLength:.1f} x {bb.ZLength:.1f}',print_note='0.4mm nozzle / 0.2mm layer; orient joints/bosses for strength; calibrate fit'))
  if p['region']!='coupon':
   mesh.transform(App.Matrix())
   pts=mesh.Topology
   lines=['# CAD-derived; Webots vertices in metres']
   lines+=['v '+' '.join(f'{a/1000:.8f}' for a in point) for point in pts[0]]
   lines+=['f '+' '.join(str(i+1) for i in face) for face in pts[1]]
   (OUT/'webots'/(id+'.obj')).write_text('\n'.join(lines)+'\n')
 # Exact CAD-versus-envelope collisions, not just a 2-D drawing.
 collisions=[]
 structural=[p for p in printed if p['region']!='coupon' and not p['id'].startswith(('Carrier_','Retainer_','Clip_'))]
 for it in MAN['components']:
  id=it['id'];env=component_shapes[id]
  for p in structural:
   if not env.BoundBox.intersect(p['mesh_bounds']):continue
   # Foil is placed beneath a removable skin; trim its allocated pocket from the inlay.
   try:
    overlap=env.common(p['shape']);volume=0 if overlap.isNull() else overlap.Volume
   except (ValueError,Part.OCCError) as error:
    results.setdefault('undetermined_intersections',[]).append(dict(component=id,part=p['id'],error=str(error)))
    continue
   if volume>.5:collisions.append({'component':id,'part':p['id'],'overlap_mm3':round(volume,2)})
 results['envelope_collisions']=collisions
 record('Component-envelope clearance',not collisions and not results.get('undetermined_intersections'),conflicts=collisions)
 # Arm mass report excludes coupons and includes adapters/cuffs.
 for region in ('L','R'):
  mass=sum(row['estimated_mass_g'] for row in rows if row['region']==region)
  record('Arm mass '+region,mass<=25,estimated_mass_g=round(mass,2),target_g=25,density_g_cm3=1.24)
 with (REPORT/'parts.csv').open('w') as f:
  writer=csv.DictWriter(f,fieldnames=rows[0]);writer.writeheader();writer.writerows(rows)
 # Independent printable exports exclude hardware envelope blocks and coupons.
 objs=[p['obj'] for p in printed if p['region']!='coupon']
 Part.export(objs,str(OUT/'Dizzy-assembly.step'))
 results['parts']=len(objs);results['scale']=S;results['units']='mm'
 results['provisional']=['All electronic dimensions, mounting contacts and connector positions await samples','Bearing/horn/shaft fits, wire bend radii, acoustics, thermal and power validation','Mechanical carrier attachment/removal and joint sweep results must be reviewed; not a manufacturing release']
 results['hardware_envelopes']=[dict(id=i['id'],center_mm=actual_center(i,S),size_mm=i['size_mm']) for i in MAN['components']]
 (REPORT/'checks.json').write_text(json.dumps(results,indent=2)+'\n')
 doc.recompute()
 # Alternate documents preserve transforms for exploded review without changing originals.
 for i,p in enumerate(printed):
  if p['region']=='coupon' and p['obj'].ViewObject:p['obj'].ViewObject.Visibility=False
 for p in hardware:
  if p['obj'].ViewObject:p['obj'].ViewObject.Visibility=False
 doc.recompute();doc.saveAs(str(OUT/'Dizzy.FCStd'))
 print('BUILD_COMPLETE',len(objs),'parts',flush=True)

def run():
 global doc,S
 doc=App.newDocument('DizzyServiceable')
 (REPORT/'build-error.txt').unlink(missing_ok=True)
 for name in ['Printable','Hardware','Calibration']:
  groups[name]=doc.addObject('App::DocumentObjectGroup',name)
 params=doc.addObject('App::FeaturePython','DesignParameters')
 for name,value in PARAM.items():
  if isinstance(value,(int,float)):
   params.addProperty('App::PropertyFloat',name,'Prototype dimensions');setattr(params,name,value)
 S,trials=fit_search()
 override=PARAM.get('scale_override',0)
 if override:
  if not 1 <= override <= 1.1:raise ValueError('scale_override must stay between 1.0 and 1.10')
  S=override
 results['scale_search']=trials
 (REPORT/'scale-search.json').write_text(json.dumps(trials,indent=2)+'\n')
 print('SELECTED_SCALE',S,flush=True)
 build_shells();print('SHELLS_DONE',flush=True)
 build_arms();print('ARMS_DONE',flush=True)
 build_carriers();print('CARRIERS_DONE',flush=True)
 calibration()
 from refine import refine
 refine(sys.modules[__name__]);validation_and_export()
if __name__=='__main__':
 try:run()
 except Exception:
  REPORT.mkdir(exist_ok=True);(REPORT/'build-error.txt').write_text(traceback.format_exc());raise
