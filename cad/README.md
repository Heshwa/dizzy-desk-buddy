# Dizzy enclosure prototype

Open **output/Dizzy.FCStd** in FreeCAD. On this Mac, **Open Dizzy CAD.command** also loads the coloured assembly. The Printable group contains editable solid bodies. The Hardware group contains green component allowances. The Calibration group contains the small fit samples. The **Review.FCMacro** applies the assembly colours and shows the closed enclosure. For an interactive review, double-click **Start CAD Preview.command**, then turn on **Show internals** or **Explode assembly**. The motion sliders use the joint axes from Webots.

The original desk scene is preserved. Open **simulation/worlds/dizzy-cad.wbt** to see the exported CAD move through six joint poses. This scene exercises visual geometry and the joint coordinates. The validation report records mesh interference separately.

## Files and dimensions

| File or folder | Purpose |
|---|---|
| output/Dizzy.FCStd | FreeCAD assembly containing the solid parts and unscaled component allowances |
| output/Dizzy-assembly.step | Solid exchange assembly in millimetres |
| output/step | Individual exchange solids |
| output/stl | Individual enclosure and mount meshes |
| output/calibration | Fit samples, with 0.2, 0.3 and 0.4 mm clearances |
| components.json | Part dimensions, placement, measurement status and planned removal direction |
| reports | Geometry, fit and articulation evidence |
| parameters.json and source/build.py | Regenerating and revising the design |

The case uses the seated Webots proportions enlarged 7.5% to about 218 mm tall. This is the first tested scale that passed the envelope sizing check. The GC9A01 active diameter stays nominally 32.4 mm. The display carrier reserves the full board allowance rotated around the face normal. The aperture is 2.5 mm below the visual reference to allow more space for the camera. The lens stays above it. Component boxes use the planned assemblies, including allowance for space around the bare board. See the fit report for conflicts and the measurement sheet before ordering parts or printing an entire set.

## Assembly and service

1. Measure the actual boards, servo horns, outlet plugs and lens assembly. Complete **source/calibration_measurements.csv**. Print the display seat and the screw and nut samples first. Check the board rail, buttons and bearing seats with the same printer settings planned for the enclosure.
2. Assemble the shoulders and neck on the open torso. Use the actual servo horns and verify the screw pattern against the adjustable adapters. Add the supported shafts and retaining hardware. Dry fit the covers and move the joints by hand before attaching power.
3. Load each hip board on its own carrier. Keep the USB-C plug accessible, preserve the programming and antenna clearance, route the power and signal harness separately, and keep the RTC cell reachable. The front cavities allocate the mic and speaker separately. The speaker faces the front grille.
4. Put the LCD and small camera carrier into the open helmet. Check the lens view with the shutter open. Route the flex without folding it. Put each insulated electrode beneath its own crown inlay and verify the volume cap travel. Check the head service loop through the full yaw range.
5. Fit the chest switch, front and rear shells, access cover and accent pieces. Run the arm and head sweep slowly before fitting the exterior shoulder covers. Do the assembly, fastener and stability checks with the actual parts.

The fastener baseline is M3 machine screws and captive hex nuts for repeated access, plus the purchased servo fixing hardware and insulated PCB pads. Use the screw sample to match the actual fasteners. Shell-to-carrier attachment details and final receiver positions depend on the measured hardware. The printed retainer geometries are fit prototypes. Select screw lengths after checking stack thickness, head access and clearance to the electronics. The bearing interfaces use provisional 15 × 24 × 5 mm at the neck and 4 × 13 × 5 mm at the shoulders. The exact insert, retaining fit and horn coupling depend on the purchased samples.

## Printing and validation

Use PETG for the main shells and mounts. TPU is optional for contact pads. Start with a 0.4 mm nozzle and 0.2 mm layers. Set smooth visible faces away from support contact. Use removable brims for narrow walls. Place tray and nut samples face up. Orient shoulder brackets and horn adapters so the load is carried along the layers, then inspect the sliced cross-section for weak thin walls. Build-volume checks use the STL bounding boxes. Print orientation and supports still depend on the printer.

The [validation report](reports/VALIDATION.md) lists the outline measurements and all remaining fit checks. The [removal-path data](reports/validation.json) records the covers to remove and any offset needed for each component envelope. The stand-alone coupons are the first prints. Bench checks still include fastener retention, repeatable assembly, horn fit, servo load, tipping, cable flex life, board clearance, speaker sealing, heat and touch sensitivity. The current electronics wiring plan remains in the project’s hardware folder.

## Rebuild

From the project root, run **cad/Rebuild.command** on the installed Mac or run **cad/Build.FCMacro** inside FreeCAD. The assembly is built from the shared design constants, **cad/components.json** and the CAD geometry source. Change the component manifest once actual measurements are available, then rebuild. **FreeCAD is available under Applications.**

Run the review scripts with the optional Python packages listed in **source/review-requirements.txt**. The preview generator and renderer write the browser buffers and static views, the inspection script writes the mesh, motion and silhouette results, and the world generator assembles the CAD meshes into the validation scene.

```sh
cad/.venv/bin/python cad/source/preview.py
cad/.venv/bin/python cad/source/render_review.py
cad/.venv/bin/python cad/source/validate.py
cad/.venv/bin/python cad/source/make_world.py
```

## Parts catalogue and assembly animation

Open the CAD preview and choose **All parts**. Each shell, mount, hardware allowance and fit sample has its own image and rotatable model. Choose **Assembly GIF** for the six-stage part sequence. The crown now uses two smooth curved pads seated on a curved perimeter ledge. To remove each sensor allowance, lower it 1.5 mm below the support ledge, shift it 7 mm toward the centre, then lift it through the opening. Check retention and touch response with a physical sample.

`cad/.venv/bin/python cad/source/assembly_media.py` rebuilds the part images and GIF after regenerating the review meshes.

## Connected fit study

Choose **Connected fit** to see the revised USB-C pocket, installed hardware, plug gauges and 25 cable routes. The revision adds connector relief to the affected mounts and retainers and moves the cable paths through the neck and shoulder passages. The plug gauges, all 25 cable routes and 950 combined head and arm samples pass the connected CAD checks. Open the [fit report](fit-study/FIT-REPORT.md) and **fit-study/Dizzy-connected-fit.FCStd** for the installed layout. Remove the rear hip cover to reach the ESP32 programming socket. Validate the actual plugs, camera ribbon slack, cable flex and acoustic fit before printing the complete enclosure.

The study includes the manufacturer model for Adafruit 5807. The other parts use documented dimensions and provisional details where the purchased items need measurement. The original shell files remain the baseline for the fit study.

Rebuild the study from the project root:

```sh
cad/.venv/bin/python cad/source/connected_fit.py
cad/.venv/bin/python cad/source/check_service_fit.py
cad/.venv/bin/python cad/source/fit_report.py
python3 cad/source/pack_fit_view.py
resources=/Applications/FreeCAD.app/Contents/Resources
PYTHONPATH="$resources/lib" "$resources/bin/python" cad/source/export_connected_fit.py
```
