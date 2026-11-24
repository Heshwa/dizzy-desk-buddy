# Dizzy — Seated Companion implementation

Selected direction: C in reports/design-concepts/dizzy-humanoid-directions.png. Implemented in Webots on 18 November 2026.

The model follows the sample with a broad ivory helmet, terracotta circular face rim, shaped ivory chest, warm waist band, seated hips, forward feet with beige sole inserts, shoulder covers, sleeve cuffs and thumbed mitten hands. Feet stay fixed. There is no exposed pedestal, elbow, wrist or walking mechanism.

## Controls

- A large curved crown pad covers two independent copper petting electrodes. The centre seam separates the two simulated touch zones. Tap for petting, stroke across zones, double tap to greet the paired pet, or hold for good night. A tap snoozes a ringing alarm.
- One short horizontal chest capsule is the recording button. Press once to start and again to stop. Its small microphone mark distinguishes it from the petting pad.
- Left and right helmet ear caps are volume down and up. Physical switch wiring must pass through the neck with a slack loop.
- USB-C power enters at the rear of the hips. Audio grille and microphone opening sit in the exposed central hip surface between/above the feet.
- The control panel offers Wave hand, Both hands hello, Lift hands, Rest hands, Show components and Close shell. Webots keys W/H trigger a wave/hello. Existing voice, touch, camera, music and remote controls remain available.

## Actual display versus concept illustration

The selected TECH2512 GC9A01 remains a circular 240×240 LCD with a nominal 32.4mm active diameter. The larger black face surround is a cosmetic front panel with separate camera and activity-light openings; it does not enlarge the LCD. This is the main visual difference from the illustration, which did not specify real component dimensions. All visible text stays within the physical active circle.

## Component fit

Nominal helmet generating dimensions: 102×86×92mm, trimmed at the face and neck. Actual outside depth69mm and height88.5mm. The smaller torso holds the neck servo, distribution board and recording switch. The ESP32 and PCA9685 now lie flat in the hips. Both shoulder servos occupy integral higher side pods. The 120×116×60mm hips replace the previous stand and contain the RTC/cell, speaker, amplifier, microphone, capacitors and USB-C input. The clock and PD allowances were repositioned to avoid the torso electronics. The two volume switches moved to the helmet.

All head, torso and hip allowance corners pass the nominal 2.5mm wall-envelope checks. Fixed torso and hip allowances are also checked against each other in common coordinates. Green boxes in Show components are assembly sizing envelopes, not exact models of the purchased circuit boards. The component diagram and BOM identify the parts.

Overall nominal height203mm; moving-arm width167mm; seated footprint approximately120mm wide and136mm deep, excluding hands. These describe the simulation, not a final printable enclosure.

## Hands and motion

Two real Webots shoulder motors and position sensors use a forward lifting axis, travel limited to0–120°. Hand geometry now includes an upper sleeve, coloured cuff, rounded palm and small thumb. Wave lifts the right hand and alternates its angle; hello and lift use both hands. All sequences return smoothly to rest. Petting makes a small lift; a fresh remote wave triggers one receiving sequence. Duplicate messages are acknowledged without restarting it. Quiet mode suppresses automatic reactions; explicit hand commands remain usable. Alarms return the hands to rest.

Arm animation uses simulation time, while alarms continue to use the computer clock. Each simulated moving arm has an assumed25g mass and approximate collision volume. This permits meaningful measured joint motion but does not validate a purchased SG90, printed linkage or load capacity. The stationary robot frame is fixed to the simulated desk; balance and tipping are not validated.

## Power and remaining physical work

Main power stays USB-C, using the selected5.1V/5A-capable supply and HUSB238 input. No main battery; the RTC backup cell keeps time only. Component links and quantities are in hardware/SHOPPING_LIST.md and hardware/BOM.csv.

Before manufacture, measure the generic LCD and all boards, add mounting posts and service access, design supported shoulder shafts/horns, route wires and the camera flex, verify button guides and neck clearance, and test acoustics, electrodes, power negotiation, heat, servo load and stability. The camera port is open in this simulation; a physical privacy shutter is still a mechanical design item. No purchases or new electronics firmware are claimed.

Evidence: reports/seated-companion.png, reports/seated-hands-hello.png, reports/seated-components.png, reports/seated-checks.json and reports/TEST_REPORT.md.

## Compact revision — hands and size

The original seated revision is archived in reports/seated-v1. Height falls from225 to203mm (9.8%), and the complete arm width from186 to167mm (10.2%). The desk footprint falls from128×150 to120×136mm (15% less area). No electronic part allowance was scaled down: all eighteen keep their original dimensions, with rotations/repositioning as needed. Size comparison and placements are recorded in reports/compact-size-and-parts.json.

The higher shoulder line, continuous tapered sleeves, short shaped cuffs and smoothly blended thumbs follow the selected illustration more closely. The shoulder cases sit in side housings, clear of the central neck actuator. The real32.4mm display and all current control functions remain. Cable paths, mounting tolerances and measured component samples limit further shrinking; the current margins are provisional engineering allowances.
