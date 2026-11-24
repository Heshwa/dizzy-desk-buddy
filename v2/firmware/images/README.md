# Built firmware images

The default merged images target the Waveshare **ESP32-S3-Touch-AMOLED-1.75 SKU 31261** head and the Classic ESP32-WROOM-32 audio helper, respectively. These were built from the V2 source with ESP-IDF 5.5.5.

- Both merged images use flash offset `0x0`. Verify the target and back up existing firmware before flashing.
- The head image is built with no Wi-Fi password or Mac token, and motor output is disabled. Configure and build the head firmware to enable the Mac voice bridge.
- Complete [the hardware bring-up](../../hardware/ASSEMBLY.md) before enabling motion or using the rechargeable pack.
