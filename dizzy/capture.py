"""Capture microphone PCM in an isolated process with a bounded lifetime.

macOS audio drivers can deadlock during PortAudio stream teardown. The parent
ends this process to release the audio device without waiting for that teardown.
"""
import os
from pathlib import Path
import signal
import sys
import time


def main():
    import sounddevice as sd

    destination = Path(sys.argv[1])
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    frames_written = 0

    def finish(signum, frame):
        os._exit(0)

    signal.signal(signal.SIGTERM, finish)
    signal.signal(signal.SIGINT, finish)

    def write_audio(data, frames, timing, status):
        nonlocal frames_written
        remaining = 16000 * 30 - frames_written
        if remaining > 0:
            count = min(frames, remaining)
            os.write(descriptor, memoryview(data)[:count * 2])
            frames_written += count

    stream = sd.RawInputStream(
        samplerate=16000, channels=1, dtype='int16', blocksize=1600,
        callback=write_audio,
    )
    stream.start()
    print('READY', flush=True)
    # Also stop if the service disappears or the parent misses its deadline.
    deadline = time.monotonic() + 31
    parent = os.getppid()
    while time.monotonic() < deadline and os.getppid() == parent:
        time.sleep(.1)
    os._exit(0)


if __name__ == '__main__':
    main()
