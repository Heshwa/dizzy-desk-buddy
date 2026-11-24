"""Freeze the Webots reference and enumerate provisional mechanical interfaces."""
from pathlib import Path
import sys,json,hashlib,shutil,csv
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from dizzy import design as d
CAD=ROOT/'cad'
ref={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'assets').glob('*.obj'))}
(CAD/'reference/asset-hashes.json').write_text(json.dumps(ref,indent=2)+'\n')
shutil.copy(ROOT/'dizzy/design.py',CAD/'reference/design.py')
shutil.copy(ROOT/'protos/Dizzy.proto',CAD/'reference/Dizzy.proto')
shutil.copy(ROOT/'reports/seated-companion.png',CAD/'reference/seated-companion.png')
items=[]
def item(id,size,center,region,role,removal='rear',**extra):
 items.append(dict(id=id,size_mm=list(size),reference_center_mm=list(center),region=region,role=role,removal=removal,measurement_status='PROVISIONAL — no physical sample',connector_allowance='Original envelope includes headers; additional port space checked separately',**({'mount':'Independent screwed carrier with adjustable padded edge retainers'}|extra)))
for name,group in [('head',d.HEAD_KEEPOUTS),('torso',d.BODY_KEEPOUTS),('hips',d.BASE_KEEPOUTS),('shoulder',d.SHOULDER_KEEPOUTS)]:
 for id,spec in group.items():
  if id=='servo_capacitor':
   for n,dy in [(1,-6),(2,6)]:item('servo_470uF_'+str(n),(10,10,14),(spec['center'][0],spec['center'][1]+dy,spec['center'][2]),name,'470uF/10V capacitor','bottom')
   continue
  item(id,((52,14,46) if id=='display_pocket' else (36,13,36) if id=='speaker' else spec['size']),((0,-15.5,-2.5) if id=='display_pocket' else (0,-36,30) if id=='speaker' else spec['center']),name,id.replace('_',' '),'front' if id in ('pca9685_driver','speaker','microphone_board','amplifier','power_distribution','talk_switch','display_pocket') else 'side' if 'shoulder' in id else 'rear')
item('controller_100uF',(7,7,12),(45,0,30),'hips','100uF controller capacitor','rear')
item('master_switch',(14,8,9),(27,30,22),'hips','Master power switch','rear')
for n,x in enumerate((-10,-6,-2,2,6,10),1):item('decoupling_100nF_'+str(n),(3,3,4),(x,-29.5,66.5),'torso','Local decoupling allocation; distribute on breakout pins during hardware wiring','front',mount='Removable passive carrier; provisional lead locations')
for side,x in [('left',-10),('right',10)]:item('crown_'+side,(18,22,.1),(x,0,38.35),'head','Insulated copper touch electrode','top',mount='Separate pocket beneath replaceable thin crown inlay')
item('camera_lens',(10,10,8),(0,-18,25),'head','OV2640 on compatible 75mm FPC','front')
item('camera_LED',(3,5,3),(10,-22,25),'head','3mm activity LED','front')
manifest=dict(units='mm',reference_height_mm=203,reference_width_mm=167,scales=[1,1.025,1.05,1.075,1.10],wall_mm=2.5,fit_per_side_mm=.3,hardware_scaled=False,components=items,
interfaces={'head_yaw_degrees':[-45,45],'arm_lift_degrees':[0,120],'print_volume_mm':[180,180,180],'neck_bearing':'15x24x5 mm planning interface; verify supplier and shaft assembly','shoulder_bearing':'4x13x5 mm planning interface; verify supplier and horn offset','fasteners':'M3 shell/carrier screws with replaceable captive hex nuts; M2 only where verified on purchased boards'},
auxiliary=[{'id':'wire_harness','mount':'Retained channels and removable clips','status':'AWG and connector dimensions provisional; power capability not qualified'}, {'id':'pullups_and_terminals','mount':'Removable distribution/passive carrier','status':'Layout prototype; final solder footprint not released'}, {'id':'servo_horns','mount':'Vendor horn screwed to removable coupling, never printed splines','status':'Measure actual horns before printing adapters'}, {'id':'RTC_cell','mount':'Accessible holder on removable RTC carrier','status':'Noncharging board required'}, {'id':'speaker_gasket','mount':'Removable TPU/foam ring','status':'Prototype acoustic fit'}, {'id':'fasteners','mount':'Individual captive-nut pockets','status':'Calibrate before final print'}])

for it in items:
 if it['id']=='display_pocket':it.update(physical_envelope_before_rotation_mm=[46,14,52],orientation_note='Rotate board 90 degrees around its face normal; active display moves down 2.5mm for camera clearance; no dimensions scaled')
 if it['id']=='speaker':it.update(shape='cylinder_y',physical_envelope_before_rotation_mm=[36,36,13],orientation_note='Round speaker faces front, nominal purchased diameter 28mm; 36mm assembly envelope includes clearance',removal='front')
 if it['id']=='clock_board_and_cell':it['removal']='bottom'
 if it['id'].startswith('servo_470'):it['removal']='left'
(CAD/'components.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(len(items),'component allocations; reference frozen')
