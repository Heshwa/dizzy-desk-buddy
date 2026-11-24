# Dizzy simulation test report

## Current voice latency and identity update —18 November2026

The pet/system identity is now Dizzy, created and developed by <creator> for <companion>. Explicit local head/hand/music commands avoid the cloud, while general requests use a persistent Gemini client with a bounded3.5 Flash-Lite fallback and primary cooldown. Piper stays loaded, and recognized text/reply previews appear before playback ends.

130 automated tests pass. Live identity, head movement and cloud-conversation checks all produced spoken output. Head-command preparation was194ms plus80ms speech synthesis; re-transcription measured725ms separately. The cloud run encountered a real503 on3.1, successfully switched to3.5, and prepared audio in9.44s. Google overload can still slow general conversation; local commands remain independent. Full evidence and the retained first-run deadline failure are in VOICE_LATENCY.md and voice-speed-live-checks.json. Older sections below describe the previous retry design.

## Voice output repair — 18 November 2026

The user's recordings reached local transcription successfully. The initial failures were Gemini503/504 responses, while quiet mode also muted successful replies. Sound was enabled on dizzy-a. Gemini now makes a bounded retry for temporary5xx responses, with a readable busy/timeout message. Spoken requests also speak provider failures when sound is enabled; quiet/zero-volume replies report why they were silent. The panel retains the recognized transcript and displays the waiting stage. afplay failures now produce a playback error rather than a success claim.

Validation:116 automated tests passed, including provider-failure speech, preserved recorded transcripts, quiet/zero-volume notices and speaker-error reporting. A fresh user microphone request completed through local transcription, Gemini, Piper and afplay with ok=true and spoken=true. No additional recording was required for this verification. The result is saved in voice-repair-checks.json. A separate local synthesized speaker diagnostic also completed successfully. Gemini capacity remains external; temporary failures now provide accurate audible and visible feedback.

Retry handling follows [Google's troubleshooting guidance](https://aistudio.google.com/docs/troubleshooting#retry-strategy). No model, account tier, API credential or paid service was changed.

## Current compact hands revision — 18 November 2026

The selected seated concept is now smaller, with higher shoulder joints, curved tapered forearms, short cuffs and continuous blended thumb/palm meshes. Greeting poses reach118° and return to rest. The component list is unchanged; all eighteen sizing allowances retain their original dimensions.

| Dimension | Previous | Compact |
|---|---:|---:|
| Height |225mm|203mm|
| Complete moving-hand width |186mm|167mm|
| Body/feet projected footprint |128×150mm|120×136mm|

This is9.8% shorter,10.2% narrower and15% less body/feet footprint area. Cable access and measured components still need a physical fitting pass.

| Latest check | Result |
|---|---|
| Automated behavior, display and geometry suite | PASS:112 tests |
| Original component allowance dimensions retained | PASS:18/18; orientations/positions changed |
| Smaller head/torso/hips and shoulder-pod wall allowances | PASS: all reserved corners fit |
| Electronic allowances do not overlap in common coordinates | PASS |
| Actual sculpted hand sweep0–120° | PASS: hips, head-yaw envelope, torso and feet clear |
| Continuous palms | PASS: each is one connected, closed mesh |
| Live loaded arm-root coordinates match compact prototype | PASS |
| Measured wave | PASS:117.96° peak, returned to rest |
| Measured hello | PASS:117.98° each, returned to rest |
| Measured lift | PASS:118° each, returned to rest |
| Quiet petting and receiving partner hand motion/acknowledgement | PASS |
| Head travel, all five resting controls, camera recognition/photo and display capture | PASS |
| Inside view opens and exterior actually returns opaque | PASS: actual transparency field verified at0.86 and0.0 |
| Live scenario total | PASS:10 checks |
| Visual inspection and genuine Webots animation | PASS: raised hands, attached shoulders, opaque exterior and clean view |
| Gemini and user-spoken microphone input | NOT RERUN: unchanged interfaces; prior revision evidence retained below |
| Actual PCB measurements, joined/hollow enclosure walls, mounts, bearings, horns and cable routes | HARDWARE-DEPENDENT |
| Servo load, current/PD negotiation, heat, touch sensitivity, audio, physical stability | HARDWARE-DEPENDENT |

The first visual inspection failed: saved Webots joint translations from the larger robot overrode the new hand roots. The stale overrides were removed, and both file-level and live-coordinate checks now catch that condition. A second visual finding was that Close shell did not restore opacity: the Webots wrapper rejected integer0 for a float field. It now receives0.0, and the test checks the actual field rather than trusting the action acknowledgement. These failures and fixes are retained in compact-fixed-issues.json; the old saved world is archived in seated-v1.

Latest evidence: compact-size-and-parts.json, seated-checks.json, seated-final-visual-checks.json, compact-fixed-issues.json, compact-before-after.png, compact-hand-demo.gif, compact-hands-hello.png, seated-components.png and component-layout.png. The cropped animation is a presentation crop of the original Webots frames; the complete two-pet animation remains in seated-hand-demo.gif.

Reproduce with `python -m pytest -q`, `python scripts/check_seated.py --skip-llm` and `python scripts/capture_hand_demo.py` using the project environment. The --skip-llm option avoids repeating provider calls for a geometry-only revision. The full model/voice tool option remains available.

This is a working simulation and component-envelope study. Servo housings are integrated side pods; physical shells must be merged/hollowed with the required service openings, and actual shafts and wiring must be fitted before printing. The simulation fixes the main frame to the desk and assumes25g arms, so it does not validate real balance or SG90 load capacity. No electronics were purchased or scaled down for the smaller model.

## Archived larger revision

The following sections describe earlier dimensions and are retained as history.

## Current seated companion — 18 November 2026

The selected concept C is implemented as a seated Webots pet with an ivory helmet and chest, terracotta face rim/waist/cuffs, beige sole inserts and two moving mitten arms. The large crown pad has two petting zones. Recording uses one chest capsule; volume uses the helmet ear caps. The rear hip port is USB-C. The selected32.4mm active round LCD is preserved inside the larger cosmetic face surround.

| Current check | Result |
|---|---|
| Automated suite | PASS:110 tests |
| Circular screen, expression/clock content and PCB/wall allowances | PASS |
| Fixed torso/hip components checked in common coordinates | PASS: no allowance overlaps |
| Full0–120° mitten sweep against head, torso, hips and feet | PASS: conservative geometry samples |
| Measured right-hand wave | PASS: peak105.85°, returned within0.5° of rest |
| Measured both-hand hello | PASS: peaks98.56° each, returned to rest |
| Measured both-hand lift | PASS: peaks100° each, returned to rest |
| Quiet petting | PASS: happy expression retained; automatic hand movement suppressed |
| Paired MQTT wave | PASS: acknowledgement delivered and receiving right shoulder moved |
| Duplicate/stale greetings | PASS: core persistence/deduplication tests; no restarted gesture sequence |
| Head swivel and resting touch volumes | PASS:−45°, +45°, centre; all five sensors clear |
| Final face surround/camera opening | PASS: recognized target, photo captured and all resting sensors clear |
| Component inspection | PASS: translucent shell opens/closes around component allowances |
| Typed Gemini hand action | PASS: arms_pose executed successfully, then model replied “Wave!” |
| Real moving-preview evidence | PASS:34 Webots frames saved as seated-hand-demo.gif |
| Control panel | PASS: hello button executed;26 rendered buttons with no overlapping rectangles or horizontal overflow at tested viewport |
| Real microphone recording | RETAINED: existing pipeline and regression checks; no new user-spoken acceptance test in this design revision |
| Actual phone Bluetooth, ESP32 firmware and electrical operation | HARDWARE-DEPENDENT |
| Purchased-board measurements, mounts, wiring, shutter, acoustic paths and enclosure fabrication | HARDWARE-DEPENDENT |
| Servo load/current, USB-C5V/5A negotiation, heat, electrode sensitivity and tipping stability | HARDWARE-DEPENDENT |

Evidence: seated-checks.json, seated-final-visual-checks.json, seated-gemini-tool-trace.json, seated-companion.png, seated-hands-hello.png, seated-components.png, seated-hand-demo.gif and component-layout.png. Repeat with scripts/check_seated.py and scripts/capture_hand_demo.py. The latest cosmetic frame revision was checked separately for camera recognition, capture and controls; all110 automated tests passed after the final dimensions were applied.

The initial arm run failed to reach its requested peaks: the purely kinematic shoulder setup lagged the timed sequence. The adapter now uses simulation time for arm motion and approximate25g dynamic arm bodies, while alarms retain the computer clock. Measured shoulder tests subsequently passed. A first head check also failed because a fixed1.7s delay was too short; polling actual measured position passed. The intermediate report is retained as seated-before-head-wait-fix.json. These are simulation assumptions, not measured SG90 performance. The main frame remains fixed, so the scene does not validate physical balance.

The boxes seen through the shell represent assembly sizing allowances. This is a working behavior simulation and spatial fit study, not print-ready CAD or a validated circuit. Hardware links remain in hardware/SHOPPING_LIST.md and hardware/BOM.csv. No hardware purchase was made.

## Previous revision evidence

The following sections describe earlier model revisions and are retained as history. Current geometry and arm status are defined above.

## Current matched oval design — 18 November 2026

The current simulation has a truly ellipsoidal head, a matching wider oval body, circular 240×240 LCD, flush marked crown electrodes, fixed arm placeholders and a rear USB-C power port. The component baseline and supplier links are finalized for the prototype in hardware/SHOPPING_LIST.md and hardware/BOM.csv. Physical assembly qualification remains outstanding.

| Current check | Result |
|---|---|
| Automated suite | PASS: 102 tests |
| Circular visible pixels across expressions, alarm, voice and music states | PASS: all illuminated pixels stay inside radius108 |
| Geometry and component envelopes | PASS: inner shell clearance, no overlapping reserved volumes, base fit, arm/head clearance |
| Head geometry | PASS: ellipsoid surface mesh; no rounded-box head |
| Planned arm lift envelope 0–120° | PASS mathematically for flipper bounds; real joints/motors not implemented |
| GPIO allocation | PASS: unique signals, correct input-only pull-ups and available touch inputs |
| Three-servo power allocation | PASS arithmetic: 4.25A planned load below selected 5A profile; not an electrical test |
| Live head travel | PASS: measured −45°, +45°, centre |
| Live resting touch sensors | PASS: all five sensors zero at each angle |
| Wide-angle camera and tracking | PASS: actual simulation FOV120°, target recognized, tracked to15.29°, stopped on command |
| Live display capture | PASS: 240×240 image, every illuminated pixel inside circular safe boundary |
| Camera photo and scene previews | PASS: files exported from Webots |
| Existing behavior / Gemini acceptance | PASS: 10 scenarios; tracking fixture was retested after moving its target inside the camera FOV |
| Control-panel layout | PASS: connected round preview; 20 rendered buttons checked with no overlapping rectangles |
| USB-C PD contract, current capacity and temperature | HARDWARE-DEPENDENT: selected, not bench-verified |
| Actual PCB dimensions, posts, cables, fasteners, servo load and audio quality | HARDWARE-DEPENDENT |
| Physical moving arms and detailed linkage | PLANNED: fixed arms remain in this delivery |

The first Gemini command run timed out and returned an empty error. Provider requests now have bounded timeouts and readable failure feedback; the subsequent actual Gemini head/music/photo/gesture command scenario passed. The failure record is retained in round-first-run.json. A tracking fixture initially moved the target outside the relocated camera's FOV; its corrected targeted rerun passed, and the final wide-angle model was checked separately.

Current evidence: round-design-checks.json, round-design-detail.png, round-yaw--45.png, round-yaw-45.png, dizzy-a-display.png, display-states.png, component-layout.png and simulation.png. The repeatable check is scripts/check_round_design.py. Full behavior results are in simulation-checks.json; round-before-tracking-retest.json preserves the earlier fixture failure.

Power selection: official 27W USB-C supply with 5.1V/5A profile and Adafruit5807 HUSB238. The future physical controller must select only the 5V PDO, confirm the 5A contract and then enable PCA9685 outputs. The input board's hardware default is not assumed to provide5A. No real power-negotiation test is claimed. The clock coin cell preserves time only; a USB-unpowered unit cannot ring or move.

This is a behavior simulation and provisional assembly layout, not a manufacturing release. Earlier electrical, audio-loopback and physical validation limitations still apply.

## Earlier verification records

Verified on 18 November 2026 on this MacBook Air with 8 GB memory and macOS 27.0.1. Webots uses the official R2025a nightly build from 17 November 2026, commit e5d1122a3cd59f007ee4b37c8f651b50e7ee83d2. Python 3.13.7 runs both device controllers and the local service. Dependencies are recorded in requirements.txt.

## Passed

- **24 automated behavior and service tests** passed with pytest. They cover local petting, double taps and holds, persisted alarms and snooze, weekly recurrences across downtime, timers, music ducking and disconnect errors, head limits and smooth return, quiet mode, tracking controls, gesture expiry and deduplication across restarts, acknowledgment timeout, input validation, device disconnects, an injected API quota error, model tool restrictions, and concurrent microphone controls.
- **10 running-simulation acceptance scenarios** passed against the real Webots controllers and the actual Gemini API. Their results are in simulation-checks.json. The camera followed a recognized scene target, the measured servo reached -45 degrees, photos were captured, music controls and ducking worked, alarms rang and snoozed, and double taps reached the paired pet with acknowledgment. Gemini asked AM or PM for an ambiguous alarm and successfully called head, music, photo, and partner tools.
- **3 recovery scenarios** passed against the running simulation. A controller restart preserved an alarm and volume, the alarm subsequently activated its sound, an MQTT event stayed deduplicated after restart, and an expired MQTT event caused no new greeting. See recovery-checks.json.
- **Voice-service outage** passed. MQTT telemetry confirmed that the robot activated alarm sound while the voice service was stopped and cleared the abandoned thinking state. See service-outage.json.
- **Local speech generation and recognition** passed. Piper produced “Look left.” and whisper.cpp returned “Look left.” from that WAV file. See speech-check.json.
- **User-spoken microphone test** passed after the touch-model correction. The microphone captured “Look left.”, whisper.cpp transcribed it, Gemini called head_turn successfully, Dizzy replied “Done!”, and its voice state returned to idle. See microphone-check.json and live-voice-events.json.
- **Normal launcher** passed. scripts/launch.sh started the broker, voice service, Webots, and both controllers. Both pets connected and reported their initial awake expression. Microphone recording was inactive afterward, and the Gemini key loaded from the local .env file.
- **Visual inspection** passed. Both pets, animated faces, clock, camera target, and desk rendered. The final image is simulation.png, and a camera capture is camera.png. Webots used reduced graphics settings on the Apple GPU.

## Failed check and resolved findings

The automatic test that played a phrase through the Mac speakers and attempted to capture it through the microphone detected no speech. This speaker-to-microphone loopback check remains failed on this audio setup. The subsequent user-spoken microphone test passed the voice workflow. See voice-loopback.json.

During development, inspection caught an incorrect scene viewpoint and overlapping touch geometry that caused unwanted talk-button presses. Both were corrected. The corrected sensors read zero at rest. Recovery testing also caught a voice state that could remain thinking after a normal WebSocket disconnect. The state now resets when the service connection closes. A test was corrected to observe temporary head motion during the request, since the head can return to center before the final model reply arrives.

## Hardware and external checks still required

- Real Android/iPhone Bluetooth pairing and AVRCP playback control. This simulation uses a phone connection switch and original local sample tracks.
- ESP32 firmware execution, GPIO allocation, circuit wiring, I²S microphone and amplifier behavior, speaker quality, clock-module backup, power-supply behavior, and servo load.
- Capacitive sensing through the final enclosure, including strokes and holds.
- Real camera optics and face detection. The simulated camera uses Webots recognition of the moving target.
- Gesture delivery between two separate computers on different internet connections and a hosted broker. The tested pair uses separate controllers and a real local Mosquitto broker.
- The supplied Ollama adapter. The verified model provider is Gemini with its configured free-tier project.

The delivered geometry is a functional simulation model. Final enclosure dimensions and physical component mounting follow the hardware checks.

## Reproduce

Start the project with scripts/launch.sh. Run .venv/bin/python -m pytest -q for the automated tests, scripts/check_simulation.py for the interactive simulation and Gemini scenarios, and scripts/check_recovery.py for controller restart and MQTT checks. scripts/check_service_outage.py temporarily stops and restarts the voice service. Run these checks when no one is recording a voice request. Simulation tests use the configured Gemini account quota and change demo state.

For live voice, open http://127.0.0.1:8765, click Record under Talk with Dizzy, say “Look left,” and click Stop recording. Keep Webots running. scripts/check_voice.py is the optional automatic speaker-to-microphone loopback check described above.

## Recording Stop fix verified on 18 November 2026

A live process sample showed PortAudio stuck in macOS CoreAudio during stream shutdown. Microphone capture now runs in a bounded child process. Stop ends that process and saves captured PCM as WAV without waiting for audio-driver teardown. Transcription and reply generation run after microphone release, and the panel shows Processing until the result is ready. Explicit start and stop requests prevent a repeated Stop or an expired session from restarting capture. Stop targets the microphone owner when the selected pet changes. Hardware-button requests are debounced.

Three real Mac microphone start/stop cycles passed. Measured stops took 0.011, 0.005, and 0.005 seconds, with audio frames preserved and the microphone released. Evidence is in recording-stop-hardware.json. Browser checks confirmed Stop after changing pets, the Processing state, and return to Record. All 26 automated tests passed, including regressions for immediate Stop acknowledgment while transcription is blocked, duplicate Stop, stale session rejection, and Stop with no active recording.

## Rounded arm-free model verified on 18 November 2026

Dizzy now uses a rounded helmet shell, an oval display surface, an original pear-shaped body mesh, and a low circular stand. The main pet uses a white shell with turquoise accents. The partner uses purple accents. Both use the arm-free option accepted in the shape request.

The measured head reached -45 degrees, +45 degrees, and center. All three touch sensors stayed inactive at rest at every tested angle. The camera recognized the scene target and captured an image with the new mounting position. All 26 automated tests passed. Evidence is in rounded-shape-check.json and simulation.png. The scene-reset helper was corrected and verified while setting up the new view.

## Component-fitted enclosure revision — 18 November 2026

This revision supersedes the earlier oval face and arm-free shape. The selected real part is the Waveshare 2.4inch SPI LCD, SKU 18366. The simulation now uses a flat 320×240 display at its published 48.96×36.72 mm landscape active size. The head reserves a 77×47×15 mm pocket for the 70.5×43.3 mm PCB and connector allowance. A separately modeled recessed bezel replaces the curved display mask. Talk and volume pads sit flush on the stand. Fixed dummy arms have 17 mm of vertical clearance below the entire rotating head. The camera has its own port above the LCD.

| Check | Result |
|---|---|
| Automated behavior and enclosure regression suite | PASS: 92 tests |
| Clock, alarm, music, and voice text across ten expressions and multiple animation times | PASS: all rendered content inside 16-pixel safe margins |
| Display aspect ratio and physical active dimensions | PASS: 4:3 physical surface matches 320×240 pixels |
| Published display PCB fits reserved pocket | PASS in model |
| Head wall clearance and planned board/servo/audio/clock envelopes | PASS: no overlaps in reserved volumes |
| Head reaches left, right and center | PASS: measured −45°, +45°, 0° in Webots |
| Touch pads stay inactive at all tested angles | PASS: all five sensors read zero at rest |
| Camera capture and target recognition after the revision | PASS: one recognized target; snapshot saved |
| Display image captured directly from Webots | PASS: full clock visible within the LCD, 320×240 pixels |
| Visual review of front and turned head | PASS: screen recessed, dummy arms clear rotation, controls lie on base |
| Physical PCB mounting, connector and cable clearance | HARDWARE-DEPENDENT: purchased-unit measurements and prototype needed |
| Final arm joints/motors | FUTURE VERSION: current arms are fixed |

Evidence: `enclosure-checks.json`, `enclosure-detail.png`, `enclosure-yaw--45.png`, `enclosure-yaw-45.png`, `dizzy-a-display.png`, `display-states.png`, and `simulation.png`. The camera test target is hidden only from the main presentation viewpoint; robot cameras continue to see it. Display sourcing and the distinction between published measurements and provisional component envelopes are documented in `COMPONENT_FIT.md`.

No display or other hardware was purchased. The model is a simulation fit study; mounting posts, actual module depth, fasteners, tolerances, cable bends and electrical performance have not been physically validated.

