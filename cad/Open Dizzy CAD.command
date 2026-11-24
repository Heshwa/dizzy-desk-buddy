#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
open -a FreeCAD "$PWD/Review.FCMacro"
