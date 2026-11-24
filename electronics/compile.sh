#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p electronics/toolchain/firmware electronics/reports
cp electronics/wokwi/sketch.ino electronics/toolchain/firmware/firmware.ino
cp electronics/wokwi/pins.h electronics/wokwi/face_assets.h electronics/wokwi/face_renderer.h electronics/toolchain/firmware/
arduino-cli compile --fqbn esp32:esp32:esp32 electronics/toolchain/firmware > electronics/reports/firmware-build.log 2>&1
cat electronics/reports/firmware-build.log
