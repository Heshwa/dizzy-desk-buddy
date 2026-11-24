# Dizzy simulation test run — 19 November 2026

Scope: simulation only, as requested. No physical components are assembled. No Mac webcam or microphone was opened. A short synthesized reply was played through the Mac speakers.

## Results

| Test group | Result |
|---|---|
| Live Webots acceptance | 10 passed, 0 failed |
| Restart / MQTT deduplication / expiration | 3 passed |
| Alarm during voice-service outage | Passed; service restarted afterward |
| Electronics C models and actual sketch logic | 7 check groups passed |
| ESP32 sketch compilation | Passed; 326,083 bytes flash / 22,640 bytes static RAM |
| Existing Python tests | 130 passed |
| Camera capture / tracking | Passed against the Webots camera |
| Typed request → Piper speech → playback | Passed; 4.47-second non-silent WAV at 22,050 Hz |

Live Webots checks exercised petting, partner delivery, head limits, moving-target tracking and stop, PNG capture, music play/skip/disconnect, voice ducking and gain recovery, alarm touch-snooze, quiet mode, ambiguous alarm clarification and model tool execution. Restart tests checked saved alarms/settings and stale/duplicate MQTT messages. The voice-service process was stopped for the outage test and restored; alarm audio remained active in the controller.

Camera tracking uses Webots object recognition for the test face target. It does not validate a real computer-vision face detector or an OV2640 sensor. The saved 160×120 image shows the simulated desk and small test target; this is not a physical camera quality assessment.

The spoken reply was: “I'm Dizzy, your pet buddy, created and developed by <creator> for <companion>.” The generated file contains nonzero audio and playback exited successfully. Human listening quality and the MAX98357A/INMP441 I²S hardware chain are not measured.

## Power-margin finding — needs attention

The source-current interlock logic passed, including rejection of insufficient reported current and missing I²C devices. However, a reported 5A contract alone does not guarantee a healthy rail.

These additional ngspice cases use the same assumed regulator, capacitor and load model. **4.75V is a planning target for this comparison, not a certified component limit.**

| Assumed condition | Loaded servo rail | Planning target |
|---|---|---|
| baseline | 4.773 V | Meets target |
| double cable resistance | 4.603 V | Below target |
| three times cable resistance | 4.439 V | Below target |
| higher servo allowance | 4.095 V | Below target |
| five volt source | 4.673 V | Below target |

Only the baseline meets the target, with approximately 23mV of headroom. The four stressed cases fall below it. Increasing the servo allowance from 2.4A to 3.6A creates an assumed total demand of 5.45A and reaches the modelled source current limit. These are findings from assumed loads, not measured servo stall current or actual charger behaviour.

**The physical power design remains unqualified.** Verify loaded voltage, wiring/connector losses, source negotiation and realistic simultaneous servo/audio demand before physical release. Neither the 5A-register check nor this model measures physical rail voltage.

## Evidence and reproduction

- `webots-checks-2026-11-19.json`, `recovery-checks-2026-11-19.json`, `service-outage-2026-11-19.json`
- `automated-checks.txt`, `compile-2026-11-19.log`, `regression-2026-11-19.txt`
- `camera-simulation-2026-11-19.png`, `spoken-reply-2026-11-19.wav`, `media-checks-2026-11-19.json`
- `../power/margins/results.json` and the corresponding ngspice circuits/logs
- `test-summary-2026-11-19.json`

From the project root:

```sh
python3 electronics/tests/run_checks.py
python3 electronics/power/run_power.py
python3 electronics/power/check_margins.py
./electronics/compile.sh
.venv/bin/python -m pytest -q
.venv/bin/python scripts/check_simulation.py
.venv/bin/python scripts/check_recovery.py
.venv/bin/python scripts/check_service_outage.py
.venv/bin/python electronics/tests/check_live_media.py
```

Run the live checks sequentially against the running Webots/Mac service. They temporarily alter demo state; the outage check briefly stops and then restarts the service. The generated lab ZIP includes the electronics tests and archived live results; full Webots test runners remain in the main project.

## Not run: physical hardware

Actual USB-PD negotiation/temperature/current delivery, servo torque/stall, LCD electrical behaviour, capacitive touch through the shell, real Bluetooth pairing, I²S timing/audio fidelity, physical camera quality and RTC backup switchover remain hardware checks. Wokwi's audio and camera blocks remain wiring-only. No physical result has been marked passed.

