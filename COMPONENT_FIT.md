# Dizzy round-display fit study

Updated 18 November 2026. The Webots model now uses the selected round display class and the complete component baseline in hardware/BOM.csv. The supplied photograph is a shape reference; the shell is adapted to this assembly.

## Display and enclosure

Selected prototype display: **Techtonics TECH2512, GC9A01 7P, 1.28-inch round IPS SPI, 240×240, non-touch**.
Purchase link: https://techtonics.in/product/1-28-inch-round-display-module-gc9a01-7p-240x240-spi/
Previously listed at ₹449. Stock and price must be rechecked before purchase. No order has been placed.

| Feature | Current simulation |
|---|---|
| Framebuffer | 240×240 pixels |
| Visible surface | Circle, nominal 32.4 mm diameter |
| Content safe area | Circle of radius 108 pixels, centred in framebuffer |
| LCD board bound | Provisional 40×46 mm; not a verified TECH2512 drawing |
| Display assembly pocket | 46 mm wide ×52 mm tall ×14 mm deep |
| Head exterior | 102 mm wide, 69 mm actual front-to-back depth, 88.5 mm actual trimmed height |
| Head form / nominal wall | Trimmed ellipsoid, no box corners / 2.5 mm |
| Black circular bezel | 69 mm outer diameter, cosmetic frame around separate active LCD |
| LCD recess | 0.2 mm behind bezel front |
| Seated hips | 120×116×60 mm; no pedestal |
| Overall height / width with arms | 203 mm / 167 mm actual moving mesh bounds |
| Arms | Two shoulder motors, 0–120°; sampled hand/head/hip/foot clearance |

The generic LCD module still needs actual board/header dimensions and thickness measured before mounting posts are finalized. The simulation uses a conservative provisional bound, explicitly separate from manufacturer measurements of other GC9A01 variants. It does not claim those variants share a PCB or mounting holes.

The face is an actual circular mesh with circular texture mapping, not a rectangle with rounded corners. The renderer places all illuminated pixels inside an inset circle. The clock uses HH:MM, with larger numerals; short voice/alarm labels stay inside the circle. Full transcripts remain in the control panel. No text is hidden by a masking operation to conceal clipping.

## Component placement

Head: circular LCD and cosmetic black face surround, camera board and upper lens/activity-light ports, two side volume switches and two electrodes under the broad crown pad. The 74mm face surround is not a larger screen.

Torso: neck servo, distribution board and chest recording switch. Both shoulder servos occupy the higher side pods. Separate sleeves, cuffs and thumbed palms rotate at each shoulder. Approximate25g simulated arm masses are assumptions for motion testing.

Seated hips: flat ESP32 and PCA9685 boards, speaker, amplifier, microphone, clock/cell, capacitors and rear USB-C input. Revised clock and PD positions clear the torso electronics in common coordinates. The visible audio ports occupy the central surface left exposed by the feet. Feet are fixed; small underside contact pads are shown. The robot frame is fixed in simulation, so physical stability is untested.

The assembly envelopes in dizzy/design.py include all major boards plus switch, capacitor and power-socket spaces. Regression checks verify that envelopes stay within the shell allowance and do not overlap. These checks cannot establish cable access, fastener access, component tolerances or manufacturability.

## Review files

- hardware/BOM.csv: complete component quantities, supporting parts and budget allowances.
- hardware/pinmap.json: board-specific GPIO allocation.
- hardware/ASSEMBLY.md: wiring, power, audio ownership and physical assembly constraints.
- reports/component-layout.png: dimensioned component allowance views.
- reports/display-states.png: round screen expressions at native resolution.
- reports/seated-companion.png, reports/seated-hands-hello.png and reports/seated-components.png: Webots previews.
- reports/TEST_REPORT.md: verification results and hardware-dependent checks.

Rebuild meshes with `.venv/bin/python scripts/build_enclosure.py`. Refresh the layout diagram with `.venv/bin/python scripts/render_component_layout.py`. Run checks with `.venv/bin/python -m pytest -q`.

This is a working behavior simulation and assembly fit study. Physical board samples, mounting posts, cable bends, servo horn/bearing design, acoustics, thermal behavior and enclosure tolerances remain prototype work before a print-ready/manufacturing release.

## Compact repacking

The unchanged58×30×12mm main-controller and64×26×14mm servo-driver allowances lie flat in the hips. The higher shoulder pods contain the same34×34×14mm servo allowances. The torso retains the neck servo, distribution board and chest switch. Head and hip clearances are checked with the reduced dimensions, while the arm sweep uses actual sculpted mesh vertices. See reports/compact-size-and-parts.json for all eighteen locations and SEATED_COMPANION_DESIGN.md for comparison with the original size. No real part is shrunk to make the simulation fit.
