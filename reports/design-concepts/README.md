# Dizzy design direction — Seated Companion selected

The user rejected the prior oval head/body design and asked for mini humanoid pet inspirations to select from. These are visual concepts, not dimensionally verified enclosure drawings. The seated direction is now implemented in Webots.

- A — Pocket Pilot: ivory/seafoam miniature humanoid, balanced helmet/chest/boots, warm and approachable.
- B — Little Explorer: cream/cobalt/orange, sturdy adventurous humanoid, broader chest and boots.
- C — Seated Companion: cream/terracotta seated humanoid pet with forward feet and relaxed proportions.
- D — Neo Buddy: charcoal/silver/blue, slimmer futuristic humanoid.

The user selected **C — Seated Companion**. The image is dizzy-humanoid-directions.png. The implementation target is recorded in SEATED_COMPANION_DESIGN.md at the project root.

Preserve circular LCD, camera, crown petting areas, USB-C power, head swivel and two simple shoulder lifting axes when engineering the chosen concept. Legs/feet are static for the first build. Cosmetic segmentation is not a promise of elbow/wrist/leg actuation. Reconcile screen size, internal boards, shoulder volumes, support geometry and centre of gravity after selection. The simulation now has two moving shoulder joints.

Implementation: the seated Webots model, two moving shoulder joints, component inspection and control placement are now complete as a simulation. See ../../SEATED_COMPANION_DESIGN.md and ../seated-checks.json.
