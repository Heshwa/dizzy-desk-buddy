"""Launch the project processes together and stop only processes we start."""
import argparse
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dizzy.server import load_env


def listening(port):
    with socket.socket() as connection:
        return connection.connect_ex(('127.0.0.1', port)) == 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    os.chdir(ROOT)
    load_env()
    (ROOT / 'runtime').mkdir(exist_ok=True)
    webots = os.getenv('WEBOTS_EXECUTABLE', '/Applications/Webots.app/Contents/MacOS/webots')
    broker = shutil.which('mosquitto') or '/opt/homebrew/sbin/mosquitto'
    if not Path(webots).exists() or not Path(broker).exists():
        sys.exit('Run scripts/setup.sh and install Webots before launching.')
    if listening(8765):
        sys.exit('Dizzy is already running. Open http://127.0.0.1:8765 or stop the previous launch first.')
    processes = []
    logs = []
    def start(command, name):
        log = open(ROOT / 'runtime' / f'{name}.log', 'a')
        logs.append(log)
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        processes.append(process)
        return process
    def stop(signum=None, frame=None):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    try:
        host = os.getenv('DIZZY_MQTT_HOST', '127.0.0.1')
        port = int(os.getenv('DIZZY_MQTT_PORT', '18884'))
        if host == '127.0.0.1' and port == 18884 and not listening(port):
            start([broker, '-c', str(ROOT / 'scripts/mosquitto.conf')], 'mqtt')
        start([sys.executable, '-m', 'dizzy.server'], 'service')
        for _ in range(50):
            if listening(8765):
                break
            time.sleep(.1)
        if not listening(8765):
            raise RuntimeError('The control service failed. Read runtime/service.log.')
        simulation = start([webots, '--mode=realtime', '--stdout', '--stderr', str(ROOT / 'worlds/dizzy.wbt')], 'webots')
        if not args.no_browser:
            webbrowser.open('http://127.0.0.1:8765')
        print('Dizzy controls at http://127.0.0.1:8765', flush=True)
        print('Press Ctrl+C here to stop this session.', flush=True)
        simulation.wait()
    except KeyboardInterrupt:
        pass
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        for log in logs:
            log.close()


if __name__ == '__main__':
    main()
