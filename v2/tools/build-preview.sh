#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p .work
if [ ! -f .work/lvgl/CMakeLists.txt ]; then
  git clone --depth 1 --branch v9.3.0 https://github.com/lvgl/lvgl.git .work/lvgl
fi
cmake -S preview -B .work/preview -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build .work/preview
