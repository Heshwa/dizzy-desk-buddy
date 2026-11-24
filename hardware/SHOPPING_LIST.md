# Dizzy selected components and links

Final prototype baseline: 18 November 2026. Prices are observed listings or planning allowances, not a checkout quote. Recheck stock, GST and shipping before purchase. No items have been ordered. The complete assembly, including planned lifting arms, is expected to be roughly **₹6,500–₹8,500 before enclosure printing and delivery**. Earlier estimates were rough allowances and excluded the final official controller/power selection and arm provisions.

## Main parts

| Part | Qty | Selected link | Notes |
|---|---:|---|---|
| Main controller | 1 | [Espressif ESP32-DevKitC-32E](https://robu.in/product/espressif-esp32-devkitc-esp32-wroom-3-2e-development-board/) | Original ESP32 with Bluetooth Classic; official board listing ₹1,129. |
| Round face | 1 | [Techtonics TECH2512 GC9A01](https://techtonics.in/product/1-28-inch-round-display-module-gc9a01-7p-240x240-spi/) | 1.28-inch IPS SPI, 240×240, non-touch; previously ₹449. Physical module outline must be measured. |
| Camera board | 1 | [ESP32-CAM + OV2640, TECH3184](https://techtonics.in/product/esp32-cam-wifi-bluetooth-development-board-with-ov2640-camera-module-2mp/) | Listed ₹775. Separate camera processor and PSRAM. |
| Front camera flex assembly | 1 | [Compatible OV2640 75mm 24-pin assembly](https://probots.co.in/ov2640-120-degree-wide-angle-lens-2mp-camera-module-24pin-75mm.html) | Replaces short-flex bundled lens for positioning. Verify connector compatibility and actual horizontal FOV; listing is the wide-angle variant. |
| Microphone | 1 | [INMP441 TECH1488](https://techtonics.in/product/inmp441-mems-omnidirectional-microphone-module-high-precision-snr-low-power-i2c-interface-supports-esp32/) | Listed ₹140. It uses I2S; the seller title incorrectly says I2C. |
| Audio amplifier | 1 | [MAX98357A TECH2003](https://techtonics.in/product/max98357-i2s-3w-class-d-amplifier-interface-audio-decoder-module-filterless-board/) | Listed ₹130; mono music and voice. |
| Speaker | 1 | [PUI Audio AS02804PR-N50-R](https://in.element14.com/pui-audio/as02804pr-n50-r/speaker-250hz-20khz-4-ohm-76-5dba/dp/4411358) | 28mm, 7.5mm deep, 4 ohm, 3W nominal. Listed ₹724.78 before checkout additions. Selected documented part, not an unspecified 40mm speaker. |
| Clock / backup holder | 1 | [DS3231 TECH module](https://techtonics.in/product/ds3231-real-time-clock-module-3-3v-5v-precise-with-battery/) | Listed ₹235 with battery. Inspect cell chemistry and charging circuit; disable any charger path before using a non-rechargeable cell. Run I2C at 3.3V. |
| Positional servo | 3 | [SG90 180-degree TECH1699](https://techtonics.in/product/towerpro-sg90-9g-micro-servo-motor-180-degree-rotation/) | One neck and two planned shoulders. Supplier lists ₹89 each; qualify actual torque, noise and authenticity. Do not buy continuous-rotation units. |
| Servo driver | 1 | [PCA9685 TECH1049](https://techtonics.in/product/pca9685-16-channel-12-bit-pwm-servo-driver-i2c-interface/) | Listed ₹249. Separate 3.3V logic and 5V motor power. |
| USB-C input | 1 | [Adafruit 5807 HUSB238](https://www.digikey.in/en/products/detail/adafruit-industries-llc/5807/21839778) | Listing ₹565.90 before checkout tax/delivery. [Manufacturer](https://www.adafruit.com/product/5807). Select only 5V PDO over I2C and verify actual 5A contract before enabling motion. |
| External power | 1 | [Official Raspberry Pi 27W USB-C supply](https://hubtronics.in/rpi-foundation/raspberry-pi-5-c-supply-27w) | Listed ₹1,275 including GST, 140 in stock at check. Select Indian plug. Rated 5.1V/5A profile and captive cable; this is only the charger, not a Raspberry Pi computer. |
| Camera programmer | 1 shared | [ESP32-CAM-MB TECH2480](https://techtonics.in/product/esp32-cam-mb-micro-usb-download-module-for-esp32-cam-development-board/) | Setup tool, stays outside the enclosure. Match micro-USB data cable. |

## Small parts and mechanical assembly

| Parts | Quantity / specification | Link |
|---|---|---|
| Petting electrodes | Two approximately 18×15mm pads; use overlapping/soldered copper strips under crown | [Conductive copper tape TECH2329](https://techtonics.in/product/conductive-copper-foil-tape-roll-10mm-x-10mtr/) |
| Talk / volume switches | Three 6×6×5mm momentary switches; use three from the supplier's minimum quantity of ten | [TECH1779 tactile switches](https://techtonics.in/product/tactile-push-button-switch-4-pin-6x6x5-pack-of-10/) |
| Resistors | Four 10k pull-ups and one 330 ohm LED resistor, through-hole preferred for prototype | [Resistor supplier category](https://techtonics.in/shop/) — match values; obtain a small quantity locally if bulk-only. |
| Camera LED | One 3mm green LED | [LED supplier category](https://techtonics.in/product-category/indicator-and-displays/leds/) |
| Bulk / local capacitors | Three 470uF/10V electrolytics, one 100uF/10V and six 100nF ceramics | [Capacitor supplier category](https://techtonics.in/product-category/electronic-components/capacitors/) — match specified values; category is not a substitute for a verified exact value. |
| Power switch / wiring | One switch rated at least 5A DC, 18AWG short power trunk, suitable locking connectors, insulated signal leads, perfboard and strain relief | [Switches](https://techtonics.in/product-category/electronics-parts/switches-and-relays/), [connectors](https://techtonics.in/product-category/electronics-parts/connector-and-jumpers/) |
| Neck and shoulder support | Printed brackets/couplers, servo horns, supported shafts/bearings, M2/M3 screws and spacers | [Mechanical supplier category](https://techtonics.in/product-category/mechanical-parts/) — exact linkage parts depend on measured servo/horn and prototype. |
| Enclosure | Printed head, matching oval body, base, current fixed flippers, future shoulder hubs, shutter and rubber feet | Custom model; prototype quote needed. |

The links for commodity passives and custom mechanics are supplier categories, not finalized manufacturer part numbers. Select their electrical ratings as listed and record actual dimensions before assembly. The selected functional modules are specified above; this remains a prototype BOM, not a production-qualified purchasing release.

## Power decision

Use **USB-C desk power**. A normal computer USB port or a random phone charger is not the assumed supply. The chosen supply exposes a 5.1V/5A profile; the HUSB238 must negotiate/select that low-voltage profile and verify sufficient current. Leave motors disabled if it cannot. Higher-voltage PD profiles must never reach the 5V electronics. The supply's captive cable avoids buying a separate high-current USB-C cable.

No main rechargeable battery, lithium cell charger or BMS is included. The RTC cell preserves the time; the bot cannot move, talk or ring an alarm after main USB power is removed. Battery operation can be a separate later revision with a new power and enclosure review.

## Hands decision

Reserve three servos and the driver now. The current simulation keeps fixed arms as the exterior preview. One future lifting axis per shoulder enables wave, hello, excited, listening and sleepy poses. No elbow, wrist or fingers are planned in this first mechanism. See HANDS_PLAN.md for travel, pose sequence, startup disable and power checks.
