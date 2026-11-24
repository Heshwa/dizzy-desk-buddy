"""Render individual part cards and a looping assembly sequence from the CAD meshes."""
from concurrent.futures import ThreadPoolExecutor
import io
import json
import math
from pathlib import Path
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont

CAD = Path(__file__).resolve().parents[1]
REPORTS = CAD / 'reports'
data = json.loads((CAD / 'preview-data.json').read_text())
parts = data['parts']
OUT = REPORTS / 'parts'
OUT.mkdir(exist_ok=True)
main_font = ImageFont.load_default(size=27)
small_font = ImageFont.load_default(size=16)


def observe(azimuth, elevation):
    azimuth, elevation = map(math.radians, (azimuth, elevation))
    return (math.cos(azimuth) * math.cos(elevation),
            math.sin(azimuth) * math.cos(elevation), math.sin(elevation))


def render(executable, entries, size, pixels_per_mm, eye, center):
    header = ' '.join(map(str, (*size, pixels_per_mm, *eye, *center, len(entries))))
    commands = [
        ' '.join(map(str, (*part['color'], *offset))) + '\n' + str(CAD / part['path'])
        for part, offset in entries
    ]
    raster = subprocess.run([executable], input=('\n'.join([header, *commands]) + '\n').encode(),
                            capture_output=True, check=True)
    return Image.open(io.BytesIO(raster.stdout)).convert('RGB')


def thumb(executable, part):
    diameter = max(math.hypot(*part['size_mm']), .1)
    camera = observe(48 if part['id'] == 'Helmet_front' else -57, 28)
    frame = render(executable, [(part, (0, 0, 0))], (360, 280), 228 / diameter,
                   camera, part['center'])
    frame.save(OUT / (part['id'] + '.png'), optimize=True)


# Move part groups into place in order. Within each group the most visible
# covers move away from their actual service sides, preserving that order on return.
def group_offset(part):
    name = part['id']
    x, y, z = part['center']
    direction = -1 if x < 0 else 1
    if name == 'Helmet_rear':
        return 4, (0, 54, 9)
    if name == 'Helmet_front':
        return 4, (0, -52, 12)
    if name.startswith(('Crown_', 'Volume_', 'Face_', 'Camera_shutter')) or part.get('visible_exterior'):
        if name.startswith('Crown_'):
            return 5, (direction * 12, 0, 54)
        if name.startswith('Volume_'):
            return 5, (direction * 49, 0, 14)
        return 5, (0, -81, 11)
    if part['region'] == 'head':
        return 3, (x * .35, 18 if y >= 0 else -22, 36)
    if name.startswith(('Forearm_', 'Palm_', 'Cuff_', 'Horn_', 'Shoulder_')):
        drift = 11 if name.startswith('Forearm_') else 0
        return 2, (direction * (52 + drift), -8, 8 if z > 78 else -16)
    if name.startswith(('Hip_', 'Bottom_cover', 'Foot_', 'Sole_')):
        if name == 'Bottom_cover':
            return 0, (0, 0, -38)
        return 0, (direction * 18, -40 if y < 0 else 42, -18)
    if name.startswith(('Torso_', 'Waist_', 'Chest_', 'Record_')):
        return 1, (0, -40 if y < 0 else 42, 10)
    return 0 if z < 57 else 1, (direction * 14, 12 if y > 0 else -12, -8)


stages = [
    'Seat the base and its electronics',
    'Close the torso and seat the joint mount',
    'Fit the shoulders and hands',
    'Place the display, camera and helmet mounts',
    'Close the helmet',
    'Fit the bezel, buttons and crown pads',
]
sequence = [(part, *group_offset(part)) for part in parts if part['region'] != 'coupon']
stage_frames = 9
frame_indices = range(7 + stage_frames * len(stages) + 15)


def animation_frame(executable, index):
    step = (index - 7) / stage_frames
    entries = []
    for part, stage, offset in sequence:
        progress = max(0, min(1, step - stage))
        interpolation = progress * progress * (3 - 2 * progress)
        if part['hardware'] and not part.get('visible_exterior') and progress >= 1:
            # Keep the video readable while showing the provisional internal
            # positions during placement. Hidden envelopes don't become surfaces.
            continue
        entries.append((part, tuple(value * (1 - interpolation) for value in offset)))
    shrink = max(0, min(1, step / 6))
    azimuth = -60 - 16 * shrink
    frame = render(executable, entries, (820, 770), 1.82 + .75 * shrink,
                   observe(azimuth, 15 - 5 * shrink), (0, 0, 113 + 16 * (1 - shrink)))
    draw = ImageDraw.Draw(frame)
    draw.rectangle((0, 0, frame.width, 82), fill='#eaeFEB')
    draw.text((24, 15), 'Dizzy enclosure assembly', font=main_font, fill='#223632')
    label = 'Exploded parts' if step < 0 else 'Assembled prototype' if step >= 6 else stages[int(step)]
    draw.text((25, 54), label, font=small_font, fill='#546c62')
    return frame.quantize(colors=112, method=Image.Quantize.MEDIANCUT)


with tempfile.TemporaryDirectory() as temp:
    executable = str(Path(temp) / 'raster')
    subprocess.run(['clang++', '-O2', '-std=c++17', str(CAD / 'source/raster.cpp'), '-o', executable],
                   check=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda part: thumb(executable, part), parts))
        frames = list(pool.map(lambda index: animation_frame(executable, index), frame_indices))
    durations = [100] * len(frames)
    durations[0] = 300
    durations[-1] = 900
    frames[0].save(REPORTS / 'dizzy-assembly.gif', save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, disposal=2, optimize=False)
    frames[-1].convert('RGB').save(REPORTS / 'assembly-poster.png')
print(f'Rendered {len(parts)} individual images and a {len(frames)}-frame assembly GIF.')
