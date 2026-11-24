#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .work/wokwi-sketch hardware/wokwi/build
python3 hardware/build_wokwi.py
cp hardware/wokwi/sketch.ino .work/wokwi-sketch/wokwi-sketch.ino
arduino-cli compile --fqbn esp32:esp32:esp32s3 --build-path "$PWD/.work/wokwi-build" .work/wokwi-sketch
cp .work/wokwi-build/wokwi-sketch.ino.merged.bin hardware/wokwi/build/dizzy-v2-wokwi.bin
cp .work/wokwi-build/wokwi-sketch.ino.elf hardware/wokwi/build/dizzy-v2-wokwi.elf
for chip in body pca9685 ds3231; do
   "${WOKWI_CLI:-wokwi-cli}" chip compile "hardware/wokwi/$chip.chip.c" -o "hardware/wokwi/$chip.chip.wasm"
done
