# Dizzy desk pet

Dizzy is a desk clock, Bluetooth speaker, and interactive pet with animated eyes on a display, a touch-sensitive head, a camera, and a left-to-right swivel. It can talk back and exchange gestures with a paired Dizzy across the internet. The prototype uses an ESP32 and an existing computer.

## What Dizzy does

| Feature | Planned behavior |
| --- | --- |
| Face and display | Show the clock below animated eyes. Use sleepy, happy, listening, speaking, and alarm expressions. Animate the mouth during spoken replies. |
| Petting | A single tap makes Dizzy blink and chirp. Two capacitive pads under the shell can detect a stroke and make its eyes close into happy arcs. |
| Head movement | A positional servo turns the head left and right. Start around 45° either side of center and adjust after checking cable clearance. Dizzy can turn on command, react to greetings, or follow a face when tracking is enabled. |
| Clock, alarms, and timers | Set alarms and timers by voice or with local controls. Show a countdown, chime at the scheduled time, and snooze an active alarm with a head tap. Store alarms on the device and keep time with a battery-backed clock. |
| Phone music | Pair an Android phone or iPhone over Bluetooth and play audio through Dizzy's speaker. Support play, pause, next, previous, and volume where supported by the phone. Show a music expression. |
| Camera | Take an on-demand photo and start or stop face tracking. Put the camera above the display with a sliding cover and visible activity indication. Process tracking on the computer. |
| Paired pets | Double-tap to send a greeting. The other Dizzy swivels, blinks, and shows a heart. Hold the touch pad to send a good-night moon. Confirm delivery when the other unit acknowledges it, and indicate when it is offline. |
| Voice | Press a dedicated talk button, speak a request, and hear Dizzy's reply. Support device commands and open-ended conversation. |

## Hardware and connections

The next revision follows [HARDWARE_PLAN.md](HARDWARE_PLAN.md): a budget GC9A01 round display, two crown petting electrodes and component-first enclosure design. The round display is now implemented in the simulation. See hardware/BOM.csv, hardware/pinmap.json and COMPONENT_FIT.md for the selected assembly and fit allowances.

- **In each Dizzy** use an original ESP32-WROOM-32 DevKit for the SPI LCD, touch pads, servo, battery-backed clock, and Bluetooth audio. Add a talk button, local controls, an I²S microphone, and an I²S amplifier with a speaker. Use an ESP32-CAM with OV2640 for photos and tracking frames.
- **On the existing computer** run a small service for voice processing and face tracking. The computer must be awake for these features. Local controls, saved alarms, pet reactions, and Bluetooth playback run on Dizzy.
- **Between the two Dizzys** use a hosted MQTT broker with authenticated, encrypted connections for gesture events and delivery acknowledgments. Both pets need internet for a live reaction. The computer can be asleep.

When the alarm is ringing, a head tap snoozes it. Otherwise, one tap pets Dizzy, two taps send a greeting, and a hold sends good night. Lower music volume during voice interactions and alarms.

## Voice and model tools

Both voice modes use the same set of actions. Dizzy records a push-to-talk request, the computer transcribes it, the model picks a tool when needed, and the computer validates and executes the action. Dizzy speaks the result after it receives confirmation. Ask a follow-up for ambiguous requests like “Set an alarm for seven.”

- **Local first** using whisper.cpp for speech recognition, a tool-capable Ollama model, and Piper for speech. Once installed, this voice pipeline can run over local Wi-Fi without internet.
- **Cloud option** using a commercial provider such as OpenAI through the same computer service. This mode needs internet and may incur usage charges. Keep provider credentials on the computer.

| Tool group | Actions |
| --- | --- |
| Clock and alarms | Read time. Set, list, cancel, or snooze alarms. Start, check, or cancel a timer. |
| Music | Resume, pause, skip forward or back, and adjust volume. |
| Face and head | Turn left, right, or center. Play an expression or head animation. Enable or disable quiet mode. |
| Camera | Capture a photo. Start or stop face tracking. Report camera availability. |
| Paired pets | Check if the partner is online. Send a wave or good-night gesture and check delivery. |

Open-ended conversation uses the same voice pipeline. Choosing a specific song or playlist by name can follow once basic phone playback works. It needs a music app integration or a local music library.

## Build and verification order

1. **Simulate one Dizzy in Webots.** Use the Python controller, display, servo, speaker, and touch controls. Verify the time display, idle blinks, petting reaction, head position, alarm, and snooze.
2. **Simulate two Dizzys.** Send gestures in both directions. Verify the receiving animation, delivery confirmation, and what the sender shows when the partner is offline.
3. **Prototype voice on the computer.** Use the computer's mic and speaker with a simulated device. Test “Set an alarm,” “Look left,” and “Send a wave.” Check ambiguous times and verify that a failed action gets an accurate spoken reply.
4. **Build one physical unit.** Test touch through the shell, servo clearance, independent alarm playback, and phone pairing. Connect the mic, amplifier, and speaker and test a spoken reply while music is playing.
5. **Add the camera and finish the pair.** Verify on-demand photos and face tracking, then test gestures between two physical devices on different Wi-Fi networks with the computer off.

## Selected visual direction — Seated Companion

The user selected concept C: a seated mini humanoid pet in warm ivory and terracotta, with a rounded helmet, compact torso, seated hips and two forward-facing fixed feet. This replaces the standing oval/puck design as the visual target. Preserve the circular display, camera, crown petting areas, head swivel, USB-C power and planned shoulder lifting motions. See SEATED_COMPANION_DESIGN.md. The seated geometry and moving shoulders are implemented; see reports/seated-checks.json.

## Current seated simulation and component baseline

The selected C Seated Companion is implemented in Webots, with a broad ivory helmet, terracotta face rim and waist, forward feet and cuffed mitten hands. The crown is a large two-zone petting pad, recording has its own chest button, and volume uses the side ear caps. Two measured shoulder motors implement wave, hello, lift and rest. See SEATED_COMPANION_DESIGN.md and reports/TEST_REPORT.md.

Retain the selected TECH2512 round240×240 LCD, original ESP32-WROOM-32E, ESP32-CAM/OV2640, three SG90 positional servos, PCA9685, MAX98357A,4-ohm3W speaker, INMP441 and DS3231. USB-C powers the robot; the RTC cell is the only battery. The updated sizing envelopes fit the helmet, torso and seated hips. Hardware links remain in hardware/SHOPPING_LIST.md and hardware/BOM.csv.

Webots verifies behavior and reserved space. Physical board outlines, mounting posts, cables, shoulder support, load, stability, touch sensitivity, acoustics and electrical performance require bench checks. This is not a manufacturing-ready enclosure or completed ESP32 firmware.

Compact update:203mm height,167mm hand span,120×136mm body footprint. All eighteen component allowances keep their original dimensions. The main board/driver rotate flat into the hips, and both shoulder servos move into higher side pods. See reports/compact-size-and-parts.json.
