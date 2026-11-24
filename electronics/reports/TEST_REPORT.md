# Dizzy electronics simulation report

## Direct Wokwi retest — wiring correction

The direct Wokwi retest found and fixed the volume-up terminal: GPIO39 must connect to `esp:VN`, not `esp:39`. Corrected startup, volume switches and motor power interlock were retested. [Read the Wokwi-only results](WOKWI_TESTS_2026-11-19.md). This supersedes the earlier volume-up claim based on the floating-input startup event.

## Latest test run — 19 November 2026

See [the new simulation test report](SIMULATION_TESTS_2026-11-19.md): live camera/audio behaviour, restart/outage checks, electronics logic and compilation passed. The power sensitivity cases expose limited margin; four stressed cases fall below the 4.75V planning target. No physical hardware was tested.

Date: 18 November 2026. Host: the existing Mac. This report covers the electronics bring-up lab, separate from the complete Webots/Mac pet behaviour.

## Software and evidence

- ngspice 47, Arduino CLI 1.6.0, ESP32 Arduino core 3.3.5.
- Adafruit GC9A01A 1.2.0, GFX 1.13.0 and BusIO 1.17.4.
- Wokwi anonymous, unsaved browser session. The sources are stored locally; no project was publicly published and no credentials were uploaded.
- `firmware-build.log`: native ESP32 compilation result: 326,083 bytes flash and 22,640 bytes static/global RAM in the final sketch.
- `automated-checks.txt`: tests execute the actual C register/display model sources using a host API test double. The actual sketch’s action functions also run against deterministic clock/GPIO stubs. These are model/logic tests, not analog validation.
- `power-blocked-ui.txt`: actual Wokwi serial output with `POWER_BLOCKED`, `power=0 OE=1`, and unchanged motor positions.
- `project-regression.txt`: existing application tests, **130 passed**.

## Passed checks

| Check | Result / scope |
|---|---|
| Compile the actual ESP32 sketch | Passed with ESP32 core 3.3.5; see build log for final flash/RAM sizes. Not flashed to physical hardware. |
| Pin assignments | All firmware constants match `hardware/pinmap.json`. |
| Button wiring | External 10k pull-ups on GPIO34/35/39 verified in the connection graph; switch paths go to ground. |
| I²C wiring / register discovery | Actual running Wokwi sketch reports ACK at 0x08, 0x40 and 0x68. Shared bus is GPIO21/22 with 3.3V pull-ups. |
| Clock register model | BCD time reads and simulated time progression passed; unpowered model rejects requests. |
| PCA9685 register model | Approximately 50Hz PWM and 1500µs centre pulse passed. OE high, missing V+ and SLEEP all inhibit pulses. |
| HUSB238 register model | 5V/5A status, weaker 3A/1A settings and rejection of a different voltage request passed. This is a programmed register result, not USB-PD protocol simulation. |
| Motor power interlock in running firmware | With source-current slider at 3A, actual serial output reports `POWER_BLOCKED` and `power=0 OE=1`; a wave request does not change motor positions. Returning to 5A reports `POWER_OK`. |
| Pet / talk / volume inputs | Actual Wokwi serial output observed `PET_TAP`, `PTT_START`, `VOLUME=55`. These are local diagnostic behaviours. |
| Neck command | Actual Wokwi sketch reached −45° from a serial `left` command. |
| Display parser | RGB565 colour, split-byte input, circular clipping and loss-of-power write inhibition passed against the actual C model. |
| Good-supply analog scenario | ngspice calculates loaded servo rail **4.773V**, bus **4.845V** with the assumed 4.25A load and 5A current limit. |
| Weak-supply analog scenario | ngspice calculates loaded servo rail **3.155V**, bus **3.205V** with a 3A current limit. This scenario is intentionally insufficient for the design load. |
| Existing application regression | **130 tests passed**. |

## Live visual checks

Passed in the final running Wokwi build:

- Round display: cyan eyes and `13:20` (advancing to `13:26`) clock text were visible inside the circular 240×240 mask. Alarm changed eyes to red. The viewport reported approximately 98–102% simulation speed after the direct-feature drawing fix.
- `right`: serial status reached neck **+45°**. `center` returned it to **0°**.
- `hello`: both shoulders lifted together (observed **104°**, then **76°** during the gesture), then both returned to **0°**. The three native servo indicators visibly changed angle.
- `alarm`: serial reported `ALARM_RINGING`; the screen changed to the red alarm expression. A short crown press produced **`ALARM_SNOOZED: 5 minutes`**, followed by `alarm=0`.
- Actual button interactions produced volume **55 → 50**, **`PTT_START`**, **`PET_TAP`** and **`GOODNIGHT`**.
- A tightly timed double-tap is covered by the deterministic test that executes the actual sketch's touch functions; the automated browser clicks did not reproducibly generate the required press/release spacing. This is not labelled a passed physical double-tap sensitivity test.

The host sketch test also verifies the actual firmware power decision, missing-device inhibit, single/double/hold distinction, snooze deadline, ±45° neck limits, motion freeze with insufficient power and volume clamps. UI screenshots and the captured serial state are stored alongside this report.

## Failed attempts and limitations

- The first custom-chip build could not resolve a shared project header. The three register chip sources are now self-contained and compile in Wokwi; `dizzy_devices.h` remains their canonical source.
- Optimized ESP32 hardware-SPI writes did not deliver correct pixel data to the custom SPI chip (blank or white display). This path is not accepted. The lab instead uses vendor initialization and changed features sent over software SPI. The model starts with cleared display RAM. A real display requires a full startup clear.
- A full static copy of the previous frame exceeded the ESP32 static DRAM region. Two full RGB565 frame copies also exceeded available runtime heap. The final version draws changed features directly and keeps only the previous expression and text; it requires no full-frame buffers on the ESP32.
- Free Wokwi firmware builds waited approximately one to two minutes in the shared build queue. This delay is compilation, not voice latency. No paid plan was activated.
- These are partial peripheral models, not vendor-certified silicon models. Servo motion and display updates demonstrate function; no hard real-time scheduling or production performance claim is made.
- The wiring-only audio/camera symbols intentionally do not generate I²S audio, capture images or run a second ESP32 CPU. PTT here toggles a diagnostic event; it is not connected to the Mac voice service. MQTT/LLM/Bluetooth remain in the existing software demo and future firmware work.
- The demo alarm uses simulated uptime and is visual only. Full persistent alarms, audio ducking, quiet mode and messaging continue in Webots/Mac. The circuit sketch does not replace those services yet.

## Power-model assumptions

The source has a 5.1V target, 20mΩ effective regulation droop and an ideal 5A or 3A current limit. Cable/connector path is 40mΩ plus 1µH; servo branch is 30mΩ. Capacitors are 2×470µF servo, 470µF amplifier, 100µF controller and 100nF local, with explicit ESR assumptions. Baseline allowance is 1.15A (MCU, camera, display/other); three-servo step is 2.4A; audio step is 0.7A. These are design allowances, not measured current consumption or a transistor-level motor model.

The model's load decreases below 4.5V to keep the weak-supply calculation physically bounded; real electronics may reset or oscillate instead. A 5A-capable source reporting a contract does not prove rail quality. Bench testing must verify actual voltage, negotiation, heating and worst-case servo stall current. `peak_lead_A` can briefly exceed the source current limit because the source-side capacitor supplies a transient.

## Hardware-dependent / not yet passed

- Actual 5V/5A USB-C contract with the chosen supply and HUSB238 board, current rating, thermal rise, cable resistance and loaded rail quality.
- SG90 authenticity, stall current, torque, mechanical clearances and calibrated pulse limits. The 500–2500µs demo range must not be assumed safe for the physical mechanism.
- Capacitive sensing through the enclosure; the two simulated crown switches are digital stand-ins.
- Actual LCD voltage/pin order, full initialization, startup clearing and achievable frame rate.
- I²S microphone clocks, speaker/amplifier power and distortion, real Bluetooth A2DP pairing and simultaneous Wi-Fi/audio behaviour.
- Real ESP32-CAM image quality, local streaming, camera indicator semantics and physical shutter.
- RTC battery switchover/drift and a verified noncharging CR2032 circuit.
- Programmer VBUS isolation, switch/wire ratings, grounding/noise, enclosure ventilation and electrical safety review before assembly.

No electrical or hardware item above is labelled passed solely because the functional simulation runs.
