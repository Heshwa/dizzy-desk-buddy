# Dizzy connected fit review

**The revised design passes the CAD service checks.** The physical prototype still requires measured plugs and boards, a small calibration print and unpowered dry-fit before the complete enclosure is printed.

The first connected review found a blocked rear USB-C inlet, nine modelled component contacts and reported two clear cable routes. The revised case centres a 15.4 × 10.6 mm pocket on the recessed socket. The ESP32 tray has header slots and programming-plug relief. The LCD, servo-driver and microphone retainer bridges moved off the connector areas. The neck bridge has splined-shaft clearance, the nearby capacitor carrier moved, and cable entries were opened through the inboard shoulder shells. The exterior scale stays at +7.5%.

Open **Connected fit** in the CAD preview to show the installed hardware, removable covers and cable paths. The Adafruit 5807 uses the manufacturer model. Other hardware combines published dimensions with provisional vendor-specific features. The cable elbow meshes are centred on the route waypoints. This corrects an error in the first study that placed some elbows at the assembly origin and could incorrectly flag the bottom cover.

## Repeated CAD tests

| Check | Result |
|---|---|
| Modelled rigid components | 0 component-pair contacts and 0 contacts with shells, trays or retainers. |
| Rear USB-C access | **Clear**. The seated and full insertion gauges clear when no contacts are listed. The 12.4 × 7.6 mm overmould gauge and tip were swept through a continuous corridor with 0.3 mm added on each side. Socket recess 9.72 mm. The sweep includes shells, mounts, unrelated hardware and cable routes. |
| ESP32 programming | **Clear** with the rear hip cover removed. The closed case still obstructs the approach at Hip_rear. |
| Cable routes | 25/25 clear the checked covers, mounts and unrelated modelled hardware. 0 sampled wire-pair overlaps outside shared connector fan-outs. |
| Camera ribbon | 75 mm service loop checked as a 13.5 × 0.8 mm flat envelope. |
| Head articulation | 19/19 samples clear at 5° steps across ±45°. The assumed 6.5 mm harness clears the 11 mm bore. |
| Shoulder articulation | 50/50 individual 0–120° arm poses and 950/950 combined arm and head poses clear the checked installed parts and cable envelopes. |

The routing check uses swept bundle envelopes against solids and half-millimetre centreline samples for bundle spacing. Branches sharing a connector may meet within a 9 mm fan-out. JR servo leads use a provisional 3.1 mm envelope at 3.4 mm socket pitch. Measure effective bundle widths and add bend and pull relief on the real harness. The sampled head harness envelope stays on the yaw axis. Cable twist, bend radii, connector engagement and screw/tool access require the physical fit test.

## Outstanding prototype checks

- Camera optics and ribbon. The 6 mm aperture with 5.1 mm setback yields an idealised 60.9° clear cone. Bench-check the selected 120° lens, ribbon width, bend transitions, retention and flex connector orientation.
- Acoustics. Speaker grille path is about 16.0 mm. The microphone PCB centre is about 58.5 mm from its opening. Check sealing, isolation and feedback using the selected devices.
- Confirm plug overmoulds, breakout variants, electrical current margin, minimum print walls, fastener fit, load and durability on hardware. Build and dry-fit the USB-C opening and carrier samples before ordering a full print.

## Model dimensions

- **Espressif ESP32 DevKitC V4**. Official 48.26 × 27.94 mm PCB outline. Module/socket stack and plug dimensions are assumptions. [Reference](https://dl.espressif.com/dl/schematics/esp32_devkitc_v4_dimensions.pdf)
- **Adafruit HUSB238 5807**. Manufacturer 3D file, including the tall terminal block. The chosen cable overmold uses a provisional gauge. [Reference](https://learn.adafruit.com/adafruit-husb238-usb-type-c-power-delivery-breakout/downloads)
- **TECH1049 PCA9685 servo board**. Supplier 62 × 25 mm outline. Header, screw terminals and JR plugs are occupied volumes. [Reference](https://techtonics.in/product/pca9685-16-channel-12-bit-pwm-servo-driver-i2c-interface/)
- **TECH2512 round GC9A01 LCD**. 1.28-inch display class. 46 × 40 mm carrier orientation and header position await a measurement. [Reference](https://techtonics.in/product/1-28-inch-round-display-module-gc9a01-7p-240x240-spi/)
- **ESP32-CAM and separate OV2640 lens**. Supplier 40 × 27 × 12 mm board size. Lens bracket/FPC pin and connector positions remain provisional. [Reference](https://techtonics.in/product/esp32-cam-wifi-bluetooth-development-board-with-ov2640-camera-module-2mp/)
- **DS3231 and coin-cell holder**. The supplier variant needs measurement. PCB and plug placement are representative.
- **MAX98357A amplifier**. The supplier variant needs measurement. PCB and plug placement are representative.
- **INMP441 microphone**. The supplier variant needs measurement. PCB and plug placement are representative.
- **5 V distribution board**. The supplier variant needs measurement. PCB and plug placement are representative.
- **PUI Audio 28 mm speaker**. Manufacturer 28 × 7.5 mm nominal speaker plus a separate diaphragm-travel gauge. [Reference](https://puiaudio.com/product/speakers-and-receivers/as02804pr-n50-r)
- **TowerPro SG90 neck**. Manufacturer body specification 23 × 12.2 × 29 mm. Shaft centre and housing orientation are trial values. [Reference](https://towerpro.com.tw/product/sg90-analog/)
- **TowerPro SG90 left shoulder**. Manufacturer body specification 23 × 12.2 × 29 mm. Shaft centre and housing orientation are trial values. [Reference](https://towerpro.com.tw/product/sg90-analog/)
- **TowerPro SG90 right shoulder**. Manufacturer body specification 23 × 12.2 × 29 mm. Shaft centre and housing orientation are trial values. [Reference](https://towerpro.com.tw/product/sg90-analog/)

Open `connected-fit.json` for the exact contact names, waypoints and sampled poses. See `wiring-routes.csv` for the route and pin labels.
