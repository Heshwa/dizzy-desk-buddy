# Round LCD correction — 19 November 2026

The selected hardware remains the GC9A01 1.28-inch 240×240 round LCD. The earlier Wokwi demonstration used simplified eyes and generic rectangular presentation, which did not match Webots.

## Passed

- Generated face masks directly from dizzy.face.render_face for 11 states; speaking and music each have eight frames, with periodic blink variants.
- Compiled the actual sketch into a host renderer and compared every body-mask pixel against Webots for all states and animation phases. All illuminated pixels, including clock/status labels, fit inside radius 108 of the 240×240 panel.
- All eight electronics behavior/model/wiring check groups passed.
- ESP32 firmware compiled: 435399 bytes flash, 25016 bytes static RAM.
- Updated the live Wokwi circuit with the new sketch, face headers and LCD model. Simulation started; serial accepted face heart and face speaking. Visually observed heart eyes, speaking mouth and TALKING label inside a circular aperture, plus centered clock at idle. Screenshot: wokwi-round-display.jpg.

## Limits

Wokwi still supplies a rectangular green generic custom-chip adapter around the circular screen. The 264×264 presentation includes a 12-pixel bezel; SPI addressing remains 240×240. This is not a manufacturer-board mechanical model. Serial face previews are visual only. Audio capture/playback, camera and network gestures retain the existing simulation boundaries. Browser animation frame rate was not benchmarked; host checks validate distinct frames rather than real hardware timing.

## Reproduce

From the project root:

```
.venv/bin/python electronics/generate_face_assets.py
.venv/bin/python electronics/tests/check_face_rendering.py
python3 electronics/tests/run_checks.py
./electronics/compile.sh
```

In Wokwi upload face_assets.h and face_renderer.h as well as the existing files. Start, expand Serial Monitor and enter face heart, face speaking or face music. Talk switches listening on/off. Tap either crown for the happy expression; hold for goodnight. These controls use the actual sketch.

## Reaction parity correction

A later user review exposed that matching artwork silhouettes did not establish matching reactions. Corrected the actual sketch: single tap now lifts both hands to 40° for 1.2 seconds; alternating crown zones within 0.8 seconds produces a three-second happy stroke; goodnight makes a gentle 20° hand gesture; wave follows all six Webots stages through 5.8 seconds; an alarm returns hands to rest; inactivity after 30 seconds produces sleepy eyes, while quiet itself does not force sleepy eyes. Quiet suppresses the automatic gesture poses. Alarm snooze takes priority over a crown hold.

Added deterministic checks of stroke, happy hand targets/return, quiet/idle/sleep priority, wave fourth stage and alarm interruption to the actual-sketch behavior harness. Eight groups passed; 11-state body-artwork comparison and safe-area checks passed. Adjusted RGB565 conversion to the nearest available cyan/background channels. Text antialiasing and exact continuous animation timing are still not identical to Python/Webots; the previous claim of complete visual equivalence was too broad.

In the real Wokwi UI, holding/releasing Crown L produced GOODNIGHT. A 120 ms press/release produced PET_TAP and status showed both arms beginning to lift (left=4 right=4), proving the connected input reached the updated firmware rather than a direct function call. Fast double-tap and alternating-zone manual timing were checked in the host harness, not established by this browser run. Full instructions: ../TESTING_GUIDE.md.

## User-requested still idle eyes and audio/camera clarification

Removed the automatic 4.7-second blink from both the shared Webots face renderer and Wokwi. Explicit blink remains available; speaking mouth/music movement stay tied to their states. Tests establish steady idle/listening/happy/heart images across timestamps. Added visible microphone, speaker/amplifier and camera annotations; replaced the ambiguous speaker resistor with an explicitly wiring-only speaker block connected across SPK+/SPK−. This does not implement audio or camera emulation. Reopened Webots because the Mac service had zero connected controllers.

Validation after this change: 78 design/display tests passed, all 11 Webots-to-sketch face silhouettes and safe-area checks passed, eight electronics groups passed, ESP32 build passed (435803 bytes flash / 25040 bytes static RAM). Wokwi started and its accessibility tree confirmed all new speaker/microphone/camera labels. Shared renderer changes loaded on reopening Webots.

Mac/Webots test: connected dizzy-a and dizzy-b; typed Look left returned success, local action route, spoken=True, reply Turning my head to the left. Reply was ready in 218 ms; total including playback 3652 ms. This was not a Gemini conversation or microphone transcription test. Camera button returned Done · photo_capture and displayed a new simulated image. Screenshots: camera-controls-current.jpg and wokwi-labelled-media-current.jpg.
