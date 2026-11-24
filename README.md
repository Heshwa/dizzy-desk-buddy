# Dizzy desk pet project

This repository contains the original V1 simulation and the newer V2 full-motion prototype. For the current design and implementation, start with [Dizzy V2](v2/README.md). New contributors and agents should follow the [handover guide](HANDOVER.md) and use the [V2 test report](v2/reports/TEST-REPORT.md) to distinguish simulation results from hardware checks. The sections below document V1.

Dizzy is a seated mini humanoid in Webots with two lifting mitten hands, a rotating head, animated 240×240 face on a recessed 1.28-inch round GC9A01 LCD, two touch zones, camera, speaker, clock, alarms, music controls, and a paired pet. The desktop voice service supports push-to-talk speech and typed requests using Gemini tools.

The compact revision is about20.3cm tall and16.7cm across the hands. It keeps the selected parts, with higher shoulders, tapered forearms and smoothly blended mittens.

The large top pad is for petting; the chest capsule starts/stops recording; the helmet ear buttons adjust volume. Use **Show components** to inspect the fitted board spaces. See [the seated design](SEATED_COMPANION_DESIGN.md) and [test report](reports/TEST_REPORT.md).

## Prototype enclosure CAD

The seated enclosure is available as a FreeCAD prototype with STEP and STL exports, individual component carriers, calibration prints and a separate Webots review scene. See [the CAD assembly and print guide](cad/README.md).

The revised enclosure passed the connected CAD service checks for USB-C insertion, the component mounts and all 25 cable routes. The ESP32 programming plug is accessible with the rear hip cover removed. See the [fit and motion results](cad/fit-study/FIT-REPORT.md) and [project documentation](docs/Dizzy%20Project%20Documentation.docx) for the status of the physical prototype and simulator tests.

## Start

Double-click **Start Dizzy.command**, or run the following from this folder.

```sh
./scripts/launch.sh
```

Open [Dizzy controls](http://127.0.0.1:8765). Keep Webots running in real-time mode. Press Ctrl+C in the launch terminal to stop the session. The launcher stops the processes it started. Logs are in `runtime/`.

This Mac has Webots installed at `/Applications/Webots.app`. It uses the official R2025a nightly build dated 17 November 2026 because the stable release has a macOS 27 startup defect. This build is from the [official Webots release](https://github.com/cyberbotics/webots/releases/tag/nightly_17_11_2026). The [upstream issue](https://github.com/cyberbotics/webots/issues/6976) describes the fix. Webots lowers graphics settings on Apple GPUs. The simulation was tested with these settings.

## Setup on another Mac

Install Homebrew and Python 3.13, install the Webots build above, then run `./scripts/setup.sh`. It creates a Python environment, installs the local Mosquitto broker and whisper.cpp, downloads the English base transcription model and the Piper English voice, generates original sample audio, and sets Webots' Python path. Run setup again after moving this project to a different folder.

Copy `.env.example` to `.env`, then add your Gemini API key. Keep your API key only in your local `.env`; that file is excluded from version control and must stay local. Use a Gemini API project on the free tier. The selected model is configurable through `DIZZY_GEMINI_MODEL`. Model availability was verified with real generation requests. `DIZZY_GEMINI_FALLBACK_MODEL` selects the fallback model; its default is gemini-3.5-flash-lite. Free-tier availability and quotas are account-dependent.

## Controls

Use Wave hand, Both hands hello, Lift hands and Rest hands to animate the shoulders. Show components opens a translucent assembly view; Close shell restores the exterior. The large crown pad is for petting, the chest capsule starts/stops recording, and the side ear caps adjust volume. See SEATED_COMPANION_DESIGN.md for the fitted design.

Use the control panel to pet, stroke, or hold the head, turn the head, set alarms, run timers, toggle quiet mode, play music, take photos, move the camera target, and send paired gestures. Select Your Dizzy or Partner Dizzy at the top. A head hold must last at least 1.2 seconds. Two taps within 350 milliseconds send a greeting. Single taps react after the double-tap window closes. While an alarm rings, a tap snoozes it for five minutes.

For voice, click **Record**, speak, then click **Stop recording**. macOS may ask for microphone access. Type a request into **Ask Dizzy** to exercise the same model and tools without recording. Voice replies play through the Mac's speakers. Disable **Speak replies** to keep the result as text. Recording stops and processes automatically after 30 seconds. Stop releases the microphone immediately and the button changes to Processing while transcription and the reply finish. If you switch pets during a recording, Stop still controls the pet that owns the microphone. The final reply or error appears automatically. The first local speech transcription may take longer while the model loads.

Try “What time is it?”, “Set an alarm for seven”, “Look left”, “Pause music”, “Take a photo”, or “Send a wave to the other Dizzy”. Connect the simulated phone before asking for music playback. Alarms use Asia/Kolkata. Cancel saved alarms from their rows in the panel. Restarting the robot preserves alarms, volume, and quiet mode.

With the Webots 3D view focused, use these keys on Your Dizzy.

| Key | Action |
| --- | --- |
| W / H | Wave one hand / both-hands hello |
| T | Pet or snooze |
| S | Stroke the head |
| G / N | Send wave / good night |
| V | Start or stop voice recording |
| A | Start a five-second timer |
| F / C | Toggle tracking / capture photo |
| P / M | Connect phone / play or pause music |
| + / - | Increase or decrease volume |
| Q | Toggle quiet mode |

The physical sensor nodes are present in the model. On-screen gestures and keyboard controls provide repeatable touch input. The camera tracks a recognizable moving object in the Webots scene. Photos are saved in `runtime/`. Saved settings and alarm data are in separate `runtime/dizzy-a.json` and `runtime/dizzy-b.json` files. Active timers belong to the current run. Overdue alarms ring when less than one minute late, then become disabled or advance to the next recurrence.

## Architecture and interfaces

The Python Webots controller owns device state and alarm scheduling. The network workers exchange messages through queues so Webots API calls stay on the simulation thread. The voice service owns microphone capture, transcription, model requests, and speech synthesis. Restarting the voice service leaves local alarms and MQTT gestures running.

The service binds to loopback at port 8765. These interfaces are for local development.

| Interface | Purpose |
| --- | --- |
| `GET /api/status` | Connected devices, state, recent events, recording status |
| `POST /api/action` | Execute `{device, action, args}` and receive `{ok, result}` or `{ok, error}` |
| `POST /api/chat` | Submit `{device, text, speak}` and receive a reply or error |
| `POST /api/record` | Send `{device, operation: "start"}` or `{device, operation: "stop", session_id}`. Stop acknowledges microphone release immediately; `/api/status` exposes the completed voice result. Calls with only `{device}` preserve the original toggle-and-await behavior |
| `WS /device/{id}` | Controller status, action requests, correlated results, and device events |

`dizzy/tools.py` defines the LLM's action schemas. `dizzy/core.py` contains device behavior. `dizzy/providers.py` supplies Gemini and Ollama providers through the same action executor. Only the declared model tools are available to the LLM. Test operations such as screenshots and controller restart are excluded from the model's tools.

The MQTT broker listens on loopback at port 18884. Per-device topics under `dizzy/demo` carry presence, gestures, acknowledgments, and telemetry. Gestures use QoS 1, unique identifiers, a ten-second expiry, persisted duplicate detection, and no retained event. Presence has a heartbeat and last-will message. Delivery means an acknowledgment arrived. If it does not arrive, the sender shows unconfirmed.

For two computers, configure a hosted broker with TLS, per-device topic access, and credentials in `.env` on both machines. Change `DIZZY_MQTT_HOST`, `DIZZY_MQTT_PORT`, `DIZZY_MQTT_TLS`, username, password, and a pair-specific topic prefix. The two device IDs must be `dizzy-a` and `dizzy-b`. The default single-machine scene runs both pets to test the message flow. Testing through two different internet connections remains a separate check.

For a local LLM later, install Ollama and a tool-capable model, then set `DIZZY_PROVIDER=ollama` and `DIZZY_OLLAMA_MODEL` in `.env` before restarting. This adapter is supplied. The current acceptance run uses Gemini.

## Verify

```sh
.venv/bin/python -m pytest -q
.venv/bin/python scripts/check_simulation.py
```

Run the second command while the launcher and Webots are active. It exercises the actual robot controllers and Gemini service, changes demo state, and saves evidence in `reports/`. It uses your Gemini quota. `scripts/check_recovery.py` verifies controller restarts and MQTT duplicate suppression. `scripts/check_service_outage.py` temporarily stops and restarts the voice service to test independent alarm audio. Run these recovery checks when no one is using voice recording. The tests create a short alarm and cancel its snoozed copies afterward. See `reports/TEST_REPORT.md` for recorded results and outstanding checks.

## Hardware validation

The simulation tests device behavior, real desktop voice processing, and MQTT delivery between two controllers. Phone pairing is represented by a simulated connection and local demo tracks. The camera uses Webots recognition of the scene target. The microphone and generated voice use the Mac's audio devices.

Physical Bluetooth pairing, ESP32 firmware, I²S audio, capacitive sensing through an enclosure, camera image processing on real frames, servo load, supply design, and battery-backed clock wiring need hardware verification. The intended boards remain the original ESP32-WROOM-32 DevKit and a separate ESP32-CAM. The geometry is a functional model for simulation. Final enclosure design and wiring follow hardware verification.

Component dimensions, display purchase links, and enclosure allowances: [COMPONENT_FIT.md](COMPONENT_FIT.md). The current seated shape has independently lifting arms, a chest talk button and helmet volume controls.

The implemented component-first revision uses a low-cost round display and two marked head petting zones. See [HARDWARE_PLAN.md](HARDWARE_PLAN.md) for the component baseline, sourcing comparison, budget and fit sequence. The Webots simulation now uses the round-display revision.

Complete parts: [hardware/BOM.csv](hardware/BOM.csv). Wiring and power: [hardware/ASSEMBLY.md](hardware/ASSEMBLY.md). GPIO allocation: [hardware/pinmap.json](hardware/pinmap.json). Component layout: [reports/component-layout.png](reports/component-layout.png).

Selected parts and purchase links: [hardware/SHOPPING_LIST.md](hardware/SHOPPING_LIST.md). Planned lifting-arm mechanism: [hardware/HANDS_PLAN.md](hardware/HANDS_PLAN.md). Verify the current round model with `.venv/bin/python scripts/check_round_design.py`.

## Voice feedback

The Talk panel shows “Heard:” after transcription, then the reply or failure. Its provider line shows whether sound is on, muted by quiet mode, or set to zero volume. Quiet mode suppresses speech; turn it off for spoken replies. Temporary Gemini server errors can switch once to the fallback model before tools execute. The primary model then has a60s cooldown. Explicit head/hand/music commands and creator questions run locally. Speech stays loaded, and text previews appear before audio finishes. The last voice-output repair was verified with an actual user microphone request; see reports/voice-repair-checks.json.

Dizzy’s pet identity is “created and developed by Heshwa for Yoga.” See reports/VOICE_LATENCY.md for measured delays, Google outage traces and safe fallback behavior. The last full voice-speed run passed along with130 automated checks.

Electronics simulation: [lab and launch guide](electronics/README.md), [connection diagram](electronics/wiring.svg), [test results](electronics/reports/TEST_REPORT.md). The lab runs ESP32 bring-up firmware in Wokwi and assumed power loads in ngspice, separately from the Webots pet simulation.
