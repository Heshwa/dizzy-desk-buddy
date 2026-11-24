#!/bin/sh
set -eu
cd "$(dirname "$0")/../.."
v2/tools/build-shared.sh
mkdir -p v2/.work
if ! nc -z 127.0.0.1 "${DIZZY_V2_MQTT_PORT:-18886}"; then
  printf 'listener %s 127.0.0.1\nallow_anonymous true\npersistence false\n' "${DIZZY_V2_MQTT_PORT:-18886}" > v2/.work/mosquitto.conf
  mosquitto -c v2/.work/mosquitto.conf > v2/.work/mosquitto.log 2>&1 &
  broker=$!
  trap 'kill "$broker" 2>/dev/null || true' EXIT
fi
.venv/bin/python -m v2.app.server "$@"
