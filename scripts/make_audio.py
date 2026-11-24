"""Generate small original demo loops and pet sounds."""
import math
from pathlib import Path
import struct
import wave

root = Path(__file__).resolve().parents[1] / 'assets'
root.mkdir(exist_ok=True)
rate = 22050
for name, notes, duration in [
    ('music-0', [261.63, 329.63, 392, 329.63, 293.66, 349.23, 440, 349.23], 4),
    ('music-1', [220, 277.18, 329.63, 440, 329.63, 277.18], 4),
    ('music-2', [196, 246.94, 293.66, 246.94], 4),
    ('chirp', [880, 1174.66], 0.22),
    ('alarm', [660, 0, 880, 0], 1.2),
]:
    data = bytearray()
    for i in range(int(rate * duration)):
        t = i / rate
        step = duration / len(notes)
        note = notes[min(int(t / step), len(notes) - 1)]
        phase = (t % step) / step
        envelope = min(1, phase * 20) * (1 - phase) ** 1.5
        value = int(8500 * envelope * math.sin(2 * math.pi * note * t)) if note else 0
        data.extend(struct.pack('<h', value))
    with wave.open(str(root / f'{name}.wav'), 'wb') as out:
        out.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
        out.writeframes(data)
