# Dizzy V2 FreeCAD fit study

Open `output/Dizzy_V2.FCStd` to inspect printable solids and provisional component envelopes. The Parts group, individual STEP/STL files, front/rear pictures and assembly GIF correspond to this revision. Rebuild with `build.sh` or `Build.FCMacro`. The part dimensions and removal labels come from `components.json`.

1. Bring up the two electronic branches and controls on the open rig. Measure every board, the display cover glass and connector, the battery and supplied servo horns.
2. Compare the measurements to the component envelopes. Check the display seat, neck pin gauge, chosen captive nuts and trial screw bosses before ordering a full shell print.
3. Install the battery drawer, board retainers and controls in the torso. Place the pack low and leave the rear removal path and harness slack available.
4. Install the supported neck yaw and pitch joints. Fit the display cassette and voice speaker before closing the helmet. Check the camera add-on cover and crown controls while the rear half is still open.
5. Mount the shoulders and individual leg cassettes using the supplied servo horns and separate support pins. Test motion with covers off, then sweep again with the shell and actual connectors installed. Keep the motor cut-off accessible.
6. Add limb covers, soles and the seated dock. Check fastener access, cable retention, foot contact and final balance.

PETG shell defaults are a 0.4 mm nozzle and 0.2 mm layers. Lay thin shell edge faces down where stable, use supports under load-bearing overhangs, and print the gauge before press fits. Use M3 machine screws and captive nuts for access panels, M2 hardware where the board hole size permits, and the selected servo screws and factory horns. Verify each fastener length against the actual part and cable path. Foot pads may be printed in TPU or cut from rubber.

The CAD envelope uses provisional module dimensions. The Webots CAD world displays the actual exported shell shapes over the joint rig's simplified contact bodies. Final cover seams, support-pin fit, real cable sweep, dynamic balance and a priced print quote require a physical build.
