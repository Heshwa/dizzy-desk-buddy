#!/bin/bash
# ESP-IDF creates linker dependencies that fail with spaces in resolved paths.
set -eo pipefail
cd "$(dirname "$0")/../.."
project="$PWD/v2"
stage="${DIZZY_BUILD_ROOT:-$HOME/.cache/dizzy-v2-build}"
sdk="${DIZZY_IDF_ROOT:-$stage/esp-idf-v5.5.5}"
case "$stage:$sdk" in *' '*) echo "Set DIZZY_BUILD_ROOT and DIZZY_IDF_ROOT to paths without spaces." >&2; exit 2;; esac
mkdir -p "$stage"
if [ ! -f "$sdk/export.sh" ]; then
  git clone --depth 1 --branch v5.5.5 --recursive --shallow-submodules https://github.com/espressif/esp-idf.git "$sdk"
  "$sdk/install.sh" esp32,esp32s3
fi
source "$sdk/export.sh" >/dev/null
target="${1:-head}"
shift || true
case "$target" in
  head)
    mkdir -p "$stage/project/.work" "$stage/project/shared" "$stage/project/firmware/head"
    if [ ! -f "$stage/project/.work/bmi270/bmi270.c" ]; then
       git clone --depth 1 --branch v2.113.0 https://github.com/boschsensortec/BMI270_SensorAPI.git "$stage/project/.work/bmi270"
    fi
    rsync -a "$project/shared/" "$stage/project/shared/"
    rsync -a --exclude sdkconfig --exclude build --exclude managed_components "$project/firmware/head/" "$stage/project/firmware/head/"
    app=esp32s3
    ;;
  audio)
    mkdir -p "$stage/project/firmware/audio"
    rsync -a --exclude sdkconfig --exclude build "$project/firmware/audio/" "$stage/project/firmware/audio/"
    app=esp32
    ;;
  *) echo "Select head or audio." >&2; exit 2;;
esac
if [ "$#" -eq 0 ]; then
    set -- build
fi
idf.py -C "$stage/project/firmware/$target" -DIDF_TARGET="$app" "$@"
