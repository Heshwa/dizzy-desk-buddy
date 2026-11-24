"""Shared renderer and choreography compiled from the same files as the firmware."""
import ctypes as c
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
lib = c.CDLL(os.getenv('DIZZY_V2_NATIVE',str(ROOT / '.work/dizzy-native.so')))


class Shape(c.Structure):
    _fields_ = [(field, c.c_int16) for field in ('kind', 'x', 'y', 'a', 'b', 'radius')] + [('color', c.c_uint32)]


lib.dizzy_face.argtypes = [c.c_int, c.c_int, c.POINTER(Shape), c.c_int]
lib.dizzy_face.restype = c.c_int
for api in (lib.dizzy_face_name, lib.dizzy_face_style):
    api.argtypes = [c.c_int]
    api.restype = c.c_char_p
lib.dizzy_pose.argtypes = [c.c_int, c.c_double, c.c_double, c.POINTER(c.c_float)]
lib.dizzy_pose.restype = None
CATALOG = [{'id': i, 'name': lib.dizzy_face_name(i).decode(), 'style': lib.dizzy_face_style(i).decode()} for i in range(30)]
MOTION = {'rest': 0, 'wave': 1, 'sway': 2, 'heel': 3, 'bounce': 4, 'shuffle': 5}


def frame(face, ms):
    shapes = (Shape * 64)()
    count = lib.dizzy_face(face, ms, shapes, len(shapes))
    return [[s.kind, s.x, s.y, s.a, s.b, s.radius, s.color] for s in shapes[:count]]


def pose(name, elapsed, bpm=100):
    angles = (c.c_float * 8)()
    lib.dizzy_pose(MOTION[name], elapsed, bpm, angles)
    return list(angles)
