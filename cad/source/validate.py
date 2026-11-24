"""Check exported objects, articulation and component removal paths."""
from itertools import product
from pathlib import Path
import hashlib
import json
import math

import numpy as np
import trimesh
from PIL import Image, ImageDraw
from scipy.ndimage import binary_erosion, distance_transform_edt

ROOT = Path(__file__).resolve().parents[2]
CAD = ROOT / 'cad'
OUT = CAD / 'output'
REPORT = CAD / 'reports'
data = json.loads((CAD / 'preview-data.json').read_text())
build = json.loads((REPORT / 'checks.json').read_text())
components = json.loads((CAD / 'components.json').read_text())['components']
scale = data['scale']
parts = {p['id']: p for p in data['parts'] if not p['hardware'] and p['region']!='coupon'}
meshes = {name: trimesh.load(OUT / 'stl' / (name + '.stl'), force='mesh') for name in parts}
all_solids = {**meshes, **{path.stem: trimesh.load(path, force='mesh') for path in (OUT / 'calibration').glob('*.stl')}}
def collision_manager(names):
    manager = trimesh.collision.CollisionManager()
    for name in names:
        manager.add_object(name, meshes[name])
    return manager
def rotation(deg, axis, base):
    return trimesh.transformations.rotation_matrix(math.radians(deg), axis, np.array(base)*scale)

# Moving exterior and bridge parts checked against fixed structure, then one another.
# Intentional shaft-bearing mating surfaces are omitted from the rigid interference list.
moving = {reg: [name for name,p in parts.items() if p['region']==reg and name.startswith(('Helmet','Face','Crown','Volume','Forearm','Palm','Cuff','Horn_adapter'))]
          for reg in ('head','L','R')}
fixed = [name for name,p in parts.items() if p['region']=='fixed' and name.startswith(('Torso','Hip_', 'Shoulder_housing','Foot_','Sole','Waist','Chest','Record_','Bottom_cover'))]
static = collision_manager(fixed)
managers = {reg: collision_manager(names) for reg,names in moving.items()}
transforms = {
    'head': {a: rotation(a,(0,0,1),(0,0,109.5)) for a in range(-45,46,5)},
    **{reg: {a: rotation(a,(-1,0,0),(sign*56,0,94)) for a in range(0,121,5)} for reg,sign in [('L',-1),('R',1)]},
}
def move(reg, angle):
    for name in moving[reg]:
        managers[reg].set_transform(name, transforms[reg][angle])
def collisions(a,b):
    found,pairs=a.in_collision_other(b,return_names=True)
    return [list(pair) for pair in sorted(pairs)] if found else []
rigid_results=[]
for reg in transforms:
    for angle in transforms[reg]:
        move(reg,angle)
        pairs=collisions(managers[reg],static)
        if pairs:rigid_results.append(dict(groups=[reg,'fixed'],angles=[angle],parts=pairs))
for first,second in [('head','L'),('head','R'),('L','R')]:
    for a,b in product(transforms[first],transforms[second]):
        move(first,a);move(second,b)
        pairs=collisions(managers[first],managers[second])
        if pairs:rigid_results.append(dict(groups=[first,second],angles=[a,b],parts=pairs))
print('Articulation collision sets:',len(rigid_results),flush=True)

# Check straight-line removal of each envelope with its own retainer and the
# designated exterior service cover removed. Rotation and real cable bends
# require physical samples and are intentionally outside this sweep.
access = {'front':[0,-1,0],'rear':[0,1,0],'left':[-1,0,0],'bottom':[0,0,-1],'top':[0,0,1]}
envelopes = {}
for p in build['hardware_envelopes']:
    model = trimesh.creation.box(extents=p['size_mm'])
    if p['id']=='speaker':
        model=trimesh.creation.cylinder(radius=18,height=13)
        model.apply_transform(rotation(90,(1,0,0),(0,0,0)))
    model.apply_translation(p['center_mm']);envelopes[p['id']]=model
hardware_manager=trimesh.collision.CollisionManager()
for name,envelope in envelopes.items():
    hardware_manager.add_object(name,envelope)
_, hardware_intersections=hardware_manager.in_collision_internal(return_names=True)
fallback=[]
for check in build.get('undetermined_intersections',[]):
    name=check['component']
    target=check['part']
    manager=collision_manager([target])
    collision=manager.in_collision_single(envelopes[name])
    fallback.append(dict(component=name,part=target,intersection=collision,
                         mesh_surface_gap_mm=round(float(manager.min_distance_single(envelopes[name])),3)))
removal=[]
cover = {
    ('head','front'):('Face_bezel','Face_insert','Shutter','Camera_shutter','Lens_flex_support','LED_holder'),
    ('head','rear'):('Helmet_rear',),
    ('head','top'):('Crown_inlay_',),
    ('torso','front'):('Torso_front','Chest_inset','Record_button','Waist_band'),
    ('torso','rear'):('Torso_rear',),
    ('hips','front'):('Hip_front','Foot_','Sole_insert_'),
    ('hips','rear'):('Hip_rear',),
    ('hips','bottom'):('Bottom_cover',),
    ('hips','left'):('Hip_front','Hip_rear'),
}
def service_direction(direction, name):
    if direction == 'side':
        side = 'L' if name.startswith('left') else 'R'
        return np.array([-1 if side=='L' else 1,0,0]), ('Shoulder_housing_'+side,)
    if direction == 'right':
        return np.array([1,0,0]), ()
    return np.array(access[direction]), ()

def route_hits(obstacles, envelope, route, sample_mm=2):
    hits=set()
    origin=np.zeros(3)
    for goal in route:
        for fraction in np.linspace(0,1,max(2,int(np.linalg.norm(goal-origin)/sample_mm)+1)):
            transform=trimesh.transformations.translation_matrix(origin+(goal-origin)*fraction)
            found,names=obstacles.in_collision_single(envelope,transform=transform,return_names=True)
            if found:hits.update(names)
        origin=goal
    return hits

alternative={
    'pca9685_driver':('rear','front'),
    'clock_board_and_cell':('rear','front','bottom'),
    'audio_capacitor':('front','rear'),
    'power_distribution':('rear','front'),
    'minus_switch':('left','rear'),
    'plus_switch':('right','rear'),
}
for item in components:
    name=item['id'];region=item['region'];direction=item['removal']
    best=None
    for side in dict.fromkeys((direction,*alternative.get(name,()))):
        vector,extra=service_direction(side,name)
        cover_names=cover.get((region,side),())+extra
        if name=='pca9685_driver' and side=='front':
            cover_names+=('Torso_front','Chest_inset','Waist_band','Record_button')
        # Ear caps release their own switch. No unrelated electronic part is removed.
        if name in ('minus_switch','plus_switch'):
            cover_names+=('Volume_cap_'+('L' if name=='minus_switch' else 'R'),)
        manager=trimesh.collision.CollisionManager()
        for other,mesh in envelopes.items():
            if other!=name:manager.add_object('HW_'+other,mesh)
        for other in fixed+moving['head']:
            if not other.startswith(cover_names):manager.add_object(other,meshes[other])
        base=vector*85
        candidates=[[base]]
        sensor=side=='top' and name.startswith('crown_')
        if sensor:
            # Drop below the curved retaining ledge, offset toward the centre,
            # and then lift the thin electrode through the circular opening.
            inward=7 if name=='crown_left' else -7
            candidates.insert(0,[np.array([0,0,-1.5]),np.array([inward,0,-1.5]),
                                 np.array([inward,0,85])])
        for axis in range(3):
            if vector[axis]!=0:continue
            for length in (-20,-16,-12,-8,-4,4,8,12,16,20):
                offset=np.eye(3)[axis]*length
                for lead in (0,5,10):
                    candidates.append([vector*lead,vector*lead+offset,base+offset])
        for route in candidates:
            hits=route_hits(manager,envelopes[name],route, .33 if sensor else 2)
            state=dict(component=name,direction=side,clear=not hits,blocking_geometry=sorted(hits),
                       removed_cover_prefixes=cover_names,waypoints_mm=[p.tolist() for p in route])
            if best is None or len(hits)<len(best['blocking_geometry']):best=state
            if not hits:break
        if best['clear']:break
    removal.append(best)
print('Nominal removal paths clear:',sum(p['clear'] for p in removal),'/',len(removal),flush=True)

# Front, side, rear, and 3/4 projected silhouette distance. 4 px/mm.
reference = [
    ('head-shell',(0,0,157)),('bezel',(0,0,157)),('face-glass',(0,0,157)),('crown-marks',(0,0,157)),
    ('volume_down',(0,0,157)),('volume_up',(0,0,157)),('body',(0,0,64.5)),('waist',(0,0,64.5)),
    ('chest',(0,0,0)),('hips',(0,0,30)),('talk',(0,0,0)),
]
for sign,name in [(-1,'left'),(1,'right')]:
    reference.extend([('foot',(sign*28,-60,30)),('sole',(sign*28,-60,30)),
                      ('shoulder-housing',(sign*36,0,94)),
                      *[(name+'-'+suffix,(sign*66,0,79)) for suffix in ('sleeve','cuff','palm')]])
ref=[]
for name,center in reference:
    mesh=trimesh.load(ROOT/'assets'/('dizzy-'+name+'.obj'),force='mesh')
    mesh.apply_scale(1000*scale);mesh.apply_translation(np.array(center)*scale);ref.append(mesh)
for sign in (-1,1):
    ear=trimesh.creation.cylinder(radius=14*scale,height=4*scale,sections=48)
    ear.apply_transform(rotation(90,(0,1,0),(0,0,0)))
    ear.apply_translation(np.array([sign*50.5,0,157])*scale)
    ref.append(ear)
    pad=trimesh.creation.cylinder(radius=1,height=2,sections=48)
    pad.vertices*=np.array([8,9,1])*scale
    pad.apply_translation(np.array([sign*28,-60,1])*scale)
    ref.append(pad)
neck=trimesh.creation.cylinder(radius=14*scale,height=10*scale)
neck.apply_translation([0,0,113.5*scale])
ref.append(neck)
exterior_names = [name for name in (*fixed,'Neck_retaining_ring','Neck_hollow_hub','Neck_bearing_seat',*moving['head'],*moving['L'],*moving['R']) if not name.startswith('Horn_adapter')]
def silhouette(list_of_meshes,yaw):
    img=Image.new('1',(1024,1024));draw=ImageDraw.Draw(img)
    p=math.radians(yaw)
    for mesh in list_of_meshes:
        vs=mesh.vertices
        xy=np.column_stack((512+4*(vs[:,0]*math.cos(p)+vs[:,1]*math.sin(p)),960-4*vs[:,2]))
        for tri in xy[mesh.faces]:draw.polygon([tuple(v) for v in tri], fill=1)
    from scipy.ndimage import binary_fill_holes, binary_closing
    return binary_fill_holes(binary_closing(np.asarray(img),iterations=2))
silhouettes=[]
for view,yaw in [('Front',0),('Side',90),('Rear',180),('Three-quarter',35)]:
    original=silhouette(ref,yaw);prototype=silhouette([meshes[n] for n in exterior_names],yaw)
    a=original^binary_erosion(original);b=prototype^binary_erosion(prototype)
    errors=np.concatenate((distance_transform_edt(~a)[b],distance_transform_edt(~b)[a]))/4
    silhouettes.append(dict(view=view,max_mm=round(float(errors.max()),2),percentile95_mm=round(float(np.percentile(errors,95)),2),passes_max_0p75=bool(errors.max()<=.75),raster_mm_per_pixel=.25))
    rgba=np.full((1024,1024,3),[234,240,236],dtype='uint8')
    rgba[original]=[93,149,137]
    rgba[prototype]=[185,108,79]
    rgba[original&prototype]=[52,73,69]
    Image.fromarray(rgba).save(REPORT/('overlay-'+view.lower()+'.png'))
# Measure a deterministic set of wall-ray lengths at triangle interiors.
# This screens broad skins. Sharp edges and build anisotropy need real inspection.
wall_checks=[]
rng=np.random.default_rng(492)
for name in ('Helmet_front','Helmet_rear','Torso_front','Torso_rear','Hip_front','Hip_rear','Forearm_L','Forearm_R'):
    mesh=meshes[name]
    areas=mesh.area_faces
    faces=rng.choice(len(areas),220,p=areas/areas.sum())
    positions=mesh.triangles_center[faces]
    normals=mesh.face_normals[faces]
    hits,rays,_=mesh.ray.intersects_location(positions-.02*normals,-normals,multiple_hits=False)
    thickness=np.linalg.norm(hits-positions[rays],axis=1)
    wall_checks.append(dict(part=name,samples=len(thickness),minimum_mm=round(float(thickness.min()),2),
                            percentile10_mm=round(float(np.percentile(thickness,10)),2)))
mesh_results=[dict(part=name,watertight=bool(m.is_watertight),winding_consistent=bool(m.is_winding_consistent),max_edge_mm=round(float(m.extents.max()),3))
              for name,m in sorted(all_solids.items())]
ref_hashes=json.loads((CAD/'reference/asset-hashes.json').read_text())
preserved=all(hashlib.sha256((ROOT/'assets'/name).read_bytes()).hexdigest()==digest for name,digest in ref_hashes.items())
report=dict(hardware_intersections=[list(pair) for pair in sorted(hardware_intersections)],
            kernel_fallback_checks=fallback,wall_samples=wall_checks,meshes=mesh_results,rigid_motion=dict(step_degrees=5,pose_pair_tests=2*19*25+25*25,
    collisions=rigid_results,scope='Triangle interference at discrete poses, excludes bearing and live loads'),
    removal_paths=removal,silhouettes=silhouettes,reference_assets_unchanged=preserved)
(REPORT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('Watertight and consistently wound',sum(p['watertight'] and p['winding_consistent'] for p in mesh_results),'/',len(mesh_results),flush=True)
print('Silhouettes',silhouettes,flush=True)
