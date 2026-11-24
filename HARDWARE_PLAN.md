# Dizzy: component-first round-display revision

Decision date: 18 November 2026. This is the baseline for the next enclosure revision. The Webots model now implements this round-display revision. Its assembly volumes are provisional until physical samples are measured. No parts have been purchased.

## Display choice and sourcing

**Selected part: Techtonics TECH2512 — 1.28-inch round GC9A01 7P SPI display, 240×240 pixels, non-touch.** This is the display baseline for the first prototype. The head petting electrodes provide touch interaction independently of the screen. Avoid paying for an integrated touchscreen/processor board when those functions are already provided elsewhere.

| Candidate | Price including GST when checked | Availability and decision |
|---|---:|---|
| Techtonics GC9A01 7P module, TECH2512 | ₹449 | Selected for prototype; previously listed in stock |
| Robocraze GC9A01, TIFDP0143 | ₹449 on latest page | Sold out on latest check; backup seller only |
| HUBTRONICS generic round plate, 05769 | ₹447 | Out of stock; backup only |
| Waveshare 19192 via ThinkRobotics/Atlantis | ₹1,499.99 | Listed in stock; branded alternative, not selected for the budget build |

Links:
- Selected budget module: https://techtonics.in/product/1-28-inch-round-display-module-gc9a01-7p-240x240-spi/
- Backup: https://robocraze.com/products/1-28-inch-round-tft-display-module-240x240-hd-ips-full-color-screen
- Branded alternative: https://thinkrobotics.com/products/waveshare-1-28inch-lcd-module
- Waveshare manufacturer specifications: https://www.waveshare.com/1.28inch-LCD-Module.htm
- Waveshare technical guide: https://www.waveshare.com/wiki/1.28inch_LCD_Module

The selected part was previously listed at ₹449 including GST. A repeat page fetch timed out when recording the final choice, so stock and price need rechecking before purchase. Seller documentation establishes a low-cost candidate; it does not establish tested production reliability. Qualify a sample for dead pixels, uniform brightness, viewing angle, stable SPI operation, and repeated power-up before committing to an enclosure or buying two units.

The Waveshare version publishes a 32.4 mm active diameter and a 40.4×37.5 mm board envelope. Generic GC9A01 boards use different PCB shapes, headers and outlines. **Do not apply Waveshare mounting dimensions to the Techtonics board.** Obtain its actual drawing or measure the purchased sample, including the header and cable, before freezing the display pocket. Use 3.3 V logic and confirm the particular module's supply/backlight requirements.

## Final selected baseline

The complete selected list is in **hardware/BOM.csv**, with quantities, supplier links and observed prices. The readable list is **hardware/SHOPPING_LIST.md**. The earlier ₹2,400–₹3,700 estimate was a preliminary allowance; it did not include the now-selected official main board, stronger USB-C power path or complete lifting-arm provisions. Budget approximately **₹6,500–₹8,500 before enclosure printing and delivery**, with supplier taxes/quotes to be rechecked. No purchase has been made.

Selected controller: original ESP32-DevKitC-32E; round TECH2512 display; ESP32-CAM with compatible long-flex OV2640; three positional SG90-class servos (head and planned two shoulders); PCA9685 driver; INMP441 microphone; MAX98357A amplifier; PUI AS02804PR-N50-R 28mm speaker; DS3231 clock with a correctly matched noncharging backup-cell arrangement.

Selected power: official 27W Raspberry Pi USB-C supply with 5.1V/5A profile, captive cable and Adafruit 5807 HUSB238 PD input. Select the 5V PDO and verify the 5A contract before enabling all three servos. No main battery or lithium charging circuit is included. This uses the existing Mac for voice, so there is no Raspberry Pi computer in the bot.

Original ESP32 is chosen for Bluetooth Classic A2DP. ESP32-S3 supports BLE but not Bluetooth Classic; it is not an equivalent drop-in for this music architecture. Complete firmware memory, radio and audio stress checks remain physical prototype work.

## Petting / pamper controls are retained

The current Webots prototype already has `pet_left` and `pet_right` sensors. They were hidden under the crown to avoid protruding buttons. They have not been removed.

For the round-display revision, retain **two separate capacitive electrodes beneath the left and right crown**, read by the ESP32 touch peripheral. Put a small printed or recessed touch mark over each zone, flush with the enclosure. These are petting areas, not physical pushbuttons and not touchscreen areas. Exact electrode size and shell thickness are prototype variables; start with approximately 18×15 mm electrodes under thin non-metallic plastic, calibrate and test with the final material. Keep the wiring away from the servo power path and antenna.

| Input | Result |
|---|---|
| Single head tap | Blink/happy reaction and chirp; no remote message |
| Stroke across the two zones | Happy closed eyes and gentle head response |
| Double tap | Send partner greeting once; show acknowledgement/failure |
| Hold for approximately 1.2 seconds | Send good night once on release |
| Any head tap while alarm rings | Snooze; consumes gesture so it cannot send a greeting |
| Dedicated talk button | Push-to-talk voice interaction |
| Two local volume buttons | Change volume; recessed/flush caps, separate from petting |

Firmware must debounce, calibrate baseline drift, delay single-tap classification until the double-tap window closes, and suppress accidental taps after a stroke/hold. The simulated touch interactions already cover the gesture rules; real sensitivity, wet hands, servo noise and enclosure material require bench checks. Use discrete touch modules only if native touch cannot meet those checks; they are not silently added to the baseline cost or pin count.

## Matched enclosure and hands

The seated Webots model now uses a102×86×92mm generating helmet (trimmed depth69mm, height88.5mm), a smaller torso,120×116×60mm seated hips and forward feet. A terracotta rim and cosmetic black face surround frame the actual32.4mm round LCD. The large crown pad retains two petting electrodes. Recording uses the chest capsule; volume uses the two helmet ear controls. USB-C remains at the rear of the hips.

Both shoulder joints are implemented with measured simulation feedback and0–120° bounds. Sleeve/cuff/mitten shapes replace the fixed flippers. See hardware/HANDS_PLAN.md and SEATED_COMPANION_DESIGN.md for gestures and component placement. The model uses assumed arm masses and a fixed root; physical linkage, current, torque, stability and all electrical qualification remain outstanding.

## Round-screen UI rules

The 240×240 framebuffer has a circular visible area. Keep the complete illuminated pixels inside an inset circle (initial safe radius 108 pixels about the screen centre). Checking only the outer square rectangle is insufficient.

Use eyes above a centred HH:MM clock. Use short icons or split labels for listening, alarms and good night. Long transcripts stay in the computer control panel. Check the rasterized pixels for every expression, blink, speaking animation and clock width against the circular safe mask. Choose font sizes at actual physical scale, not only in a magnified preview.

## Build order

1. Qualify the selected display and confirm its PCB/header dimensions. Obtain the exact development board and breakout outlines and complete the pin/power map.
2. Bench-test two petting electrodes, talk/volume switches, LCD and RTC together. Test alarm timing and snooze without the computer.
3. Add servo, microphone and speaker. Check false touches during movement, audio noise, resets and full audio/animation/Wi-Fi/Bluetooth load.
4. Fit component volumes and cable routes, then revise the Webots enclosure with the real circular display and visible flush petting marks. Verify all head and moving-arm clearances.
5. Run the circular-pixel clipping tests and repeat existing behavior, voice, camera and paired-pet checks. Record failures separately from simulation passes.
6. Print a fit prototype; check mounting, heat, touch and servo load, then freeze enclosure drawings.

## Supporting technical references

- ESP32 Bluetooth capability matrix: https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-guides/bt-architecture/overview.html
- Native touch sensing: https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/peripherals/cap_touch_sens.html
- ESP32 touch design example: https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32/esp32-sense-kit/user_guide.html
- Positional SG90: https://towerpro.com.tw/product/sg90-analog/
- Amplifier: https://www.analog.com/en/products/max98357a.html
- Clock: https://www.analog.com/en/products/ds3231.html

## Implemented design files

The component baseline is expanded into hardware/BOM.csv, hardware/pinmap.json and hardware/ASSEMBLY.md. The round Webots screen, marked crown pads, moving arms, speaker grille, microphone opening, rear power socket and flush local controls are implemented. COMPONENT_FIT.md records current dimensions and provisional assumptions. Electrical wiring and ESP32 firmware remain the next physical prototype stage.

The compact revision is203mm tall and167mm across the hands. ESP32/PCA9685 move flat into the hips; higher shoulder pods house both arm servos. The bill of materials is unchanged. Full revised dimensions and fit evidence are in SEATED_COMPANION_DESIGN.md.
