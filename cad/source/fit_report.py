"""Write connected-fit results and the wiring schedule from the tested solids."""
import csv
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / 'fit-study'
data = json.loads((OUT / 'connected-fit.json').read_text())
usb = data['usb_c']
micro = data['micro_usb']
audio = data['audio']
cam = data['camera']
routes = data['routes']


def status(hits):
    return ', '.join(hits) if hits else 'Clear'


with (OUT / 'wiring-routes.csv').open('w', newline='') as stream:
    writer = csv.writer(stream)
    writer.writerow(['Route', 'Nets', 'From', 'To', 'Centreline mm', 'Envelope mm',
                     'Cover contacts', 'Support contacts', 'Other hardware contacts'])
    for route in routes:
        envelope = ' × '.join(f'{d:g}' for d in route['ribbon_mm']) if route['ribbon_mm'] else f"Ø {2*route['radius_mm']:g}"
        writer.writerow([route['label'], route['pins'], route['start'], route['end'],
                         route['centerline_mm'], envelope, ', '.join(route['covers_hit']),
                         ', '.join(route['supports_hit']), ', '.join(route['other_parts_hit'])])

route_contacts = [r for r in routes if r['covers_hit'] or r['supports_hit'] or r['other_parts_hit']]
head_ok = sum(not pose['contacts'] for pose in data['head_sweep'])
combined = data['combined_motion_samples']
verdict = 'The revised design passes the CAD service checks.' if data['service_checks_passed'] else 'Some CAD service checks still need review.'
usb_hits = sorted(set(usb['seated_case_hits'] + usb['unplugged_insertion_hits'] +
                      usb['insertion_hardware_hits'] + usb['insertion_wire_hits']))
programming_hits = sorted(set(micro['rear_cover_removed_insertion_hits'] + micro['rear_cover_removed_wire_hits']))
report = f"""# Dizzy connected fit review

**{verdict}** The physical prototype still requires measured plugs and boards, a small calibration print and unpowered dry-fit before the complete enclosure is printed.

The first connected review found a blocked rear USB-C inlet, nine modelled component contacts and reported two clear cable routes. The revised case centres a {usb['opening_mm'][0]:g} × {usb['opening_mm'][1]:g} mm pocket on the recessed socket. The ESP32 tray has header slots and programming-plug relief. The LCD, servo-driver and microphone retainer bridges moved off the connector areas. The neck bridge has splined-shaft clearance, the nearby capacitor carrier moved, and cable entries were opened through the inboard shoulder shells. The exterior scale stays at +7.5%.

Open **Connected fit** in the CAD preview to show the installed hardware, removable covers and cable paths. The Adafruit 5807 uses the manufacturer model. Other hardware combines published dimensions with provisional vendor-specific features. The cable elbow meshes are centred on the route waypoints. This corrects an error in the first study that placed some elbows at the assembly origin and could incorrectly flag the bottom cover.

## Repeated CAD tests

| Check | Result |
|---|---|
| Modelled rigid components | {len(data['component_contacts'])} component-pair contacts and {len(data['rigid_contacts'])} contacts with shells, trays or retainers. |
| Rear USB-C access | **{status(usb_hits)}**. The seated and full insertion gauges clear when no contacts are listed. The {usb['plug_gauge_mm'][0]:g} × {usb['plug_gauge_mm'][2]:g} mm overmould gauge and tip were swept through a continuous corridor with {usb['clearance_per_side_mm']:g} mm added on each side. Socket recess {usb['setback_mm']:.2f} mm. The sweep includes shells, mounts, unrelated hardware and cable routes. |
| ESP32 programming | **{status(programming_hits)}** with the rear hip cover removed. The closed case still obstructs the approach at {status(micro['closed_case_insertion_hits'])}. |
| Cable routes | {len(routes)-len(route_contacts)}/{len(routes)} clear the checked covers, mounts and unrelated modelled hardware. {len(data['wire_pair_contacts'])} sampled wire-pair overlaps outside shared connector fan-outs. |
| Camera ribbon | {cam['flex_route_mm']:g} mm service loop checked as a {cam['flex_envelope_mm'][0]:g} × {cam['flex_envelope_mm'][1]:g} mm flat envelope. |
| Head articulation | {head_ok}/{len(data['head_sweep'])} samples clear at 5° steps across ±45°. The assumed {data['bundle_outer_diameter_mm']:g} mm harness clears the {data['neck_passage_mm']:g} mm bore. |
| Shoulder articulation | {50-len(data['arm_contacts'])}/50 individual 0–120° arm poses and {combined-len(data['combined_motion_contacts'])}/{combined} combined arm and head poses clear the checked installed parts and cable envelopes. |

The routing check uses swept bundle envelopes against solids and half-millimetre centreline samples for bundle spacing. Branches sharing a connector may meet within a {data['shared_fanout_mm']} mm fan-out. JR servo leads use a provisional 3.1 mm envelope at 3.4 mm socket pitch. Measure effective bundle widths and add bend and pull relief on the real harness. The sampled head harness envelope stays on the yaw axis. Cable twist, bend radii, connector engagement and screw/tool access require the physical fit test.

## Outstanding prototype checks

- Camera optics and ribbon. The {cam['opening_mm']} mm aperture with {cam['pupil_setback_mm']:.1f} mm setback yields an idealised {cam['cone_angle_deg']:.1f}° clear cone. Bench-check the selected 120° lens, ribbon width, bend transitions, retention and flex connector orientation.
- Acoustics. Speaker grille path is about {audio['diaphragm_to_grille_centerline_mm']:.1f} mm. The microphone PCB centre is about {audio['mic_center_to_port_mm']:.1f} mm from its opening. Check sealing, isolation and feedback using the selected devices.
- Confirm plug overmoulds, breakout variants, electrical current margin, minimum print walls, fastener fit, load and durability on hardware. Build and dry-fit the USB-C opening and carrier samples before ordering a full print.
"""
if data['rigid_contacts'] or route_contacts or data['wire_pair_contacts']:
    report += '\n## Remaining contacts in this run\n\n'
    for item in data['rigid_contacts']:
        report += f"- {item['component']} {item['piece']} touches {status(item['touches'])}.\n"
    for route in route_contacts:
        report += f"- {route['label']} touches {status(route['covers_hit']+route['supports_hit']+route['other_parts_hit'])}.\n"
    for pair in data['wire_pair_contacts']:
        extent = f" by {pair['overlap_mm']:g} mm" if pair['overlap_mm'] is not None else ''
        report += f"- {' and '.join(pair['routes'])} overlap{extent} in the model.\n"
report += '\n## Model dimensions\n\n'
for component in data['components']:
    link = f" [Reference]({component['source']})" if component['source'] else ''
    report += f"- **{component['label']}**. {component['basis']}{link}\n"
report += '\nOpen `connected-fit.json` for the exact contact names, waypoints and sampled poses. See `wiring-routes.csv` for the route and pin labels.\n'
(OUT / 'FIT-REPORT.md').write_text(report)
print('Connected fit report and wiring schedule written')
