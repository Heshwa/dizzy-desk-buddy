# Dizzy CAD validation

The candidate is 1.075 times the Webots exterior, with an approximate nominal height of 218.2 mm. The physical component allowances use millimetres and remain unscaled. See the source measurement sheet for unresolved interfaces.

| Check | Result |
|---|---|
| Original mesh hashes | Unchanged |
| Closed, valid, single CAD solids | 107 / 107 |
| Watertight STL with consistent face winding | 107 / 107 |
| Part bounds within 180 mm on each axis | 107 / 107 |
| Component envelope overlaps with checked solids | 0 |
| Component envelopes touching or overlapping each other | 0 |
| Sampled removal routes clear in nominal geometry | 31 / 31 |
| Sampled rigid poses with intersections | 0 |
| Left and right moving printed mass | 18.27 g and 18.34 g, using solid PETG density |

The motion check samples each joint against the fixed shell at 5° increments, then checks 1575 pairs of sampled moving poses. Separate combinations cover head/left, head/right and left/right. It omits intended bearing fits, loads and flexible cables. The removal check translates each component allowance through its identified service side, with the designated cover and its own retainer removed. It samples straight and offset paths. Individual retainers and wiring are outside this route check. Any unresolved path needs a revised placement or more realistic measured geometry.

## Exterior comparison

The silhouettes compare the CAD exports to the uniformly scaled Webots meshes in four projections, at 0.25 mm per pixel. The comparison includes outline changes from openings, seams and attachment geometry. It measures projected outlines, so hidden surface and wall thickness require separate checks.

| View | 95th percentile | Maximum | 0.75 mm maximum target |
|---|---:|---:|---|
| Front | 0.25 mm | 0.9 mm | Review |
| Side | 0.25 mm | 2.57 mm | Review |
| Rear | 0.25 mm | 0.9 mm | Review |
| Three-quarter | 0.25 mm | 0.35 mm | Pass |

## Wall samples

These rays sample the broad surfaces, including seam and opening areas when hit. The minimum is a screen for locally thin sections. It is not a complete wall map.

| Part | Minimum | 10th percentile | Rays |
|---|---:|---:|---:|
| Helmet_front | 0.02 mm | 0.13 mm | 189 |
| Helmet_rear | 0.99 mm | 2.48 mm | 220 |
| Torso_front | 0.14 mm | 1.54 mm | 220 |
| Torso_rear | 0.2 mm | 2.29 mm | 220 |
| Hip_front | 0.59 mm | 2.3 mm | 220 |
| Hip_rear | 0.48 mm | 2.3 mm | 220 |
| Forearm_L | 0.51 mm | 2.17 mm | 220 |
| Forearm_R | 0.6 mm | 2.21 mm | 220 |

## Findings that still need work

- The solid kernel could not resolve minus_switch against Helmet_front. The exported mesh check found clearance with a surface gap of 3.79 mm.

The separate Webots world ran all six commanded poses. The controller checked its pose fields at rest and at the end stops.

The 0.75 mm appearance target, board placement, fastener engagement, independent removal and motion have separate acceptance checks. Any result marked for review remains open. The prototype requires measured boards and horns before mechanical release. Wall minima around openings, real connector and cable bends, touch, acoustics, heat, servo loads, tipping and durability still need physical verification. Print the calibration samples first.
