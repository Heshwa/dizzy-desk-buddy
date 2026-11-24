#!/bin/sh
set -eu
cd "$(dirname "$0")"
resources="${DIZZY_FREECAD_RESOURCES:-/Applications/FreeCAD.app/Contents/Resources}"
export PYTHONPATH="$resources/lib${PYTHONPATH:+:$PYTHONPATH}"
"$resources/bin/python" build.py
