# Test Dizzy: Wokwi circuits and Webots pet

Use Wokwi for connected ESP32 inputs, LCD and servo signals. Use Webots + the Mac service for the full companion, voice, music, camera and two-pet messaging. The two applications are separate; a Wokwi Talk press does not start the Mac microphone.

## 1. Start Wokwi

The prepared browser tab is unsaved. Keep it open. If it opens with just a blank ESP32 sketch, it is not Dizzy. Restore the files using the View / run instructions in electronics/README.md; include face_assets.h and face_renderer.h. The local ZIP contains all circuit files. Do not upload .env.

1. Click green Play at top left; wait for compilation and READY in Serial Monitor.
2. Collapse Serial Monitor using the arrow at its right edge if it hides the buttons. Click blank canvas and press F to fit; + zooms in, − zooms out.
3. Five blue buttons, left to right: Talk, Vol −, Vol +, Crown L, Crown R. Press/release their centres. Hold about 0.1 seconds for a normal tap. Cmd-click on Mac latches a switch; click again to release. Avoid leaving a crown latched accidentally.
4. Keyboard alternatives: click blank canvas first, then T=Talk, J=Vol−, K=Vol+, P=Crown L, O=Crown R. Release each key between taps. Serial commands must be typed in the Serial Monitor input, not on the canvas.
5. For a command, expand Serial Monitor, type one line in its input and press Enter. Collapse it again to inspect the display. Wait for the serial confirmation before checking the next step.

## 2. Connected button and pet checks

Turn Talk off and quiet mode off before testing pet expressions. A listening or ringing state takes priority over petting.

| Test | Do this | Expected result |
|---|---|---|
| Idle/clock | Leave controls alone | Steady curved idle eyes and clock inside circle; no automatic blink loop. After 30 seconds without activity, sleepy horizontal eyes. |
| Talk | Press Talk once, then again | Tall listening eyes + LISTEN; next press returns to normal. Serial PTT_START/PTT_STOP. This does not record audio in Wokwi. |
| Volume | Press Vol+ once, Vol− once | Volume changes by 5 then returns; limits 0–100. Inspect bottom status/Serial Monitor. No audio is synthesized. |
| Single pet | Briefly press/release either crown, then wait at least 0.35 seconds | Happy eyes with smile for about 2 seconds; both hands lift toward 40° and return after 1.2 seconds. PET_TAP. No remote greeting. |
| Stroke | Briefly press/release Crown L, then Crown R within 0.8 seconds | Happy face for 3 seconds and both hands lift toward 40°; PET_STROKE. No sound in Wokwi. |
| Double tap | Two short presses/releases of the SAME crown less than 0.35 seconds apart | One local right-hand wave. DOUBLE_TAP. Remote delivery and receiver heart reaction require Webots. |
| Hold | Hold one crown at least 1.2 seconds and release | GOOD NIGHT face; hands gently lift toward 20° then return after 1 second. No remote delivery in Wokwi. |
| Quiet | Enter quiet, then repeat single pet | QUIET=1; expression still reacts, automatic hand gestures suppressed. Enter quiet again for QUIET=0. Quiet does not itself force sleepy eyes. |

The digital switches approximate touch gestures; they do not measure real capacitive touch sensitivity. Motors move smoothly, so very short gestures may turn around before reaching the nominal angle.

## 3. Every face, in isolation

First dismiss alarms and switch Talk off. Enter each command separately, observe it, then proceed. Each is an eight-second visual preview. Only face blink deliberately closes the eyes; there is no automatic blink loop.

| Command | Expected face |
|---|---|
| face idle | Curved eyes + clock |
| face happy | Curved eyes + smiling mouth + clock |
| face sleepy | Horizontal closed eyes + clock |
| face listening | Tall eyes + LISTEN |
| face thinking | Rounded open eyes + THINKING |
| face speaking | Rounded eyes + changing mouth + TALKING |
| face alarm | Tall eyes + WAKE UP |
| face heart | Two heart eyes + clock |
| face goodnight | Closed eyes + GOOD NIGHT |
| face music | Bobbing eyes + music bars + clock |
| face blink | Closed eyes + clock |

These previews do not start conversation, an alarm, music or a partner message. Artwork silhouettes come from the Webots renderer; the MCU uses one-bit artwork and RGB565 colour, so antialiasing and colour are not pixel-identical to the Python image. Wokwi software SPI timing is not a hardware animation-performance benchmark. The green rectangular adapter around the circular active screen is Wokwi artwork.

The labelled SPEAKER connects to amplifier SPK+/SPK−, MICROPHONE is the INMP441 I²S wiring block, and CAMERA is the ESP32-CAM power block beside its green activity LED. None captures or plays media in this sketch. Talk does not connect to the Mac service.

## 4. Motors, alarm, clock and camera indicator

| Command/action | Expected result |
|---|---|
| left | Neck reaches −45° relative to centre. |
| right | Neck reaches +45°. |
| center | Neck returns to 0°. These explicit commands stay at their target. |
| wave | Right shoulder: 118°, 75°, 118°, 75°, 118°, rest, using Webots' stage times through 5.8 seconds. |
| hello | Both shoulders: 118°, 80°, 118°, rest, through 4.2 seconds. |
| alarm | Wait 5 seconds: ALARM_RINGING, WAKE UP face, arms return to rest. No buzzer/audio in this sketch. |
| Tap crown while ringing | ALARM_SNOOZED; five simulated minutes later it rings again. A long hold also snoozes during an alarm. |
| dismiss | Cancel ringing and pending demo alarm. |
| photo | Camera activity LED lights about 1 second; CAMERA_LED_TEST. No image file in Wokwi. |
| Watch clock across a minute | Minute advances from the simulated RTC. This is not proof of battery backup or saved alarm persistence. |

For the power interlock, click the HUSB238 model and change Modelled source current from 5 A to 3 A. Expect POWER_BLOCKED and OE=1; motion must stop. Restore 5 A: POWER_OK, OE=0; motion resumes toward its target. This changes reported registers only, not actual USB-C negotiation or analog current. Never use it as proof of physical power safety.

## 5. Full companion checks in Webots

Double-click Start Dizzy.command in the project folder, keep Webots running in real-time mode, then open http://127.0.0.1:8765. Select Your Dizzy. Use this checklist independently of Wokwi.

| Feature | Steps and expected result |
|---|---|
| Pet/stroke/hold | Use the panel pet controls. Single pet: happy + gentle two-hand lift + chirp. Stroke: happy for 3 seconds. Double tap within 350 ms sends a wave; hold at least 1.2 seconds sends good night when partner is online. |
| Hands | Try Wave hand, Both hands hello, Lift hands, Rest hands. Watch both shoulders and return to rest. |
| Head | Look left/right then centre. Head stays within ±45°. |
| Tracking | Enable tracking and move the camera target; head follows within limits. Disable tracking and verify target movement no longer drives the head. |
| Typed tools | In Ask Dizzy send What time is it?, Look left, Pause music, Take a photo, Send a wave. Check the action actually succeeded before accepting the spoken confirmation. |
| Clarification | Send Set an alarm for seven. It should ask AM/PM rather than silently schedule. Answer with an explicit time and verify the alarm row in Asia/Kolkata. |
| Real voice | Enable Speak replies. Record → say Look left → Stop recording. Stop should release the microphone and show processing, then transcript/reply. Head moves and the Mac speaks confirmation. Browser/macOS microphone permission and a working provider key/quota are needed. |
| Music | Connect the simulated phone; play local sample, pause, resume, skip and adjust volume. Disconnect and confirm play reports failure. This is not phone Bluetooth pairing. |
| Ducking | With music playing, request a spoken reply; music dips and returns. Repeat with an alarm and dismiss/snooze it; volume returns to its saved setting. |
| Timer/alarm | Start a short timer; verify alarm face/audio. Tap to snooze 5 minutes; dismiss. Create an alarm a few minutes ahead, restart the application before it is due and verify it remains listed and rings. Clean up test alarms afterwards. |
| Voice service outage | Advanced: schedule a short alarm, then stop only the voice-service process, leaving Webots/controller running. Alarm must still ring. Stopping the whole launcher is not this test. Restart the voice service afterwards. |
| Camera | Take a photo and check the new image under runtime. It is a simulated camera image. |
| Quiet mode | Turn quiet on: sound and automatic gestures follow quiet policy; explicit manual actions remain testable. Restore quiet off. |
| Paired pets | Keep both online. Send one wave: partner shows heart eyes and sender delivery changes to delivered. Send good night: receiver shows good night. |
| Recovery | Disconnect a partner/broker, try a greeting and inspect offline/unconfirmed status. Wait over 10 seconds, reconnect: old greeting must not replay. A fresh greeting should deliver once. Restart and verify saved volume/quiet/alarm settings. |
| Provider failure | If the model returns quota/network/tool errors, confirm the panel reports failure and does not claim the action succeeded. Do not deliberately exhaust the free quota. |

## 6. Checks awaiting hardware

Actual Bluetooth phone pairing, audio quality/I²S timing, touch through the enclosure, servo loads, physical camera quality, USB-C PD contract/temperature/current, regulator stability, battery backup and cable voltage drop cannot be passed by these visual tests. The ngspice power model is available separately in electronics/power; it uses assumed loads and does not qualify the assembled circuit.

## 7. Reproducible developer checks

From the project root:

```
python3 electronics/tests/run_checks.py
.venv/bin/python electronics/tests/check_face_rendering.py
./electronics/compile.sh
```

These check register models, wiring, actual sketch behavior, face silhouettes, safe display bounds and firmware compilation. They do not replace manual audio/camera/LLM or hardware tests.
