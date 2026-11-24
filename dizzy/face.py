"""Render the 240x240 GC9A01 with content inside its circular visible area."""
from functools import lru_cache
import math
from PIL import Image, ImageDraw, ImageFont
from .design import DISPLAY_PIXELS

BACKGROUND = (5, 13, 18, 255)
INK = (109, 238, 233, 255)
SAFE_MARGIN = 12
SAFE_RADIUS = 108


@lru_cache(maxsize=4)
def label_font(size=23):
    return ImageFont.load_default(size=size)


def face_label(status):
    if status.get('ringing'):
        return 'WAKE UP'
    if status['expression'] == 'goodnight':
        return 'GOOD NIGHT'
    voice = status.get('voice', 'idle')
    if voice != 'idle':
        return {'listening': 'LISTEN', 'thinking': 'THINKING', 'speaking': 'TALKING'}.get(voice, 'BUSY')
    return status['clock'][11:16]


def render_face(status, timestamp):
    image = Image.new('RGBA', DISPLAY_PIXELS, BACKGROUND)
    draw = ImageDraw.Draw(image)
    expression = status['expression']
    # Reactions drive the face; idle/listening do not run an automatic blink loop.
    blink = expression == 'blink'
    bob = int(math.sin(timestamp * 4 * math.pi) * 3) if expression == 'music' else 0
    for x in (81, 159):
        if blink or expression in ('happy', 'idle', 'sleepy', 'goodnight'):
            if expression in ('happy','idle') and not blink:
                draw.arc((x-28, 68, x+28, 112), 195, 345, fill=INK, width=9)
            else:
                draw.rounded_rectangle((x-23, 92, x+23, 98), radius=3, fill=INK)
        elif expression == 'heart':
            draw.ellipse((x-22, 73, x+1, 98), fill=INK)
            draw.ellipse((x-1, 73, x+22, 98), fill=INK)
            draw.polygon([(x-21, 91), (x+21, 91), (x, 117)], fill=INK)
        else:
            height = 57 if expression in ('alarm','listening') else 46
            draw.rounded_rectangle((x-18, 94-height//2+bob, x+18, 94+height//2+bob), radius=14, fill=INK)
            draw.ellipse((x-6, 78+bob, x+6, 94+bob), fill=BACKGROUND)
    if expression == 'speaking':
        opening = 4 + int((math.sin(timestamp*12)+1)*5)
        draw.ellipse((108, 139-opening, 132, 139+opening), fill=INK)
    elif expression == 'happy':
        draw.arc((103, 119, 137, 143), 10, 170, fill=INK, width=4)
    if status.get('playing'):
        for x, height in ((109,5),(117,9),(125,6)):
            draw.rounded_rectangle((x,143-height,x+4,143),radius=2,fill=INK)
    label = face_label(status)
    font = label_font(34 if ':' in label else 21)
    box = font.getbbox(label)
    width = box[2]-box[0]
    draw.text(((240-width)//2-box[0], 169-box[1]),label,font=font,fill=INK)
    # No mask is used to conceal bad layout: tests check every illuminated pixel.
    return image
