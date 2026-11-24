#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
export HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_INSTALL_CLEANUP=1
if ! command -v brew >/dev/null; then
  echo 'Install Homebrew from https://brew.sh, then run this setup again.'
  exit 1
fi
brew install mosquitto whisper.cpp
if [ ! -x .venv/bin/python ]; then python3 -m venv .venv; fi
.venv/bin/python -m pip install -r requirements.txt
mkdir -p models runtime reports
if [ ! -s models/ggml-base.en.bin ]; then
  curl --fail --location https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin -o models/ggml-base.en.bin
fi
if [ ! -s models/en_US-lessac-medium.onnx ]; then
  .venv/bin/python -m piper.download_voices --download-dir models en_US-lessac-medium
fi
.venv/bin/python scripts/make_audio.py
.venv/bin/python scripts/build_enclosure.py
.venv/bin/python - <<'PY'
from pathlib import Path
root = Path.cwd()
(root / 'controllers/dizzy/runtime.ini').write_text('[python]\nCOMMAND = ' + str(root / '.venv/bin/python') + '\n')
PY
if [ ! -d /Applications/Webots.app ]; then
  echo 'Install the official Webots R2025a nightly build for macOS 27.'
  echo 'https://github.com/cyberbotics/webots/releases/tag/nightly_17_11_2026'
fi
echo 'Setup complete. Launch with ./scripts/launch.sh'
