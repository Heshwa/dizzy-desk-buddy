# Dizzy V2 prototype test report

## Passed on the Mac

| Check | Result |
|---|---|
| V1 regression | 131 tests passed. V2 assets and runtime are in a separate project. |
| Shared LVGL renderer | Rendered all 24 reactions and six status faces. Desktop actions preview and assign multiple picks. Idle held still between its clocked blink windows. |
| Local tools and preferences | Alarm, touch snooze, timer, and restart persistence passed with a simulated device. Preferences and alarms survived a fresh process loading saved state. |
| Phone controls | Simulated connection, track skip, disconnected command rejection and gain recovery passed. Volume returned to 65% after a speech duck. |
| Voice in the browser | Automated Chrome microphone fixture used Start and Stop. Generated audio (not a real microphone recording) passed through Whisper, transcribed “Look left,” drove the simulated head, and produced a Piper reply. The same panel was checked at mobile width. |
| Live Gemini | Text requests to the live Gemini provider received replies. A separate text request drove the device tool and confirmed a measured 24° simulated head turn. Gemini was not tested with live microphone audio. Ambiguous alarm wording asked for AM or PM and accepted the follow-up. |
| Partner gestures | Waves and good-night events were acknowledged by the two simulated identities on Mosquitto. Duplicated and expired events were covered. A stand-in for the hardware tested device authentication, action acknowledgments, and gestures in both directions. |
| Real firmware build | Both ESP-IDF targets built. The S3 build includes the Waveshare board support package, codec I/O and independent local tools. The Classic ESP32 build includes A2DP, AVRCP and I²S. Neither binary has been flashed to a physical robot on this Mac. |

## Passed in the motion and power models

- **Webots.** Ten shuffle cycles covered **30.4 cm forward** and **31.6 cm total**, without a fall. The sway, heel-tap and bounce trials each remained upright for 60 seconds and moved their target joints. The joint-limit sweep measured approximately ±45° yaw and −20° to +25° pitch, plus both shoulder axes. The final run had self-collision enabled. The CAD-derived scene uses the same physics model with the exported visible shell meshes.
- **ngspice.** The fresh, nominal and low-charge source models kept both rails above 4.75 V under prescribed loads. Aged and undercharged profiles fell below the limit and were flagged as expected. The model reached about 6.1 A pack demand in the low-charge case. It does not model the actual BMS trip curve, converter loop, motor feedback or heating.
- **FreeCAD.** 49 individual printable solids were valid, watertight and within the provisional 180 mm envelope using sampled STL bounds. There were zero overlaps between modeled component boxes in the final placement layout. This check covers the boxes only. Connector extraction, cable strain, fastening, shell clearances and the final weight distribution need a measured assembly. The printed solids are about 268 g solid-equivalent for the robot and about 330 g including the dock and gauge. Slicer mass and a real loaded gait rig will determine the final mass.

## Pending and release conditions

| Check | Reason or release condition |
|---|---|
| Wokwi live circuit | The ESP32-S3 fixture and three custom WASM chips compiled. The CLI stopped at its missing-token check. The full simulator run is pending. |
| Real Android and iPhone music | Verify actual pairing, AVRCP support, 30-minute audio streams, reconnect and ducking on the built speaker. |
| Real microphones and headphones-off speaker output | Verify the Waveshare mic channels, recording latency, local speaker playback and physical chest switch. The automated voice check used generated audio. |
| Real AMOLED response | Measure 100 ms input feedback, 30 fps animations, safe-area clipping and power on SKU 31261. |
| Physical power and gait | Verify protection, current ratings, rails, shutoff and temperature under load. Weigh the open rig before gait evaluation. Early simulated gait variations failed or fell, and the passing gait is closely tuned to the tested model. Add the actual battery, retest ten strides and three 60-second dances, and report measured battery runtime. |
| Print approval and budget | The CAD is a provisional fit study. Confirm measured mounts and removal paths, slice the parts, and get an actual print and delivery quote. ₹9,752 is the parts and delivery estimate. Pause if the delivered total reaches ₹10,000. |

Raw checks are in [demo.json](demo.json), [browser.json](browser.json), [persistence.txt](persistence.txt), [device-bridge.json](device-bridge.json), [webots.json](webots.json), [webots-cad.json](webots-cad.json), [power.json](power.json) and the [FreeCAD fit report](../cad/output/fit-report.json).
