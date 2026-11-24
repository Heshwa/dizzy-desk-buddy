"""Fail the connected CAD regression if a service path or clearance reopens."""

import json
from pathlib import Path

import trimesh

CAD = Path(__file__).resolve().parents[1]
fit = json.loads((CAD / 'fit-study/connected-fit.json').read_text())
geometry = json.loads((CAD / 'reports/validation.json').read_text())
usb = fit['usb_c']
programmer = fit['micro_usb']
routes = fit['routes']
expected_routes = json.loads(Path(__file__).with_name('service_routes.json').read_text())


def collision_control(part, gauge):
    tree = trimesh.collision.CollisionManager()
    tree.add_object(part, trimesh.load(CAD / 'output/stl' / f'{part}.stl', force='mesh'))
    return tree.in_collision_single(gauge)


# Deliberate faults prove that the fitted assemblies still expose the
# expected contact surfaces. These gauges are only diagnostic.
x, y, z = usb['panel_mm']
plug_width, _, plug_height = usb['plug_gauge_mm']
shifted_plug = trimesh.creation.box(extents=(plug_width, 14, plug_height))
shifted_plug.apply_translation((x, y, z + 4.26))
oversize_harness = trimesh.creation.cylinder(radius=6, height=4, sections=32)
oversize_harness.apply_translation((0, 0, 120))

checks = {
    'Seated and continuous rear USB-C insertion': all(not usb[field] for field in (
        'seated_case_hits', 'unplugged_insertion_hits', 'insertion_hardware_hits', 'insertion_wire_hits',
    )),
    'ESP32 programming with rear hip cover removed': not (
        programmer['rear_cover_removed_insertion_hits'] or programmer['rear_cover_removed_wire_hits']
    ),
    'Modelled components and their mounts': not (fit['rigid_contacts'] or fit['component_contacts']),
    'All declared cable envelopes': {r['id'] for r in routes} == set(expected_routes) and all(
        not (r['covers_hit'] or r['supports_hit'] or r['other_parts_hit']) for r in routes
    ),
    'Cable spacing outside shared connector fan-outs': not fit['wire_pair_contacts'],
    'Full-length flat camera ribbon': (
        fit['camera']['flex_route_mm'] == fit['camera']['flex_spec_mm'] == 75
        and fit['camera']['flex_envelope_mm'] == [13.5, .8]
    ),
    'Head articulation from -45 to +45 degrees': [p['yaw_deg'] for p in fit['head_sweep']] == list(range(-45, 46, 5))
    and all(not p['contacts'] for p in fit['head_sweep']),
    'Both shoulders and combined head poses': (
        fit['combined_motion_samples'] == 950 and not fit['arm_contacts'] and not fit['combined_motion_contacts']
    ),
    'Printable meshes and nominal service routes': all(
        m['watertight'] and m['winding_consistent'] for m in geometry['meshes']
    ) and all(p['clear'] for p in geometry['removal_paths']) and not geometry['rigid_motion']['collisions'],
    'Original Webots meshes unchanged': geometry['reference_assets_unchanged'],
    'Misaligned USB-C plug is blocked': collision_control('Hip_rear', shifted_plug),
    'Oversized head harness is blocked by its bore': collision_control('Neck_hollow_hub', oversize_harness),
}
for label, passed in checks.items():
    print(('PASS ' if passed else 'FAIL ') + label)
raise SystemExit(0 if all(checks.values()) and fit['service_checks_passed'] else 1)
