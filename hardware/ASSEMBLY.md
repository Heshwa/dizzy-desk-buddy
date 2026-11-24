# Dizzy electrical and mechanical baseline

Use with BOM.csv, pinmap.json and HARDWARE_PLAN.md. This is a prototype wiring plan, not completed ESP32 firmware or a manufacturing release.

## Connections

Main board is specifically original ESP32-WROOM-32E DevKitC V4. Use the JSON pin map as the signal allocation. The separate ESP32-CAM exchanges frames over Wi-Fi. It has its own camera firmware and GPIO assignment; the main-board map does not apply to its camera connector. No microSD card is required for this first version: Mac saves photos and streams speech, and short alarm/chirp samples can reside in main-controller flash.

- LCD: SCK18, MOSI23, CS19, DC27, RESET4, common ground. Use 3.3 V logic and verify the actual TECH2512 module's supply/backlight pinout before applying power. The selected 7-pin variant is not assumed to expose a separate BL pin.
- RTC: SDA21, SCL22, 3.3 V and ground. Confirm pull-ups are to 3.3 V. Select a noncharging backup-cell module. If a ZS-042 charging board is substituted, remove its charging path before fitting a non-rechargeable CR2032. Verify board revision and cell chemistry; do not connect a CR2032 to a charging circuit.
- Audio: BCLK26 and WS25 feed both boards; amplifier DIN32, microphone SD33. INMP441 uses 3.3 V; tie L/R low for left channel. Amplifier powered from 5 V; speaker connects between amplifier SPK+ and SPK-, neither speaker terminal goes to ground. Set amp channel/gain per its breakout documentation.
- Touch electrodes: GPIO13 and14 under left/right crown. Calibrate individually. These are sensing electrodes, not power pins.
- Servos: PCA9685 channel0 neck, planned channel1 left arm and channel2 right arm; logic VCC 3.3V, servo V+ on the separate 5V branch. GPIO16 drives OE with a 10k pull-up to keep outputs disabled at startup. Keep its high current out of the controller 3.3 V regulator. Use positional SG90 servos and physical cable stops at ±45°; the simulated motor limits are not a real torque test.
- Talk/minus/plus: GPIO34/35/39 (GPIO39 is the VN terminal), each with external 10k pull-up to 3.3 V and a normally-open switch to ground. These input-only GPIOs do not supply internal pull-ups.
- Camera activity LED: GPIO17 through 330 ohm resistor and green LED to ground. Drive while capture/tracking is active; the physical shutter gives an independent privacy control.

The selected input is the **official Raspberry Pi 27W USB-C supply, 5.1V/5A PD profile**, with its captive rated cable, feeding an **Adafruit 5807 HUSB238** board at the rear USB-C port. The processor remains ESP32. USB-C is the external power connector, not a rechargeable battery interface or the ESP32 programming/data port.

Keep the HUSB238 5V voltage jumper closed. The board defaults to a 1A request; configure a 3A startup request per its jumper guide, then use I2C to select the 5V source PDO. Confirm the actual negotiated current is 5A before enabling all three servos. I2C selection overrides the resistor-generated RDO according to the HUSB238 datasheet. The 5A negotiation and breakout/terminal temperature still need measurement on the purchased supply and board. A charger label alone is not that test. If 5A is unavailable, leave the arm outputs disabled and report insufficient power. Do not select a 9/12/15/20V PDO for this direct 5V design.

HUSB238 is at I2C address 0x08, PCA9685 at 0x40 and RTC at 0x68. Pull the shared bus to 3.3V and verify any breakout pull-ups. The PCA9685 OE line has an external pull-up, so it stays disabled while the controller boots and negotiates power. Physical firmware must enforce this startup order.

Branch the low-voltage output through a master switch/distribution board to controller, camera, amplifier and servo V+. Ground all branches together. Use two 470uF/10V capacitors on the servo branch, one 470uF near the amplifier, 100uF at the controller and 100nF locally. Use short adequately rated power wiring and strain relief. Do not power servos through the ESP32 regulator or signal headers. Do not connect external 5V and USB programming power simultaneously without documented isolation. The camera programming adapter stays outside the enclosure.

Power allocation with the planned hands: main/radio 0.5A, camera 0.5A, three servos 0.8A each transient, audio 0.7A, LCD/other 0.15A = 4.25A. These are allowances, not measured stall currents. Check voltage droop, stall behavior and temperature on the real assembly; a stalled servo must not be driven indefinitely. There is no main battery, lithium charger or battery-management board in this revision. The RTC coin cell preserves time only and cannot run the robot or sound an alarm without USB power.

## Audio and processing

A2DP phone audio, alarm samples and computer speech share a single output owner. Keep clock rates coherent on the shared I2S pins; resample voice on the Mac, pause/duck A2DP for voice and alarms, then restore it. Firmware still needs memory/CPU/radio stress tests on original ESP32. Camera separation reduces this workload but does not prove coexistence. The complete LLM runs on the Mac or a cloud provider, not on the ESP32.

The RTC battery keeps time while desk power is off. Alarms do not sound without main power. Alarm scheduling, saved settings and touch reactions must run on the physical main controller even when the Mac is asleep; Webots currently simulates that behavior.

## Reserved volumes and enclosure

The current round-display simulation reserves assembly envelopes in dizzy/design.py. This includes larger-than-bare-board volumes for headers and adjustment. The generic LCD outline has not been measured: the simulation uses a provisional 40×46 mm board bound inside a 46×52 mm pocket. This is not a verified TECH2512 manufacturer drawing. The round visible diameter uses the nominal 1.28-inch class 32.4 mm size. Measure the actual part before fixing mounting posts or ordering prints.

The ESP32-CAM board sits behind the display. A compatible 75mm-flex OV2640 assembly places the lens at the upper front port. Confirm its connector pinout and optical view; do not substitute a random 24-pin camera. Preserve loose cable bends and prevent neck cables being pinched at ±45°. The head uses an open neck passage and a separate servo support/bearing; a servo shaft alone is not the enclosure's structural bearing.

The seated revision places the talk switch under the chest capsule and volume switches under the helmet ear caps. Crown inlays cover the two insulated copper electrodes. Speaker and microphone need separate acoustic openings; power enters at the rear. Clock battery, programming access and screws must remain serviceable. Webots and the electronics lab demonstrate both shoulder axes; the physical linkage, servo mounts and cable clearances still require a prototype. See HANDS_PLAN.md for limits and actions.

Physical tests still required: PCB dimensions/connector access, wire routes, cell holder clearance, touch through shell, real servo torque/stall, audio feedback/noise and sound quality, Wi-Fi/Bluetooth load, heat, assembly tolerances and stability on the desk.

## Seated revision

The former stand electronics are now in the hips. The recording switch is under a guided chest capsule; volume switches are in the helmet ear caps and need additional conductors/slack through the neck. The broad crown pad retains two copper electrodes. Servo assemblies and the driver retain their selected electrical connections. See SEATED_COMPANION_DESIGN.md for updated geometry and the inspection view. Internal boxes are allowances, not finished mounts. Provide acoustic paths from the hip-mounted speaker/microphone to the central ports and keep flexible leads clear of all three joints. The simulated camera port is open; the physical shutter mechanism remains to be designed.

## Electronics simulation

See [electronics lab](../electronics/README.md) for the runnable Wokwi bring-up sketch, exact connection map and separate ngspice power tests. GPIO assignments are checked against pinmap.json. Camera/audio symbols are wiring-only; this lab does not replace the Mac/Webots voice and pet services.

## Power sensitivity finding — 19 November 2026

The additional ngspice scenarios expose limited margin in the assumed 5V network: 4.773V at the servo rail in the baseline, 4.603V with twice the cable-path resistance, and 4.095V with the higher servo-load allowance. These are assumed-load calculations, not component measurements. The physical power design remains unqualified; a reported 5V/5A contract is not a loaded-voltage measurement. See [the test report](../electronics/reports/SIMULATION_TESTS_2026-11-19.md) before finalizing wiring or physical release.
