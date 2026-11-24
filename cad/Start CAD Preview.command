#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
port=8767
if ! /usr/bin/nc -z 127.0.0.1 "$port"; then
  python3 -m http.server "$port" --bind 127.0.0.1 &
  server=$!
  trap 'kill "$server" 2>/dev/null || true' EXIT
fi
open "http://127.0.0.1:$port/preview.html"
if [[ -n "${server:-}" ]]; then
  wait "$server"
fi
