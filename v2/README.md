# Dizzy V2

Full-motion prototype with a 1.75-inch AMOLED, eight joints, 24 reactions, voice conversation and real phone audio firmware. The desktop work is runnable now. The first hardware build is estimated at **₹9,752** including charger and print allowance. Confirm the delivered total stays below ₹10,000. [Parts estimate](hardware/BOM.csv)

## Run on this Mac

1. Double-click **Start Dizzy V2.command**. It opens [the local control panel](http://127.0.0.1:8875).
2. Double-click **Open V2 Webots.command** to watch the physical-motion model. Select **Movement** in the panel. Select floor mode and arm it before trying a short dance or shuffle.
3. Try **Reactions**, select several stars and use **Use my favorites** to assign them to an event. Switch between Dizzy and Partner to see a wave or good-night greeting arrive.
4. Use **Start recording**, say “Look left”, then click **Stop recording**. Try “Tell me a fact about the Moon” for conversation and “Set an alarm for seven” for time clarification. Typed prompts use the same action path. Browser voice uses macOS microphone permission. The latest automated run used simulated microphone audio through the real Whisper/Piper pipeline.

The desktop demo uses the existing `.venv`, Whisper and Piper models, and Mosquitto. It reads the existing local `.env` for the Gemini key without printing it. Use `--provider ollama` to choose a local model instead. Clock, alarms, games and simulated phone music work with the language model unavailable. The desktop alarm and gesture state belong to the active simulator process. The flashed head firmware owns those local desk tools on the physical robot.

To open the independent LVGL preview, run `v2/tools/build-preview.sh` from the project root. Open `v2/.work/preview/dizzy-preview` and use the arrow keys to step through reactions. It uses the same C++ renderer as the AMOLED firmware.

## Circuits and firmware

- [Wiring table](hardware/wiring.csv), [physical bring-up](hardware/ASSEMBLY.md), [Wokwi guide](hardware/wokwi/README.md) and [ngspice model](hardware/power/battery.cir).
- Run `v2/tools/firmware.sh audio` for the Classic ESP32 build and `v2/tools/firmware.sh head` for the Waveshare S3 build. The helper stages builds in a path without spaces and uses ESP-IDF 5.5.5.
- Set Wi-Fi, the Mac bridge URL and a local device token in the head's ESP-IDF **Dizzy V2** settings. Build with `v2/tools/firmware.sh head menuconfig`. Use the same token in the Mac environment as `DIZZY_V2_DEVICE_TOKEN` and run `v2/tools/start-demo.sh --bind 0.0.0.0` on a trusted LAN. Keep the token and Wi-Fi password out of project files and shared binaries.
- Use `v2/tools/firmware.sh head -p PORT flash monitor` and the equivalent `audio` command for each device. The default S3 image leaves motors disabled. Use the physical bring-up sequence before enabling upper-body or floor motion. On the completed hardware, put the audio board into discovery with **Menu → Phone music → Pair**, then pair with **Dizzy Music** in the phone's Bluetooth settings.
- The existing simulation and real device bridge have separate identities. The V2 body uses ESP-IDF and the Waveshare board support package. The electronics harness uses a DevKit surrogate and its own sketch.

## CAD and validation

- [FreeCAD assembly](cad/output/Dizzy_V2.FCStd), [assembly GIF](cad/output/assembly.gif), [CAD assembly guide](cad/README.md), [component fit report](cad/output/fit-report.json).
- The separate `webots/worlds/dizzy_v2_cad.wbt` scene displays CAD-derived meshes. See the [test report](reports/TEST-REPORT.md) for confirmed, failed and hardware-dependent checks.
