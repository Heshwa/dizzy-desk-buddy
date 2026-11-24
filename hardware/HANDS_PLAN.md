# Lifting arms — simulated mechanism

The seated Webots robot now has two moving shoulder joints, bounded to0–120°, with position feedback for simulation checks. Each visible arm has a sleeve, cuff, palm and thumb. The real hardware remains a plan; Webots feedback does not imply an SG90 has position telemetry.

Use one positional SG90-class servo for each shoulder, a supported shoulder shaft and lightweight hollow flippers. Total actuators: one head yaw plus two arm lifts. Each arm has one rotational axis, raising forward and upward. There are no separate elbows, wrists or gripping fingers.

The matched body has nominal ellipsoid radii 45×41×49 mm, centred64.5mm above the stand datum, with the same smooth white finish as the head. Shoulder servo volumes now fit in integral side pods at x±36 mm, z94 mm. Outer shoulder joints sit at x±56 mm, z94 mm; arm reference origins at x±66 mm, z79 mm. A bearing and horn/shaft extension bridge each actuator to its outer hub. These dimensions are layout allowances; do not print a final linkage until the real servo shaft, horn and fixing holes are measured.

PCA9685 at I2C address 0x40 drives neck channel0, left channel1 and right channel2. Logic VCC and I2C pull-ups use 3.3V; servo V+ uses the independent 5V high-current branch. GPIO16 drives OE with 10k pull-up to 3.3V so pulses remain disabled at startup. Enable only after USB-C PD confirms the required 5V/5A contract. The RTC at 0x68 and PD controller at 0x08 share the bus without address conflicts.

Initial arm travel: 0 degrees hanging down to 120 degrees lifted diagonally. At the largest planned lift, the flipper remains below the head's lowest surface. Keep at least a physical clearance allowance and verify side-to-side/body clearance after printing. Smooth ramps, no sudden reversals, no forced rotation at stops, and short movement timeouts are required. Motion is suppressed in quiet mode unless specifically requested.

| Action | Planned arm movement | Face / head |
|---|---|---|
| Wave | Right arm rises to118 and alternates75/118 twice, then returns | Happy face and small turn |
| Hello | Both rise to118, dip to80, lift again, return | Blink / smile |
| Lift | Both rise to118, pause, return | Happy eyes |
| Listening | Arms remain at rest | Listening eyes |
| Pet reaction | Small40-degree lift | Blink and chirp |
| Good night | Small20-degree settling motion, then zero | Sleepy eyes and centred head |
| Alarm | Return arms to rest | Alarm face; touch still snoozes |
| Partner greeting | One wave after a fresh acknowledged event | Heart expression |

A wave uses the single lifting axis; it cannot reproduce a wrist waving sideways. One remote event must trigger only one action sequence. If power is insufficient or a joint faults, stop the sequence and report that the gesture was not completed. A positional hobby servo has no measured load/position feedback; the eventual physical safety strategy needs bench validation.

Power allocation for three servos: 0.8A transient per actuator plus 0.5A main board/radio, 0.5A camera, 0.7A audio and 0.15A LCD/other = 4.25A planned allowance. The chosen 5.1V/5A USB-C supply provides margin, but these are allocations, not measured stall currents. Confirm the negotiated current, transient voltage, wiring temperature, servo jam behavior and driver/connector ratings before energizing the physical arms.

The shoulder envelope includes mounting flanges: 34 mm along the output axis, 34 mm along the housing/flange length and 14 mm across its thin dimension. The neck envelope is 34×14×34mm at z84.5mm. The controller is moved toward the back, clear of the shoulder bays. These are conservative assembly envelopes, not detailed servo STEP models.

Simulation uses an assumed25g per arm and approximate collision boxes, with the main frame fixed. Servo load capacity, gravity balance, actual coupling and tipping require physical checks. Motion sequences use simulation time; alarms use wall-clock time.

## Compact hands revision

The low bead-shaped arms are replaced by continuous tapered forearm meshes, short chamfered cuffs and a single smooth thumb/palm surface per hand. The shoulders move upward from75 to94mm, closer to the selected reference. Higher joint positions make the existing forward lift read as a greeting beside the helmet. No extra motors or wrist/elbow joints are added.

Each side pod is40mm along X with an elliptical Y/Z section of48×30mm. The same34×34×14mm SG90 assembly allowance fits inside a nominal2.5mm wall, and clears the central neck servo. The fixed motor cases move into these pods; supported shaft extensions connect to the moving forearms. Actual horn eccentricity, bearings and mounting holes still require measurements.

All sculpted mesh vertices are checked through0–120° against the hip shell; lateral clearance covers every head yaw and the fixed feet. Palms are connected, closed meshes rather than intersecting detached thumb spheres. These are visual and motion envelopes, not hollow printable production hands.

The compact forearms have a fixed forward curve; no extra elbow joint is implied. Full greetings now reach118° (below the120° limit), placing the palms higher beside the helmet. Shoulder housings have filleted ends and a40×48×30mm outer allowance, with internal clearances checked against the unchanged servo envelopes.
