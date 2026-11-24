"""Dizzy's component-based enclosure dimensions, in millimetres.

Published display measurements are separate from prototype mounting allowances.
Other component volumes are planning envelopes, pending physical measurement.
"""
DISPLAY_PART = 'Techtonics TECH2512, GC9A01 7P round IPS SPI'
DISPLAY_URL = 'https://techtonics.in/product/1-28-inch-round-display-module-gc9a01-7p-240x240-spi/'
DISPLAY_BUY_URL = DISPLAY_URL
DISPLAY_PIXELS = (240, 240)
DISPLAY_ACTIVE = (32.4, 32.4)  # nominal class size; verify purchased generic module
DISPLAY_BOARD = (40.0, 46.0)  # provisional bound, not a supplier drawing
DISPLAY_CENTER_Z = 0.0
DISPLAY_FRONT_Y = -25.8
HEAD_SIZE = (102.0, 86.0, 92.0)
HEAD_FRONT_Y = -26.0
HEAD_BOTTOM_Z = -42.5
NECK_APERTURE = 14.4
WALL = 2.5
HEAD_CENTER_Z = 157.0
BEZEL_SIZE = (69.0, 69.0)
BEZEL_RADIUS = 34.5
CAMERA_CENTER = (0.0, -25.9, 25.0)
CAMERA_PORT_RADIUS = 3.0
LED_CENTER = (10.0, -25.9, 25.0)
LED_PORT_RADIUS = 1.2
BODY_RADII = (45.0, 41.0, 49.0)
BODY_CENTER_Z = 64.5
ARM_PIVOT_Z = 94.0
ARM_CENTER_Z = 79.0
ARM_RADII = (20.0, 18.0, 44.0)
ARM_CENTER_X = 66.0

HIP_RADII = (60., 58., 30.)
HIP_CENTER_Z = 30.


FOOT_RADII = (23.,30.,30.)
FOOT_CENTER = (28.,-60.,30.)
SHOULDER_CENTER_X = 36.
SHOULDER_RADII = (24., 15.)
SHOULDER_LENGTH = 40.

def head_contains(point, clearance=WALL):
    """Check an assembly point against the inner ellipsoid and cut planes."""
    radii = tuple(extent/2-clearance for extent in HEAD_SIZE)
    return (sum((p/r)**2 for p,r in zip(point,radii)) <= 1
            and point[1] >= HEAD_FRONT_Y+clearance
            and point[2] >= HEAD_BOTTOM_Z+clearance)


def body_front(x, z):
    import math
    c=(z-BODY_CENTER_Z)/BODY_RADII[2]
    scale=(1-.22*c)*math.sqrt(1-c*c)
    return -BODY_RADII[1]*scale*math.sqrt(1-(x/(BODY_RADII[0]*scale))**2)

HEAD_KEEPOUTS = {'display_pocket': {'size': (46.0, 14.0, 52.0), 'center': (0.0, -15.5, 0.0)},
 'camera_board': {'size': (30.0, 16.0, 44.0), 'center': (0.0, 5.0, 10.0)},
 'minus_switch': {'size': (8.0, 8.0, 8.0), 'center': (-41.0, 0.0, 0.0)},
 'plus_switch': {'size': (8.0, 8.0, 8.0), 'center': (41.0, 0.0, 0.0)}}

BODY_KEEPOUTS = {'neck_servo': {'size': (34.0, 14.0, 34.0), 'center': (0.0, -3.0, 84.5)},
 'power_distribution': {'size': (28.0, 7.0, 18.0), 'center': (0.0, -23.0, 79.0)},
 'talk_switch': {'size': (8.0, 8.0, 8.0), 'center': (0.0, -18.0, 94.0)}}

BASE_KEEPOUTS = {'esp32_board': {'size': (58.0, 30.0, 12.0), 'center': (0.0, 13.0, 43.0)},
 'pca9685_driver': {'size': (64.0, 26.0, 14.0), 'center': (0.0, -16.0, 40.0)},
 'clock_board_and_cell': {'size': (42.0, 26.0, 18.0), 'center': (0.0, 10.0, 23.0)},
 'amplifier': {'size': (22.0, 21.0, 10.0), 'center': (-34.0, -8.0, 26.0)},
 'microphone_board': {'size': (18.0, 15.0, 7.0), 'center': (31.0, -8.0, 25.0)},
 'speaker': {'size': (36.0, 36.0, 13.0), 'center': (0.0, -23.0, 26.0)},
 'servo_capacitor': {'size': (10.0, 20.0, 14.0), 'center': (-35.0, 18.0, 27.0)},
 'audio_capacitor': {'size': (10.0, 10.0, 14.0), 'center': (32.0, 17.0, 27.0)},
 'usb_c_pd_board': {'size': (28.0, 26.0, 14.0), 'center': (0.0, 37.0, 28.0)}}

SHOULDER_KEEPOUTS = {'left_shoulder_servo': {'size': (34.0, 34.0, 14.0), 'center': (-36.0, 0.0, 94.0)},
 'right_shoulder_servo': {'size': (34.0, 34.0, 14.0), 'center': (36.0, 0.0, 94.0)}}
