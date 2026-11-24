#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p .work
c++ -std=c++17 -O2 -Wall -Wextra -shared -fPIC shared/face.cpp shared/motion.cpp -o .work/dizzy-native.so
