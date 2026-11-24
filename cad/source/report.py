"""Summarize the directly measured validation outputs."""
from pathlib import Path
from collections import Counter
import json
CAD=Path(__file__).resolve().parents[1]
reports=CAD/'reports'
build=json.loads((reports/'checks.json').read_text())
review=json.loads((reports/'validation.json').read_text())
scale=build['scale']
check=build['checks']
measured=lambda name:[item for item in check if item['name'].startswith(name)]
passed=lambda items:sum(item['passed'] for item in items)
mesh=review['meshes']
motion=review['rigid_motion']
paths=review['removal_paths']
solid=measured('solid:')
bed=measured('print-volume:')
contacts=Counter(tuple(sorted(parts)) for pose in motion['collisions'] for parts in pose['parts'])
overlaps=build['envelope_collisions']
text=f"""# Dizzy CAD validation

The candidate is {scale:.3f} times the Webots exterior, with an approximate nominal height of {203*scale:.1f} mm. The physical component allowances use millimetres and remain unscaled. See the source measurement sheet for unresolved interfaces.

| Check | Result |
|---|---|
| Original mesh hashes | {'Unchanged' if review['reference_assets_unchanged'] else 'Changed, review needed'} |
| Closed, valid, single CAD solids | {passed(solid)} / {len(solid)} |
| Watertight STL with consistent face winding | {sum(x['watertight'] and x['winding_consistent'] for x in mesh)} / {len(mesh)} |
| Part bounds within 180 mm on each axis | {passed(bed)} / {len(bed)} |
| Component envelope overlaps with checked solids | {len(overlaps)} |
| Component envelopes touching or overlapping each other | {len(review.get('hardware_intersections',[]))} |
| Sampled removal routes clear in nominal geometry | {sum(p['clear'] for p in paths)} / {len(paths)} |
| Sampled rigid poses with intersections | {len(motion['collisions'])} |
| Left and right moving printed mass | {next(x['estimated_mass_g'] for x in check if x['name']=='Arm mass L')} g and {next(x['estimated_mass_g'] for x in check if x['name']=='Arm mass R')} g, using solid PETG density |

The motion check samples each joint against the fixed shell at 5° increments, then checks {motion['pose_pair_tests']} pairs of sampled moving poses. Separate combinations cover head/left, head/right and left/right. It omits intended bearing fits, loads and flexible cables. The removal check translates each component allowance through its identified service side, with the designated cover and its own retainer removed. It samples straight and offset paths. Individual retainers and wiring are outside this route check. Any unresolved path needs a revised placement or more realistic measured geometry.

## Exterior comparison

The silhouettes compare the CAD exports to the uniformly scaled Webots meshes in four projections, at 0.25 mm per pixel. The comparison includes outline changes from openings, seams and attachment geometry. It measures projected outlines, so hidden surface and wall thickness require separate checks.

| View | 95th percentile | Maximum | 0.75 mm maximum target |
|---|---:|---:|---|
"""
for r in review['silhouettes']:
    text+=f"| {r['view']} | {r['percentile95_mm']} mm | {r['max_mm']} mm | {'Pass' if r['passes_max_0p75'] else 'Review'} |\n"
text+="\n## Wall samples\n\nThese rays sample the broad surfaces, including seam and opening areas when hit. The minimum is a screen for locally thin sections. It is not a complete wall map.\n\n| Part | Minimum | 10th percentile | Rays |\n|---|---:|---:|---:|\n"
for r in review.get('wall_samples',[]):
    text+=f"| {r['part']} | {r['minimum_mm']} mm | {r['percentile10_mm']} mm | {r['samples']} |\n"
text+="\n## Findings that still need work\n\n"
for item in solid+bed:
    if not item['passed']:text+=f"- {item['name']} needs geometry review.\n"
for r in mesh:
    if not r['watertight'] or not r['winding_consistent']:text+=f"- {r['part']} needs STL repair before slicing.\n"
for r in overlaps:
    text+=f"- {r['component']} intersects {r['part']} by {r['overlap_mm3']} mm³.\n"
for r in review.get('kernel_fallback_checks',[]):
    text+=f"- The solid kernel could not resolve {r['component']} against {r['part']}. The exported mesh check {'found intersection' if r['intersection'] else 'found clearance'} with a surface gap of {r['mesh_surface_gap_mm']} mm.\n"
for a,b in contacts:
    text+=f"- Motion contact between {a} and {b} at {contacts[a,b]} sampled poses.\n"
for r in paths:
    if not r['clear']:text+=f"- {r['component']} removal toward {r['direction']} is obstructed by {', '.join(r['blocking_geometry'])}.\n"
if (reports/'webots-poses.txt').exists():
    text+="\nThe separate Webots world ran all six commanded poses. The controller checked its pose fields at rest and at the end stops.\n"
text+="\nThe 0.75 mm appearance target, board placement, fastener engagement, independent removal and motion have separate acceptance checks. Any result marked for review remains open. The prototype requires measured boards and horns before mechanical release. Wall minima around openings, real connector and cable bends, touch, acoustics, heat, servo loads, tipping and durability still need physical verification. Print the calibration samples first.\n"
(reports/'VALIDATION.md').write_text(text)
print('Wrote',reports/'VALIDATION.md')
