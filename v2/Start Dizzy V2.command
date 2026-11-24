#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:$PATH"
if [ "$#" -eq 0 ] && curl -fsS http://127.0.0.1:8875/api/catalog >/dev/null 2>&1; then
   open http://127.0.0.1:8875
   exit 0
fi
(
  for attempt in {1..40}; do
    if curl -fsS http://127.0.0.1:8875/api/catalog >/dev/null 2>&1; then
       open http://127.0.0.1:8875
       exit 0
    fi
    sleep .25
  done
) &
exec ./tools/start-demo.sh "$@"
