#!/bin/sh
set -eu
cd "$(dirname "$0")"
python3 - <<'PY'
import socket,subprocess,webbrowser
with socket.socket() as s:
    running=s.connect_ex(('127.0.0.1',8766))==0
if not running:
    subprocess.Popen(['python3','-m','http.server','8766','--bind','127.0.0.1','--directory','electronics'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
webbrowser.open('http://127.0.0.1:8766')
PY
