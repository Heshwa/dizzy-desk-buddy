#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
./tools/build-shared.sh
world="$PWD/webots/worlds/dizzy_v2.wbt"
if [ "${1:-}" = --cad ]; then world="$PWD/webots/worlds/dizzy_v2_cad.wbt"; fi
exec "${DIZZY_WEBOTS:-/Applications/Webots.app/Contents/MacOS/webots}" "$world"
