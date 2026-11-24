# Dizzy electronics lab

This lab is separate from the Webots mechanical/pet simulation. It uses the selected original ESP32-WROOM-32E DevKitC V4, 1.28-inch round GC9A01, three SG90 positional servos, PCA9685, DS3231, HUSB238 USB-C input, INMP441 microphone, MAX98357A amplifier, speaker and separate ESP32-CAM.

## Software chosen

- **Wokwi:** runs the compiled ESP32 Arduino firmware with visible wiring and native buttons/servos. Custom source models implement the selected display's RGB565/window commands and subsets of the clock, PWM and PD status registers. These are project-authored functional models, not manufacturer electrical models. [Supported hardware](https://docs.wokwi.com/getting-started/supported-hardware), [custom chip API](https://docs.wokwi.com/chips-api/getting-started).
- **ngspice 47:** analog transient calculation of the supply, cable resistance, decoupling and assumed load steps. Independent of Wokwi. No vendor regulator, USB-PD protocol or motor/gearbox model is claimed. [Official documentation](https://ngspice.sourceforge.io/docs.html).
- **Arduino CLI:** reproducible ESP32 compile on this Mac; no account, paid hosting or new API credentials needed.

The display path uses vendor initialization and software SPI to draw only changed eyes, clock digits and captions. Wokwi’s ESP32 optimized hardware-SPI path did not deliver a complete pixel stream to the custom chip. The lab starts the display model with cleared RAM; real hardware needs its own full startup clear. This workaround is not an audio/graphics or servo timing performance benchmark.

The round LCD is modelled at its actual 240×240 resolution, with a circular visible area. It does not use a rectangular substitute module. The two crown buttons are explicitly digital substitutes for capacitive electrodes. The microphone, amplifier, speaker and camera are wiring-only symbols; no speech, camera capture, Wi-Fi, Bluetooth or MQTT runs inside this bring-up sketch. Those behaviours remain in the existing Webots/Mac application. This is not yet production ESP32 firmware.

## View / run

Open `index.html` through the local lab server:

```sh
python3 -m http.server 8766 --bind 127.0.0.1 --directory electronics
```

Then open http://127.0.0.1:8766. It shows the readable connection plan, measured simulation outputs, controls and test report.

The open Wokwi tab contains the working unsaved project. Keep it open. For a fresh session:

1. Open https://wokwi.com/projects/new/esp32.
2. Replace `sketch.ino` and `diagram.json` with the files in `wokwi/` using Select All then Paste in the editor. Do not type the JSON character-by-character into the autoformatting editor.
3. In the file menu beside Library Manager, choose **Upload file(s)…**. Upload the other files from `wokwi/` (all `.chip.c`, `.chip.json`, `.h` and `libraries.txt`). Do not upload `.env` or any credentials. The custom chip sources are self-contained because Wokwi's chip compiler does not resolve shared project headers.
4. Click Start. The free build queue can take a minute or longer. There is no need to sign in or publish. A new unsaved browser session is not a durable public project link; all project files are preserved locally in `dizzy-electronics.zip`.
5. With the simulator stopped, use **… → Fit** to see the whole circuit. Zoom in to inspect a module. Use the serial input at the bottom for the commands below. Stop/start reuses the compiled firmware when unchanged.

### Controls

| Control | Behaviour in this electronics demo |
|---|---|
| Talk | Toggles PTT status; actual voice pipeline remains on the Mac |
| Vol − / Vol + | Changes the volume variable by 5; no audio synthesis |
| Crown L / R | Short release pets; two releases within 350 ms trigger local wave |
| Hold crown ≥1.2 s | Good-night face and gentle 20° hand lift, then rest; no remote delivery here |
| `left`, `right`, `center` | Neck −45°, +45°, 0° relative to centre |
| `wave`, `hello` | One or both shoulder gestures, smoothed to the target |
| `alarm` | Schedules a visual test alarm five seconds later |
| Tap crown during alarm | Snoozes five minutes in simulated uptime |
| `dismiss` | Cancels demo alarm |
| `quiet` | Toggles diagnostic state only; full quiet/audio behaviour remains in Webots |
| `photo` | Camera indicator LED for one second; does not take a photo |

Click the HUSB238 model and set **Modelled source current** to 3. Within the next power poll (500 simulated ms), expect `POWER_BLOCKED`, `power=0 OE=1` and no motor pulses. Return to 5 for `POWER_OK`, `power=1 OE=0`. This checks the firmware's response to a reported contract, not a real PD negotiation.

The logic analyser is connected: D0 neck PWM, D1 left PWM, D2 right PWM, D3 OE, D4 SDA, D5 SCL, D6 talk, D7 camera LED. Native servos show positions. Test pulse range is 500–2500µs; calibrate narrower safe limits on actual SG90/linkages before use.

## Local verification

```sh
python3 electronics/tests/run_checks.py
python3 electronics/power/run_power.py
```

Arduino CLI setup on a new machine:

```sh
arduino-cli core update-index --additional-urls https://espressif.github.io/arduino-esp32/package_esp32_index.json
arduino-cli core install esp32:esp32@3.3.5 --additional-urls https://espressif.github.io/arduino-esp32/package_esp32_index.json
arduino-cli lib install 'Adafruit GC9A01A@1.2.0' 'Adafruit GFX Library@1.13.0' 'Adafruit BusIO@1.17.4'
```

Run `./electronics/compile.sh` from the project root. Build logs are under `electronics/reports/`. Regenerate the wiring with `python3 electronics/build_wiring.py`; GPIO constants are checked against `hardware/pinmap.json`.

## Physical connection notes

Use `wiring.svg` for a readable connection map and `connections.csv` for the simulated point-to-point list. The Wokwi layout is a signal connection demo, not a physical breadboard assembly guide. Its power wiring is digital/ideal; bulk capacitors, source impedance, the master switch and RTC battery are covered in the connection plan / power model, not emulated as real power-delivery circuits in Wokwi.

- USB-C → HUSB238 **V+** → master switch → separate 5V star branches. HUSB238 breakout has no invented VCC terminal. Keep 5V selection only; verify actual 5V/5A contract and board temperature/current rating on bench. [Board pinouts](https://learn.adafruit.com/adafruit-husb238-usb-type-c-power-delivery-breakout/pinouts).
- Main board 5V input; its 3.3V output powers logic, mic, LCD and RTC. PCA VCC=3.3V, V+=5V. All grounds common; motors must not draw through the ESP32 regulator.
- GPIO34/35/39 each need external 10k pull-ups. PCA OE needs a 10k pull-up so motors start disabled. I²C needs one effective pair of pull-ups to 3.3V; use external 4.7k only if the combined breakout pull-ups do not already supply the right value. Never pull this bus to 5V.
- Two 470µF capacitors at the servo supply, one 470µF at the amplifier, one 100µF at the main controller, and local 100nF decoupling. Observe electrolytic polarity.
- Speaker connects across SPK+ and SPK−, neither terminal to ground. Mic is 3.3V; I²S clocks are shared. Actual clock rates, A2DP/voice switching and amplifier gain require firmware/bench validation.
- ESP32-CAM is a separate 5V-powered Wi-Fi node, with its own camera GPIO allocation. GPIO17 is an indicator, not camera image data.
- CR2032 powers RTC backup only. Verify the RTC board has a noncharging battery path before fitting a primary cell. This product uses USB-C desk power, not a main battery.
- Do not connect two competing 5V sources while USB programming; isolate programmer VBUS or use a verified power-path circuit.

Existing selected parts and seller links remain in `hardware/SHOPPING_LIST.md` and `hardware/BOM.csv`. Do not order solely from the visual simulation; finish the explicitly listed physical checks first.

Latest complete simulation run: [19 November 2026 results](reports/SIMULATION_TESTS_2026-11-19.md). Additional power sensitivity checks: `python3 electronics/power/check_margins.py`. Four stressed cases miss the planning voltage target; physical power delivery is not qualified.

### Round screen and matching Webots expressions

The selected LCD remains the 1.28-inch GC9A01, 240×240 round panel. The custom model now shows a circular active area and bezel; Wokwi's generic breakout adapter around it is still rectangular. Its 264×264 presentation includes a 12-pixel bezel and does not change the controller's 240×240 resolution.

The sketch uses artwork generated from the actual Webots face renderer: idle, happy, sleepy, listening, thinking, speaking, alarm, heart, goodnight, music and blink. Speaking and music have eight animation frames; automatic blinking is disabled to keep idle eyes still. Clock and status labels remain inside the circular safe area. Upload both `face_assets.h` and `face_renderer.h` alongside the other Wokwi files.

Use Serial Monitor commands such as `face heart`, `face speaking`, `face music` or `face goodnight` for an eight-second visual preview. These commands do not start real audio, recording or network delivery. Talk and crown switches still exercise the connected firmware inputs. Regenerate artwork with `.venv/bin/python electronics/generate_face_assets.py`; verify the actual sketch's rendered pixels against Webots with `.venv/bin/python electronics/tests/check_face_rendering.py` from the project root.

### Keyboard controls in Wokwi

Click the simulation canvas before using keys (so they do not go into the code editor or serial input). T toggles talk/PTT status, J lowers volume, K raises volume, P presses the left crown switch and O presses the right crown switch. Holding a key holds that connected switch. Mouse controls still work. These shortcuts drive the actual simulated pushbuttons; they are not direct firmware function calls.

Direct Wokwi retest: [19 November wiring correction and results](reports/WOKWI_TESTS_2026-11-19.md). GPIO39 is the VN board terminal; the corrected diagram and native terminal validation are included.

### If the buttons are offscreen after starting

Starting the simulation opens the Serial Monitor and reduces the canvas height. Collapse the monitor with its down-arrow control, click a blank part of the running canvas and press F to fit the circuit. Use + once or twice if needed, keeping the five blue buttons visible. Press and hold the centre of a button briefly; on Mac, Cmd-click latches it until the next click. Wait for READY before interacting. The Wokwi browser project is unsaved; keep the tab open or restore it from the local source files if closed.

Complete hands-on checklist: [Dizzy testing guide](TESTING_GUIDE.md).
