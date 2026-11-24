# Dizzy handover for the next agent

This repository contains the current V1 project plus the implemented V2 prototype. Preserve the V1 assets while continuing V2. Treat this as a prototype: CAD dimensions and the under-₹10,000 budget are planning estimates until real parts are measured, a print is quoted, and hardware is tested.

## Start here

1. Read [`v2/README.md`](v2/README.md) for the demo and build entry points.
2. Read [`v2/reports/TEST-REPORT.md`](v2/reports/TEST-REPORT.md) before claiming capabilities. It separates software/simulation passes from work still requiring hardware.
3. Review [`v2/hardware/ASSEMBLY.md`](v2/hardware/ASSEMBLY.md), [`v2/hardware/BOM.csv`](v2/hardware/BOM.csv), and [`v2/hardware/wiring.csv`](v2/hardware/wiring.csv) before changing firmware or the design.
4. Review [`v2/cad/README.md`](v2/cad/README.md) and [`v2/cad/output/fit-report.json`](v2/cad/output/fit-report.json) before modifying the enclosure.

## Current verified state

- V1 tests: 131 passed in the recorded regression run.
- V2 local panel, 24 face reactions, tools/games, MQTT partner events, simulated music, and alarm/persistence paths have automated checks.
- A generated audio fixture was recorded through the browser's start/stop controls, transcribed by Whisper, routed to an action, and answered by Piper. The live Google Gemini text path and tool calls were also exercised. **A real user microphone recording has not been verified.**
- Webots motion and CAD-derived scenes passed the recorded gait, dance, and joint-limit checks.
- Both ESP-IDF firmware targets build. Images in `v2/firmware/images/` have not been flashed to physical devices.
- FreeCAD exports and sampled mesh checks are available in `v2/cad/output/`; component interference is checked using simplified boxes. This does not verify cable routing, real connector clearance, fastening, or strength.
- Wokwi fixture/chip compilation passed; the full Wokwi run did not start because no CLI token is configured.

## Highest-priority remaining work

1. Run the actual Wokwi simulation with a locally configured CLI token, then update the test report with evidence.
2. On the selected physical parts, verify AMOLED timing/safe area, microphone and speaker, Android/iPhone Bluetooth playback, servo currents, battery protection, motor shutoff, and thermal behavior. Do not present simulation as physical validation.
3. Measure purchased components and connectors; revise adjustable carriers, harnesses, service paths, and mass estimates in FreeCAD. Slice the complete print and confirm delivered cost stays below ₹10,000.
4. Only after the open-frame rig passes current, voltage, fall, and stop checks, test unassisted walking. The simulated gait is tuned to its model; real walking remains disabled in the default head firmware image.
5. Update `v2/reports/TEST-REPORT.md` with every new result, including failures and test conditions.

## Reproducible entry points

Run commands from the project root unless a guide says otherwise:

- Desktop demo: `v2/Start Dizzy V2.command` (macOS), or `v2/tools/start-demo.sh`.
- Webots: `v2/Open V2 Webots.command` (macOS); scene files are under `v2/webots/worlds/`.
- Firmware: `v2/tools/firmware.sh head` and `v2/tools/firmware.sh audio`. The script may fetch ESP-IDF and dependencies on first run and needs network access plus a build directory without spaces.
- CAD: `v2/cad/build.sh` with FreeCAD installed; generated, editable and printable outputs go in `v2/cad/output/`.
- Wokwi: follow `v2/hardware/wokwi/README.md`. Keep any token only in the local environment; never commit it.
- Root V1 regression: use the environment and command documented in the root README; do not interpret this as a V2 physical test.

## Secrets and generated files

Never commit `.env`, API keys, Wokwi or MQTT credentials, Wi-Fi credentials, local voice models, Python environments, runtime logs, or downloaded toolchain trees. `.env.example` is safe to copy as a template. Keep hardware provisioning credentials out of firmware source, reports, screenshots, and commits.
