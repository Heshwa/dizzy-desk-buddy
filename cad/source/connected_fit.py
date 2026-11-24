"""Model installed hardware, harness routes and connector service space in the CAD shell."""
import json
import math
from itertools import combinations
from pathlib import Path

import numpy as np
import trimesh
from scipy.spatial.distance import cdist
from service_layout import ESP_HEADER_Y, USB_PLUG, USB_WELL_HEIGHT, USB_WELL_WIDTH, pd_board_origin, pd_socket_position

CAD = Path(__file__).resolve().parents[1]
ROOT = CAD.parent
OUT = CAD / 'fit-study'
GEOMETRY = OUT / 'meshes'
GEOMETRY.mkdir(parents=True, exist_ok=True)
baseline = json.loads((CAD / 'reports/checks.json').read_text())
scale = baseline['scale']
allowances = {p['id']:p for p in baseline['hardware_envelopes']}
pinmap = json.loads((ROOT / 'hardware/pinmap.json').read_text())['pins']
source = {
    'esp32': 'https://dl.espressif.com/dl/schematics/esp32_devkitc_v4_dimensions.pdf',
    'pd': 'https://learn.adafruit.com/adafruit-husb238-usb-type-c-power-delivery-breakout/downloads',
    'servo': 'https://towerpro.com.tw/product/sg90-analog/',
    'speaker': 'https://puiaudio.com/product/speakers-and-receivers/as02804pr-n50-r',
    'pca': 'https://techtonics.in/product/pca9685-16-channel-12-bit-pwm-servo-driver-i2c-interface/',
    'camera': 'https://techtonics.in/product/esp32-cam-wifi-bluetooth-development-board-with-ov2640-camera-module-2mp/',
    'flex': 'https://probots.co.in/ov2640-120-degree-wide-angle-lens-2mp-camera-module-24pin-75mm.html',
    'lcd': 'https://techtonics.in/product/1-28-inch-round-display-module-gc9a01-7p-240x240-spi/',
}
GREEN = [.15,.49,.32]
BLUE = [.12,.30,.62]
BLACK = [.12,.15,.18]
METAL = [.67,.72,.73]
GOLD = [.80,.61,.31]
RED = [.81,.24,.19]
items = []
components = []
ports = {}
routes = []
waypoints = json.loads(Path(__file__).with_name('service_routes.json').read_text())


def v(*x):
    return np.array(x,dtype=float)


def center(name):
    return np.array(allowances[name]['center_mm'])


def box(size, location):
    mesh = trimesh.creation.box(extents=size)
    mesh.apply_translation(location)
    return mesh


def cylinder(radius, height, location, axis=(0,0,1)):
    mesh = trimesh.creation.cylinder(radius=radius,height=height,sections=32)
    mesh.apply_transform(trimesh.geometry.align_vectors([0,0,1],axis))
    mesh.apply_translation(location)
    return mesh


def add(owner, name, mesh, color, kind='body'):
    items.append(dict(owner=owner, id=f'{owner}--{name}', mesh=mesh, color=color, kind=kind))


def part(name, label, basis, link=None):
    components.append(dict(id=name,label=label,basis=basis,source=link))


def board(name, dimensions, location, color=GREEN):
    add(name,'PCB',box(dimensions,location),color)


def block(name, id, size, xyz, color=BLACK, kind='body'):
    add(name,id,box(size,xyz),color,kind)


# Official PCB outline plus the measured-layout mounting assumption that the
# pins point down. Plug sizes are fit-test gauges pending a physical sample.
name = 'esp32_board'
part(name,'Espressif ESP32 DevKitC V4','Official 48.26 × 27.94 mm PCB outline. Module/socket stack and plug dimensions are assumptions.',source['esp32'])
c = center(name); z = c[2] - allowances[name]['size_mm'][2]/2 + 1.1
board(name,(48.26,27.94,1.6),[c[0],c[1],z],BLACK)
block(name,'RF_module',(25.4,18,3.1),c+v(7,0,z-c[2]+2.35),METAL)
block(name,'Micro_USB_receptacle',(5.2,7.5,2.7),c+v(-21.7,0,z-c[2]+2.15),METAL)
for sign in (-1,1):
    block(name,f'19_pin_header_{sign}',(47.5,2.5,6.2),[c[0],c[1]+sign*ESP_HEADER_Y,z-3.5],GOLD)
    block(name,f'jumper_mated_{sign}',(28,2.65,8),[c[0],c[1]+sign*ESP_HEADER_Y,z-9.35],BLACK,'connector')
    ports[f'esp_{sign}'] = v(c[0]+2,c[1]+sign*(ESP_HEADER_Y-1.5),z-13.4)
ports['esp_head'] = v(c[0]-12,c[1]+ESP_HEADER_Y-2.8,z-13.4)
mcu_plug = box((23,12,7),[c[0]-33.3,c[1],z+2.15])

name = 'usb_c_pd_board'
part(name,'Adafruit HUSB238 5807','Manufacturer 3D file, including the tall terminal block. The chosen cable overmold uses a provisional gauge.',source['pd'])
pd = trimesh.load(OUT/'vendor'/'adafruit-5807.stl',force='mesh')
c = center(name)
pd_offset = v(*pd_board_origin(c))
pd.apply_translation(pd_offset)
for i, mesh in enumerate(pd.split(only_watertight=False)):
    add(name,f'vendor_solid_{i}',mesh,GREEN if i==2 else METAL if mesh.extents[1]>7 else BLACK)
pd_socket = v(*pd_socket_position(c))
ports['pd_terminal'] = pd_offset + v(10.1,3.5,9)
# Trial connection point at the breakout's I2C pad/connector area.
ports['pd_i2c'] = pd_offset + v(17.5,10,4)

name = 'pca9685_driver'
part(name,'TECH1049 PCA9685 servo board','Supplier 62 × 25 mm outline. Header, screw terminals and JR plugs are occupied volumes.',source['pca'])
c=center(name); z=c[2]-5.6
board(name,(62,25,1.6),[c[0],c[1],z],BLUE)
block(name,'PWM_controller',(8,6,2.2),[c[0],c[1],z+1.9])
for i in range(16):
    x=(i-7.5)*3.4
    block(name,f'PWM_{i:02d}',(2.55,7.62,5.2),[x,c[1]-6.75,z+3.4],GOLD)
for i in range(3):
    x=(i-7.5)*3.4
    block(name,f'JR_plug_CH{i}',(3.1,8,10.4),[x,c[1]-6.75,z+10.25],BLACK,'connector')
    ports[f'pca_{i}']=v(x,c[1]-6.75,z+15.5)
block(name,'Power_terminal',(8,8,9),[26,c[1]+6,z+5.3],BLUE)
ports['pca_i2c']=v(15,c[1]+10,z+6)
ports['pca_power']=v(26,c[1]+9,z+8)

name='display_pocket'
part(name,'TECH2512 round GC9A01 LCD','1.28-inch display class. 46 × 40 mm carrier orientation and header position await a measurement.',source['lcd'])
c=center(name); z=157*scale-2.5
board(name,(46,1.6,40),[0,c[1]-5.5,z],BLUE)
add(name,'Round_glass',cylinder(16.2,1.4,[0,-26*scale+1.7,z],(0,1,0)),[.035,.08,.105])
block(name,'7_pin_right_angle_header',(18,4,2.7),[0,c[1]-2.8,z-16.5],GOLD)
block(name,'7_pin_mated_plug',(18,8,5),[0,c[1]+2.5,z-16.5],BLACK,'connector')
ports['lcd']=v(0,c[1]+7,z-16.5)

name='camera_board'
part(name,'ESP32-CAM and separate OV2640 lens','Supplier 40 × 27 × 12 mm board size. Lens bracket/FPC pin and connector positions remain provisional.',source['camera'])
c=center(name)
board(name,(27,1.6,40),[c[0],c[1]+2,c[2]],BLACK)
block(name,'ESP32_CAM_RF_shield',(18,3.1,20),[c[0],c[1]+4.1,c[2]+7],METAL)
block(name,'FPC_socket',(15,2.5,4),[c[0],c[1]-.05,c[2]+13],GOLD)
block(name,'Power_programming_plug',(6,8,10),[c[0]+9,c[1]+5,c[2]-14],BLACK,'connector')
ports['cam_power']=v(c[0]+9,c[1]+5,c[2]-20)
ports['cam_fpc']=v(c[0],c[1]-1,c[2]+15)
c=center('camera_lens')
add('camera_lens','Lens_barrel',cylinder(4.8,7,c,(0,1,0)),BLACK)
ports['lens_fpc']=c+v(0,3.5,-3.2)

for name, label, size, color in [
    ('clock_board_and_cell','DS3231 and coin-cell holder',(38,22,1.6),BLUE),
    ('amplifier','MAX98357A amplifier',(19,18,1.6),BLACK),
    ('microphone_board','INMP441 microphone',(15,13,1.6),BLUE),
    ('power_distribution','5 V distribution board',(24,1.6,14),GREEN),
]:
    part(name,label,'The supplier variant needs measurement. PCB and plug placement are representative.')
    c=center(name)
    if name=='power_distribution':
        board(name,size,c)
        for x in (-8,0,8):
            block(name,f'Terminal_{x}',(5,5,5),c+v(x,2.8,0),BLUE)
        ports['distribution']=c+v(0,5,1)
        continue
    z = c[2]-allowances[name]['size_mm'][2]/2+1.1
    board(name,size,[c[0],c[1],z],color)
    if name=='clock_board_and_cell':
        add(name,'Coin_cell',cylinder(10,3.2,[c[0]-3,c[1],z+3.7]),METAL)
        block(name,'I2C_plug',(10.4,5,9),[c[0]+12,c[1],z+5.3],BLACK,'connector')
        ports['rtc']=v(c[0]+12,c[1],z+10)
    elif name=='amplifier':
        block(name,'Output_terminal',(9.3,6,7),[c[0],c[1]-6,z+4.3],BLUE)
        block(name,'I2S_plug',(12.7,4,7),[c[0],c[1]+5,z+4.3],BLACK,'connector')
        ports['amp_out']=v(c[0],c[1]-7,z+6)
        ports['amp_bus']=v(c[0],c[1]+5,z+8)
    else:
        block(name,'MEMS_capsule',(4.7,3.8,1.2),[c[0],c[1]-3,z+1.4],METAL)
        block(name,'Microphone_plug',(12.7,4,7),[c[0],c[1]+3,z+4.3],BLACK,'connector')
        ports['mic']=v(c[0],c[1]+3,z+8)

name='speaker'
part(name,'PUI Audio 28 mm speaker','Manufacturer 28 × 7.5 mm nominal speaker plus a separate diaphragm-travel gauge.',source['speaker'])
c=center(name)
add(name,'Speaker_basket',cylinder(14,7.5,c,(0,1,0)),BLACK)
add(name,'Speaker_magnet',cylinder(8.5,1,c+v(0,3.7,0),(0,1,0)),METAL)
ports['speaker']=c+v(-6,4,2)
speaker_excursion=cylinder(14,3.25,c+v(0,-5.375,0),(0,1,0))

for name in ['neck_servo','left_shoulder_servo','right_shoulder_servo']:
    part(name,'TowerPro SG90 '+name.replace('_servo','').replace('_',' '),
         'Manufacturer body specification 23 × 12.2 × 29 mm. Shaft centre and housing orientation are trial values.',source['servo'])
    c=center(name)
    if name=='neck_servo':
        block(name,'Motor_body',(23,12.2,29),c,BLUE)
        block(name,'Fixing_tabs',(32.3,12.2,2),c+v(0,0,8),BLUE)
        shaft=c+v(-5,0,14.5)
        add(name,'Output_spline',cylinder(2.5,4,shaft+v(0,0,2)),GOLD)
        ports[name]=c+v(6,6.3,-11.5)
    else:
        sign=-1 if 'left' in name else 1
        block(name,'Motor_body',(29,23,12.2),c,BLUE)
        block(name,'Fixing_tabs',(2.5,32.3,12.2),c+v(sign*8,0,0),BLUE)
        shaft=c+v(sign*14.5,-5,0)
        add(name,'Output_spline',cylinder(2.5,4,shaft+v(sign*2,0,0),(1,0,0)),GOLD)
        ports[name]=c+v(-sign*12,8,0)

for name in ['talk_switch','minus_switch','plus_switch','master_switch','crown_left','crown_right','camera_LED']:
    c=center(name)
    if name.startswith('crown'):
        block(name,'Copper', (18,15,.1),c,GOLD)
    elif name=='master_switch':
        block(name,'Switch_body',(14,8,9),c,BLACK)
        block(name,'Switch_lever',(6,3,7),c+v(0,5.4,0),RED)
    elif name=='camera_LED':
        add(name,'3_mm_LED',cylinder(1.5,4,c,(0,1,0)),[.13,.65,.29])
    else:
        dim=(5,6,6) if name!='talk_switch' else (6,5,6)
        block(name,'Tactile_switch',dim,c,BLACK)
    if name=='camera_LED':
        ports[name]=c+v(0,6.8,0)
    elif name=='master_switch':
        ports[name]=c+v(0,-4.2,0)
    else:
        ports[name]=c

for name in allowances:
    if '470uF' in name or 'capacitor' in name or name=='controller_100uF':
        c=center(name); sx,_,sz=allowances[name]['size_mm']
        add(name,'Electrolytic',cylinder(sx*.42,sz-1,c),BLACK)
        add(name,'Top',cylinder(sx*.4,.4,c+v(0,0,(sz-1)/2)),METAL)
    elif name.startswith('decoupling_'):
        block(name,'100nF_body',(2.4,2.4,3.5),center(name),GOLD)


def flat_ribbon(points, width, thickness):
    """Sweep a flat section around the camera ribbon's YZ service loop."""
    path = np.array(points)
    tangent = np.gradient(path, axis=0)
    tangent /= np.linalg.norm(tangent, axis=1)[:, None]
    normal = np.cross((1., 0., 0.), tangent) * (thickness / 2)
    edge = v(width / 2, 0, 0)
    sections = np.stack((path+edge+normal, path-edge+normal,
                         path-edge-normal, path+edge-normal), axis=1)
    faces = [[0, 2, 1], [0, 3, 2]]
    for i in range(len(path)-1):
        for corner in range(4):
            a = 4*i + corner
            b = 4*i + (corner+1) % 4
            faces.extend(((a, b, b+4), (a, b+4, a+4)))
    j = len(path)*4 - 4
    faces.extend(((j, j+1, j+2), (j, j+2, j+3)))
    return trimesh.Trimesh(vertices=sections.reshape(-1, 3), faces=np.asarray(faces)[:, ::-1])


def link(id, label, first, last, pins, radius, color=BLUE, ribbon=None):
    points=[ports[first], *map(np.array,waypoints[id]),ports[last]]
    if ribbon:
        mesh = flat_ribbon(points, *ribbon)
        extent = max(ribbon)/2
    else:
        steps=[]
        for start,end in zip(points,points[1:]):
            length = float(np.linalg.norm(end-start))
            if length > .001:
                steps.append(cylinder(radius,length,(start+end)/2,(end-start)/length))
        for point in points[1:-1]:
            elbow = trimesh.creation.icosphere(subdivisions=2, radius=radius)
            elbow.apply_translation(point)
            steps.append(elbow)
        mesh=trimesh.util.concatenate(steps)
        extent = radius
    # Guard against a displaced elbow silently adding an unrelated collision.
    if (np.any(mesh.bounds[0] < np.min(points, axis=0) - extent - .001)
            or np.any(mesh.bounds[1] > np.max(points, axis=0) + extent + .001)):
        raise ValueError(f'{id} cable envelope extends outside its waypoint bounds')
    routes.append(dict(id=id,label=label,pins=pins,start=first,end=last,points=points,
                       radius_mm=radius,ribbon_mm=ribbon,mesh=mesh,color=color))


def pins(*names):
    return ', '.join(f'{name.replace("_"," ")} GPIO{pinmap[name]["gpio"]}' for name in names)


ports['neck_entry']=v(0,0,113.5)
ports['head_bus']=v(0,0,133)
link('PD_to_switch','USB-C board to master switch','pd_terminal','master_switch','5 V power and common ground',2.25,RED)
link('Switch_to_distribution','Master switch to 5 V distribution','master_switch','distribution','Switched 5 V + GND',2.25,RED)
link('Power_main','Distribution to ESP32','distribution','esp_-1','ESP32 5V/GND',1.65,RED)
link('Power_servo','Distribution to PWM servos','distribution','pca_power','PCA9685 V+/GND',2.25,RED)
link('Power_audio','Distribution to amplifier','distribution','amp_bus','MAX98357A VIN/GND', 1.65,RED)
link('I2C_RTC','ESP32 to clock','esp_1','rtc',pins('rtc_sda','rtc_scl')+', 3V3/GND',1.6)
link('I2C_PWM','ESP32 to servo controller','esp_1','pca_i2c',pins('rtc_sda','rtc_scl','servo_outputs_enable')+', 3V3/GND',1.7)
link('I2C_PD','ESP32 to PD controller','esp_1','pd_i2c',pins('rtc_sda','rtc_scl')+', common GND',1.4)
link('Audio_amp','ESP32 to amplifier','esp_-1','amp_bus',pins('audio_bclk','audio_lrclk','amplifier_din'),1.6)
link('Audio_mic','ESP32 to microphone','esp_-1','mic',pins('audio_bclk','audio_lrclk','microphone_sd')+', 3V3/GND',1.65)
link('Speaker_pair','Amplifier to speaker','amp_out','speaker','SPK+ / SPK− only',1.25,[.55,.25,.17])
for i,name in enumerate(['neck_servo','left_shoulder_servo','right_shoulder_servo']):
    # Three adjacent 3.4 mm-pitch outlets need a lead envelope no wider
    # than the provisional 3.1 mm JR housing. Gauge the purchased leads.
    link(f'PWM_CH{i}',f'PCA9685 CH{i} to {name.replace("_"," ")}',f'pca_{i}',name,'PWM / 5 V / GND',1.55,[.75,.42,.16])
link('Record','Chest recording button','esp_1','talk_switch',pins('talk_button')+', ground; external pull-up',1.1)
link('Head_riser','Control wiring from body into neck','esp_head','neck_entry','14-wire head harness: signals, 3V3, 5 V and two grounds',3.25,[.46,.29,.57])
link('Head_joint','Head harness across the turning joint','neck_entry','head_bus','14-wire head harness through nominal 11 mm bore',3.25,[.46,.29,.57])
link('LCD_SPI','Neck harness to display','head_bus','lcd',pins('lcd_sck','lcd_mosi','lcd_cs','lcd_dc','lcd_reset')+', 3V3/GND',2)
link('Camera_power','Neck harness to camera board','head_bus','cam_power','Separate camera node, 5 V and GND',1.4,RED)
link('Camera_FPC','Camera board to lens','cam_fpc','lens_fpc','24-pin 75 mm flex with provisional flat clearance envelope',
     .4,[.82,.58,.16],ribbon=(13.5,.8))
for name in ['minus_switch','plus_switch','crown_left','crown_right','camera_LED']:
    signal={'minus_switch':'volume_down','plus_switch':'volume_up','crown_left':'pet_left','crown_right':'pet_right','camera_LED':'camera_activity_led'}[name]
    link(name,name.replace('_',' ').capitalize(),'head_bus',name,pins(signal),1.05)

print(f'Modelled {len(items)} hardware shapes and {len(routes)} cable bundles',flush=True)

catalog = json.loads((CAD/'preview-data.json').read_text())['parts']
shell = {}
for item in catalog:
    if item['hardware'] or item['region']=='coupon':
        continue
    shell[item['id']] = trimesh.load(CAD/item['stl'],force='mesh')
cover_prefixes=('Helmet_', 'Face_', 'Torso_', 'Hip_', 'Bottom_cover', 'Foot_', 'Sole_',
                'Shoulder_housing_', 'Chest_', 'Waist_', 'Crown_', 'Volume_', 'Cuff_',
                'Forearm_', 'Palm_', 'Record_button')
covers={name:mesh for name,mesh in shell.items() if name.startswith(cover_prefixes)}
fixtures={name:mesh for name,mesh in shell.items() if name not in covers}


def manager(meshes):
    tree=trimesh.collision.CollisionManager()
    for name,mesh in meshes.items():
        tree.add_object(name,mesh)
    return tree


def hits(tree,mesh):
    _, names = tree.in_collision_single(mesh,return_names=True)
    return sorted(names)


def sample_path(points, spacing=.5):
    return np.concatenate([
        np.linspace(a, b, math.ceil(float(np.linalg.norm(a-b))/spacing)+1)
        for a, b in zip(points, points[1:])
    ])


plastic_tree = manager(shell)
cover_tree = manager(covers)
collisions = []
by_owner={}
for item in items:
    by_owner.setdefault(item['owner'],[]).append(item['mesh'])
    found=hits(plastic_tree,item['mesh'])
    if found:
        collisions.append(dict(component=item['owner'],piece=item['id'].split('--')[-1],
                               kind=item['kind'],touches=found,
                               touches_cover=any(f in covers for f in found)))
bodies={owner:trimesh.util.concatenate(meshes) for owner,meshes in by_owner.items()}
component_contacts=[]
for a,b in combinations(bodies,2):
    x,y=bodies[a],bodies[b]
    if np.all(x.bounds[0]<=y.bounds[1]) and np.all(y.bounds[0]<=x.bounds[1]):
        if manager({a:x}).in_collision_single(y):
            component_contacts.append([a,b])
print('Checked rigid contacts against all shell and mount solids',flush=True)

# Check candidate cable corridors including the full occupied diameter.
# Cable contact at endpoints can be an intentional mating contact.
hardware_tree=manager(bodies)
endpoint_owners={'pd_terminal':'usb_c_pd_board','pd_i2c':'usb_c_pd_board','distribution':'power_distribution',
                 'rtc':'clock_board_and_cell','amp_out':'amplifier','amp_bus':'amplifier',
                 'mic':'microphone_board','speaker':'speaker','lcd':'display_pocket',
                 'cam_power':'camera_board','cam_fpc':'camera_board','lens_fpc':'camera_lens',
                 'esp_head':'esp32_board',
                 **{f'esp_{s}':'esp32_board' for s in (-1,1)},
                 **{f'pca_{n}':'pca9685_driver' for n in [0,1,2,'power','i2c']}}
fixture_tree = manager(fixtures)
for route in routes:
    own={endpoint_owners.get(route['start'],route['start']),
         endpoint_owners.get(route['end'],route['end'])}
    route['covers_hit']=hits(cover_tree,route['mesh'])
    route['supports_hit']=hits(fixture_tree,route['mesh'])
    route['other_parts_hit']=sorted(set(hits(hardware_tree,route['mesh']))-own)
    route['centerline_mm']=round(sum(float(np.linalg.norm(a-b)) for a,b in zip(route['points'],route['points'][1:])),1)

# Check wire-to-wire packing separately from clashes with modelled solids.
# Branches sharing a connector intentionally meet in its fan-out region.
fanout_mm = 9
route_samples = {r['id']: sample_path(r['points']) for r in routes}
bundle_contacts = []
for a, b in combinations(routes, 2):
    if a['ribbon_mm'] or b['ribbon_mm']:
        if hits(manager({a['id']:a['mesh']}), b['mesh']):
            bundle_contacts.append(dict(routes=[a['id'],b['id']], overlap_mm=None))
        continue
    x, y = route_samples[a['id']], route_samples[b['id']]
    combined_radius = a['radius_mm'] + b['radius_mm']
    if np.any(x.min(0) > y.max(0) + combined_radius) or np.any(y.min(0) > x.max(0) + combined_radius):
        continue
    distances = cdist(x, y)
    close = distances < combined_radius
    for junction in {a['start'], a['end']} & {b['start'], b['end']}:
        around_x = np.linalg.norm(x-ports[junction], axis=1) < fanout_mm
        around_y = np.linalg.norm(y-ports[junction], axis=1) < fanout_mm
        close &= ~(around_x[:, None] & around_y[None, :])
    if np.any(close):
        i, j = np.argwhere(close)[np.argmin(distances[close])]
        bundle_contacts.append(dict(routes=[a['id'], b['id']],
                                    overlap_mm=round(combined_radius-distances[i, j], 2),
                                    center_mm=np.round((x[i]+y[j])/2, 2).tolist()))
print('Checked candidate bundle corridors',flush=True)

# Sweep the provisional overmould and mating tip through the complete
# insertion, plus a gauge expanded by the specified CAD clearance.
def plug(mouth):
    tip=box((8.25,6.55,2.4),mouth+v(0,-3.275,0))
    grip=box(USB_PLUG,mouth+v(0,USB_PLUG[1]/2,0))
    return trimesh.util.concatenate([tip,grip])

rear=(58*scale)*math.sqrt(1-((pd_socket[2]-30*scale)/(30*scale))**2)
current_plug=plug(pd_socket)
# The continuous corridor box encloses every sampled plug position.
# Socket internal mating space is the only allowed USB-C component contact.
usb_travel=25
grip_sweep=box((USB_PLUG[0]+.6,USB_PLUG[1]+usb_travel,USB_PLUG[2]+.6),
              pd_socket+v(0,(USB_PLUG[1]+usb_travel)/2,0))
tip_sweep=box((8.85,6.55+usb_travel,3.0),pd_socket+v(0,(usb_travel-6.55)/2,0))
usb_path=trimesh.util.concatenate([grip_sweep,tip_sweep])
usb_hardware=manager({k:m for k,m in bodies.items() if k!='usb_c_pd_board'})
wire_tree=manager({r['id']: r['mesh'] for r in routes})
pd_result=dict(
    socket_mm=pd_socket.round(2).tolist(),
    panel_mm=[0,round(rear,2),round(pd_socket[2],2)],
    setback_mm=round(rear-pd_socket[1],2),
    height_offset_mm=0,
    opening_mm=[USB_WELL_WIDTH,USB_WELL_HEIGHT],
    tip_mm=6.55,plug_gauge_mm=list(USB_PLUG),clearance_per_side_mm=.3,
    seated_case_hits=hits(plastic_tree,current_plug),
    unplugged_insertion_hits=hits(plastic_tree,usb_path),
    insertion_hardware_hits=hits(usb_hardware,usb_path),
    insertion_wire_hits=hits(wire_tree,usb_path),
)
mcu_access=dict(test='Representative attached micro-USB overmold in current x-facing orientation',
                shell_hits=hits(cover_tree,mcu_plug))
mcu_insertion=[]
for travel in range(0,81,2):
    shifted=mcu_plug.copy()
    shifted.apply_translation([-travel,0,0])
    mcu_insertion.extend(hits(cover_tree,shifted))
mcu_access['closed_case_insertion_hits']=sorted(set(mcu_insertion))
service_objects={k:m for k,m in shell.items() if k!='Hip_rear'}
service_objects.update({k:m for k,m in bodies.items() if k!='esp32_board'})
mcu_service_tree=manager(service_objects)
mcu_corridor=box((103,12.6,7.6),mcu_plug.centroid-v(40,0,0))
mcu_access['rear_cover_removed_insertion_hits']=hits(mcu_service_tree,mcu_corridor)
mcu_access['rear_cover_removed_wire_hits']=hits(wire_tree,mcu_corridor)
mic_center=center('microphone_board')
grille_position=v(0,-58*scale*math.sqrt(1-((48-30)/30)**2),48*scale)
speaker_result=dict(
    diaphragm_gauge_hits=hits(cover_tree,speaker_excursion),
    diaphragm_to_grille_centerline_mm=round(abs(-58*scale*math.sqrt(1-((40.5-30)/30)**2)-
                                             (center('speaker')[1]-3.75)),1),
    mic_center_to_port_mm=round(float(np.linalg.norm(grille_position-mic_center)),1),
)
lens=center('camera_lens')
pupil=lens+v(0,-3.5,0)
camera_setback=pupil[1]-(-26*scale)
camera=dict(pupil_setback_mm=round(camera_setback,2),opening_mm=6,
            cone_angle_deg=round(math.degrees(2*math.atan2(3,camera_setback)),1),
            flex_route_mm=next(r['centerline_mm'] for r in routes if r['id']=='Camera_FPC'),
            flex_spec_mm=75, flex_envelope_mm=next(r['ribbon_mm'] for r in routes if r['ribbon_mm']))

# Rotate all parts carried by the head together. Keep the neck entry fixed.
head_ids={item['id'] for item in json.loads((CAD/'components.json').read_text())['components']
          if item['region']=='head'}
moving_head={name:mesh for name,mesh in bodies.items() if name in head_ids}
head_routes=[r for r in routes if r['start']=='head_bus' or r['id']=='Camera_FPC']
fixed_obstacles={f'CAD {name}':mesh for name,mesh in shell.items()
                 if not any(p['id']==name and p['region'] in ('head','L','R') for p in catalog)}
fixed_obstacles.update({f'Part {name}':mesh for name,mesh in bodies.items() if name not in head_ids})
head_route_ids={r['id'] for r in head_routes}
fixed_obstacles.update({f'Cable {r["id"]}':r['mesh'] for r in routes
                        if r['id'] not in head_route_ids | {'Head_joint', 'Head_riser'}})
fixed_tree=manager(fixed_obstacles)
motion=[]
for angle in range(-45,46,5):
    rot=trimesh.transformations.rotation_matrix(math.radians(angle),[0,0,1])
    pose_hits=[]
    for name,mesh in [*moving_head.items(),*((r['id'],r['mesh']) for r in head_routes)]:
        _, collisions_at_pose=fixed_tree.in_collision_single(mesh,transform=rot,return_names=True)
        if collisions_at_pose:pose_hits.append(dict(part=name,hits=sorted(collisions_at_pose)))
    motion.append(dict(yaw_deg=angle,contacts=pose_hits))
# Sweep the moving arm solids against the installed shoulder cables and
# motor bodies. Shell-to-shell coverage remains in the enclosure report.
arm_motion=[]
combined_motion=[]
head_equipment={**moving_head, **{r['id']:r['mesh'] for r in head_routes}}
head_joint_tree=manager(head_equipment)
head_bounds=np.asarray([mesh.bounds for mesh in head_equipment.values()])
head_min,head_max=head_bounds[:,0].min(axis=0),head_bounds[:,1].max(axis=0)
head_at_yaw={angle:trimesh.transformations.rotation_matrix(math.radians(angle),[0,0,1])
             for angle in range(-45,46,5)}
for side,sign in [('L',-1),('R',1)]:
    arm_mesh=trimesh.util.concatenate([shell[p['id']] for p in catalog
                                       if p['region']==side and p['id'] in shell])
    arm_corners=trimesh.bounds.corners(arm_mesh.bounds)
    anchors=v(sign*56*scale,0,94*scale)
    targets={name:mesh for name,mesh in bodies.items() if name not in moving_head}
    targets.update({r['id']:r['mesh'] for r in routes if r['id'] not in head_route_ids})
    target_tree=manager(targets)
    for angle in range(0,121,5):
        rot=trimesh.transformations.rotation_matrix(math.radians(-angle),[1,0,0],anchors)
        _, result=target_tree.in_collision_single(arm_mesh,transform=rot,return_names=True)
        if result:arm_motion.append(dict(side=side,lift_deg=angle,contacts=sorted(result)))
        for yaw, head_pose in head_at_yaw.items():
            relative_pose=head_pose.T @ rot
            posed_corners=trimesh.transform_points(arm_corners,relative_pose)
            if np.any(posed_corners.max(axis=0)<head_min) or np.any(posed_corners.min(axis=0)>head_max):
                continue
            _, result=head_joint_tree.in_collision_single(arm_mesh,transform=relative_pose,return_names=True)
            if result:
                combined_motion.append(dict(side=side,lift_deg=angle,yaw_deg=yaw,contacts=sorted(result)))
print('Checked panel access and connected motion samples',flush=True)

# Put the real panel-gauge failure and the wiring into the review layer.
items.append(dict(owner='usb_c_pd_board',id='usb_c_pd_board--mated_cable_gauge',mesh=current_plug,
                  color=[.86,.34,.16],kind='gauge'))
records = []
render_groups={}
for item in items:
    key=(item['owner'],item['kind'],tuple(item['color']))
    render_groups.setdefault(key,[]).append(item['mesh'])
for i,((owner,kind,color),meshes) in enumerate(render_groups.items()):
    records.append(dict(id=f'Fit_Hardware_{i}',owner=owner,kind=kind,
                        color=color,mesh=trimesh.util.concatenate(meshes)))
for route in routes:
    records.append(dict(id='Fit_Wire_'+route['id'],owner=route['id'],kind='wire',
                        color=route['color'],mesh=route['mesh']))
failed_owners={c['component'] for c in collisions}
if any(pd_result[key] for key in ('seated_case_hits', 'unplugged_insertion_hits',
                                 'insertion_hardware_hits', 'insertion_wire_hits')):
    failed_owners.add('usb_c_pd_board')
failed_routes={r['id'] for r in routes if r['covers_hit'] or r['supports_hit'] or r['other_parts_hit']}
flagged_wires = failed_routes | {name for item in bundle_contacts for name in item['routes']}
display = []
for item in records:
    mesh=item.pop('mesh')
    if len(mesh.faces)>14000:
        mesh=mesh.simplify_quadric_decimation(face_count=14000)
    triangles=mesh.triangles.reshape(-1,3)
    data=np.concatenate((triangles,np.repeat(mesh.face_normals,3,axis=0)),axis=1).astype('<f4')
    path=GEOMETRY/(item['id']+'.bin')
    path.write_bytes(data.tobytes())
    mesh.export(path.with_suffix('.stl'))
    base_region='head' if item['owner'] in head_ids or (item['kind']=='wire' and triangles[:,2].min()>=125) else 'fixed'
    display.append(dict(**item,path=str(path.relative_to(CAD)),count=len(data),
                        region=base_region,center=mesh.bounds.mean(axis=0).tolist(),
                        flagged=item['owner'] in (flagged_wires if item['kind']=='wire' else failed_owners)))

payload=dict(
    scale=scale,components=components,meshes=display,pd_transform_mm=pd_offset.tolist(),
    rigid_contacts=collisions,component_contacts=component_contacts,
    routes=[{**{k:p for k,p in r.items() if k not in ('points','mesh')},
             'points_mm':[np.round(x,3).tolist() for x in r['points']]} for r in routes],
    usb_c=pd_result,micro_usb=mcu_access,audio=speaker_result,camera=camera,
    wire_pair_contacts=bundle_contacts, shared_fanout_mm=fanout_mm,
    service_checks_passed=not (failed_owners or component_contacts or flagged_wires or arm_motion
                               or combined_motion or any(p['contacts'] for p in motion)
                               or mcu_access['rear_cover_removed_insertion_hits']
                               or mcu_access['rear_cover_removed_wire_hits']),
    neck_passage_mm=11,bundle_outer_diameter_mm=6.5,head_sweep=motion,arm_contacts=arm_motion,
    combined_motion_contacts=combined_motion, combined_motion_samples=len(head_at_yaw)*2*25,
)
(OUT/'connected-fit.json').write_text(json.dumps(payload,indent=2)+'\n')
print('Fit data saved',flush=True)
