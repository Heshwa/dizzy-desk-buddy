# Dizzy V2 Wokwi circuit harness

The circuit boots an ESP32-S3 test sketch on the DevKitC surrogate. The custom WASM chips model the PCA9685 PWM signals, DS3231 register access and the relevant registers for body buttons, ADC voltage and torso orientation. The three chip JSON files declare pins. The head AMOLED and audio run in other test environments.

**Scope.** `sketch.ino` is a separate Arduino re-implementation of the safety and button logic running on a DevKitC stand-in. It does not run the real head firmware in `v2/firmware/head`. A passing Wokwi run checks the harness and the circuit model, not the ESP-IDF firmware's motor safety. Changes to `v2/firmware/head/main/main.cpp` are not exercised here.

**Build first.** The `.wasm` chips are committed. The firmware binary is not: `build/` is git-ignored, so a fresh checkout has no `build/dizzy-v2-wokwi.bin` or `.elf`. Create them with `v2/tools/build-wokwi.sh`, which needs `arduino-cli` with the ESP32 core and `wokwi-cli`. Then open this folder in Wokwi for VS Code, or use the CLI with your local Wokwi token.

```sh
wokwi-cli v2/hardware/wokwi --timeout 35000 --expect-text "DIZZY V2 HARNESS"
```

| Control | Expected result |
|---|---|
| 1 Talk twice | Serial shows recording, then stop. Holding the test state for 30 seconds times out. |
| 2 and 3 Crown | Each produces a separate pet event. |
| 4 Arm | PWM enables and eight servos move. Press again to disarm. |
| 5 Stop | The fixture disables servo PWM and reports motor lockout. |
| 6 Low battery | The fixture reports low voltage and disarms. Release the switch and rearm locally. |
| 7 Tilt | The fixture reports an invalid upright orientation and disarms. Release and rearm. |

The logic analyzer probes OE, yaw PWM, hip PWM and SDA. ADC voltage and tilt are injected fixtures. The 5 V circuit joins in this harness are idealized for Wokwi. Use the hardware wiring table for the actual isolated motor and logic supplies.

The ESP32-S3 sketch and all three WASM chips built successfully. The Wokwi CLI runtime requires a local `WOKWI_CLI_TOKEN`.
