"""Generate review meshes, crease-aware normals and the part catalog."""
from pathlib import Path
import csv
import json
import math

import numpy as np
import trimesh

CAD = Path(__file__).resolve().parents[1]
OUT = CAD / 'output'
REPORT = CAD / 'reports'
checks = json.loads((REPORT / 'checks.json').read_text())
scale = checks['scale']
manifest = {item['id']: item for item in json.loads((CAD / 'components.json').read_text())['components']}
colors = {
    'ivory': [.95, .915, .85],
    'accent': [.68, .34, .23],
    'mount': [.27, .50, .48],
    'black': [.035, .054, .060],
}
mount_prefixes = ('Carrier', 'Retainer', 'Clip_', 'Harness', 'Neck_', 'Horn_',
                  'Shoulder_bearing', 'Passive', 'LED_holder', 'Lens_', 'USB_', 'Shutter_rails')
accent_prefixes = ('Face_bezel', 'Cuff_', 'Volume_', 'Waist_', 'Record_', 'Crown_', 'Sole_', 'Foot_pad')
dark_prefixes = ('Face_insert', 'Camera_shutter', 'Speaker_gasket')
catalog = list(csv.DictReader((REPORT / 'parts.csv').open()))
models = []
mesh_checks = []


def shading_buffer(mesh, name):
    normals = mesh.face_normals
    corners = mesh.faces.flatten()
    face_of_corner = np.repeat(np.arange(len(mesh.faces)), 3)
    output = np.empty((len(corners), 6), dtype='<f4')
    output[:, :3] = mesh.vertices[corners]
    # A single geometric vertex can belong to a smooth skin and to a crisp
    # mating face. Average only neighbours within 48 degrees of this face.
    incident = mesh.vertex_faces
    weights = mesh.area_faces
    for start in range(0, len(corners), 8192):
        section = slice(start, start + 8192)
        neighbours = incident[corners[section]]
        face_normals = normals[face_of_corner[section]]
        aligned = np.einsum('ijk,ik->ij', normals[neighbours], face_normals)
        influence = np.where((neighbours >= 0) & (aligned > math.cos(math.radians(48))),
                             np.sqrt(weights[neighbours]), 0)
        sums = np.einsum('ij,ijk->ik', influence, normals[neighbours])
        lengths = np.linalg.norm(sums, axis=1)
        output[section, 3:] = np.divide(sums, lengths[:, None], out=face_normals.copy(),
                                     where=lengths[:, None] > 1e-12)
    if name.startswith(('Helmet_', 'Crown_inlay_')):
        # These skins come from known concentric ellipsoids. Use their
        # continuous normal field to remove shading bands at trim vertices.
        center = np.array([0, 0, 157 * scale])
        outer_radii = np.array([51, 43, 46]) * scale
        offset = output[:, :3] - center
        face_normals = normals[face_of_corner]
        wall = json.loads((CAD / 'parameters.json').read_text())['wall_mm']
        for layer in (0, 1.5, wall):
            radii = outer_radii - layer
            level = np.einsum('ij,ij->i', offset / radii, offset / radii)
            smooth = offset / radii**2
            smooth /= np.linalg.norm(smooth, axis=1)[:, None].clip(1e-12)
            orientation = np.einsum('ij,ij->i', smooth, face_normals)
            matched = (np.abs(level - 1) < .003) & (np.abs(orientation) > .86)
            output[matched, 3:] = smooth[matched] * np.sign(orientation[matched, None])
    return output


def describe_part(name, region, material):
    if region == 'coupon':
        return 'Fit samples', colors['mount']
    if name.startswith(mount_prefixes):
        return 'Mounts and retainers', colors['mount']
    color = colors['black'] if name.startswith(dark_prefixes) else (
        colors['accent'] if name.startswith(accent_prefixes) else colors['ivory'])
    if region == 'head':
        return 'Helmet and face', color
    if region in ('L', 'R') or name.startswith('Shoulder_housing'):
        return 'Shoulders and hands', color
    return 'Torso and base', color


def add_view(name, mesh, color, group, region, **fields):
    path = OUT / 'webots' / (name + '.bin')
    buffer = shading_buffer(mesh, name)
    path.write_bytes(buffer.tobytes())
    models.append(dict(
        id=name, path=str(path.relative_to(CAD)), count=len(buffer), color=color,
        group=group, region=region, center=mesh.bounds.mean(axis=0).tolist(),
        size_mm=np.round(mesh.extents, 2).tolist(), **fields
    ))


for row in sorted(catalog, key=lambda entry: entry['part']):
    name, region, material = row['part'], row['region'], row['material']
    folder = 'calibration' if region == 'coupon' else 'stl'
    source = OUT / folder / (name + '.stl')
    mesh = trimesh.load(source, force='mesh')
    group, color = describe_part(name, region, material)
    high_detail = name.startswith(('Helmet_', 'Crown_inlay_'))
    limit = 55000 if high_detail else 16000
    view = mesh.simplify_quadric_decimation(face_count=limit) if len(mesh.faces) > limit else mesh
    add_view(name, view, color, group, region, hardware=False, material=material,
             stl=str(source.relative_to(CAD)), step='output/step/' + name + '.step',
             mass_g=float(row['estimated_mass_g']))
    if region != 'coupon':
        simulation = view.simplify_quadric_decimation(face_count=20000) if len(view.faces) > 20000 else view.copy()
        simulation.apply_scale(.001)
        simulation.export(OUT / 'webots' / (name + '.obj'), include_normals=True)
    mesh_checks.append(dict(part=name, watertight=bool(mesh.is_watertight),
                            winding_consistent=bool(mesh.is_winding_consistent),
                            connected_meshes=len(mesh.split()), bounds_mm=mesh.extents.round(3).tolist()))

for entry in checks['hardware_envelopes']:
    name = entry['id']
    if name == 'speaker':
        mesh = trimesh.creation.cylinder(radius=18, height=13, sections=48)
        mesh.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))
    else:
        mesh = trimesh.creation.box(extents=entry['size_mm'])
    mesh.apply_translation(entry['center_mm'])
    info = manifest[name]
    region = 'head' if info['region'] == 'head' else 'fixed'
    add_view('HW_' + name, mesh, [.35, .65, .53], 'Hardware allowances', region,
             hardware=True, material='Fit envelope', title=info['role'].capitalize())

# The active display is a purchased part. Its glass face is shown in context.
screen = trimesh.creation.cylinder(radius=16.2, height=.3, sections=96)
screen.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))
screen.apply_translation([0, -26 * scale + 1.5, 157 * scale - 2.5])
add_view('LCD_visible', screen, [.03, .055, .065], 'Hardware allowances', 'head',
         hardware=True, material='Display surface', title='GC9A01 active display', visible_exterior=True)
screen.apply_scale(.001)
screen.export(OUT / 'webots' / 'LCD_visible.obj', include_normals=True)

(CAD / 'preview-data.json').write_text(json.dumps(dict(scale=scale, parts=models), indent=2))
(REPORT / 'mesh-checks.json').write_text(json.dumps(mesh_checks, indent=2) + '\n')
print('Preview models:', len(models), '| watertight STL files:', sum(m['watertight'] for m in mesh_checks))
