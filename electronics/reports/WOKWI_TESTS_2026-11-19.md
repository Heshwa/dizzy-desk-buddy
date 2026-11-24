# Direct Wokwi circuit test — 19 November 2026

These results come from the connected Wokwi project, not Webots. A clean project was loaded from the local circuit files and tested through its visible controls and serial monitor. The corrected Wokwi tab is left open and running; the older duplicate was closed to avoid using its faulty wiring. Nothing was publicly saved or published.

## Fault found and fixed

**The volume-up connection was wrong.** The original diagram used `esp:39`, but Wokwi's ESP32 DevKitC V4 exposes GPIO39 as **`VN`**. That left the input floating, produced a false volume increment at startup and prevented the connected volume-up switch from working reliably.

Changed the diagram to **`esp:VN`**. Firmware still correctly uses GPIO39. This mapping is confirmed by [Wokwi's official board definition](https://github.com/wokwi/wokwi-boards/blob/main/boards/esp32-devkit-c-v4/board.json). The corrected circuit stayed at volume 50 after startup, then produced **55 when volume-up was pressed and 50 after volume-down**.

The generator, connection list and diagram have been updated. New automated validation checks every native ESP32 terminal against the board definition, and checks every signal connection against the approved hardware GPIO map. All **8 electronics check groups pass**. Earlier volume-up claims based only on the original startup increment did not prove the switch was connected; this direct retest replaces that claim.

## Results observed in Wokwi

| Connected component / action | Result |
|---|---|
| HUSB238, PCA9685 and DS3231 I²C connections | PASS — ACK at 0x08, 0x40 and 0x68 |
| GC9A01 round display | PASS — animated eyes and advancing clock inside the circular visible area |
| Talk switch / GPIO34 | PASS — PTT_START and PTT_STOP; these are diagnostic events, not live microphone recording |
| Volume switches / GPIO35 and GPIO39 (VN) | PASS — 50 → 55 → 50 after the wiring correction |
| Neck servo | PASS — requested positions −45°, +45° and centre observed in serial state and visible servo movement |
| Both shoulder outputs | PASS — both reach 118° and return to 0° |
| Visual test alarm / crown snooze | PASS — ALARM_RINGING followed by ALARM_SNOOZED: 5 minutes |
| Crown single-tap | PASS — PET_TAP: happy blink (local) |
| Crown hold | PASS — GOODNIGHT event on held-switch release |
| Modelled 3A source result | PASS — POWER_BLOCKED, OE high, and both arms remain at zero during a gesture request |
| Restore modelled 5A source result | PASS — POWER_OK, OE low, then neck/shoulder movement resumes |
| Tightly timed double-tap in browser UI | NOT VERIFIED — automation did not reproducibly produce the required press/release spacing; actual sketch logic passes its separate deterministic double-tap test |

The alarm/hold tests were captured earlier in this same Wokwi session before the volume-only wiring correction. Their firmware and crown connections did not change. Boot, volume, talk, power inhibition/recovery, single-tap, neck limits and shoulder movement were captured again after the correction. The raw evidence labels these phases explicitly.

The servo results above are simulated positions and visible motion, not physical torque or precision measurements. The clock, LCD, servo-driver and PD blocks are custom functional models with the documented register/command subsets.

## Connected does not mean fully emulated

The **MAX98357A, INMP441 and ESP32-CAM symbols currently represent wiring only**. Wokwi does not produce amplifier audio, microphone samples or camera images from those blocks. Music, voice recognition, Gemini replies, Bluetooth phone pairing, remote MQTT gestures and real camera capture are not validated by this circuit sketch. The `photo` command only demonstrates an indicator output; the quiet toggle is diagnostic state, not a complete audio feature.

Similarly, the HUSB238 slider models the reported contract registers. It does not simulate USB-C negotiation or analog voltage drop. The previously reported voltage-margin calculations belong to the separate ngspice power model and are not Wokwi measurements.

## Controls in the open Wokwi project

- The five blue buttons below the circuit are talk, volume −, volume +, crown left and crown right.
- Click the simulation canvas before keyboard controls: **T** talk, **J** volume −, **K** volume +, **P/O** crown left/right. Keys drive the actual connected switch components.
- For a long hold, Wokwi supports Cmd-click to latch a switch on macOS, then click again to release it. [Button controls](https://docs.wokwi.com/parts/wokwi-pushbutton).
- Serial commands: `left`, `right`, `center`, `wave`, `hello`, `alarm`, `dismiss`.
- Click the HUSB238 block and change the modelled source-current slider **5 → 3 → 5** to test the output interlock.

## Evidence

- [Circuit screenshot](wokwi-tested-2026-11-19.jpg)
- [Live Wokwi serial evidence, separated by phase](wokwi-live-2026-11-19.json)
- [Machine-readable result summary](wokwi-summary-2026-11-19.json)
- [Electronics model, firmware and wiring checks](automated-checks.txt)

The local download bundle includes the corrected diagram and regression checks. Keep the unsaved Wokwi tab open; the local files remain the durable copy.
