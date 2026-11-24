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
HEAD_SIZE = (112.0, 92.0, 100.0)
HEAD_FRONT_Y = -26.0
HEAD_BOTTOM_Z = -46.5
NECK_APERTURE = 14.4
WALL = 2.5
HEAD_CENTER_Z = 175.0
BEZEL_SIZE = (74.0, 74.0)
BEZEL_RADIUS = 37.0
CAMERA_CENTER = (0.0, -25.9, 25.0)
CAMERA_PORT_RADIUS = 3.0
LED_CENTER = (10.0, -25.9, 25.0)
LED_PORT_RADIUS = 1.2
BODY_RADII = (51.0, 48.0, 56.0)
BODY_CENTER_Z = 72.0
ARM_PIVOT_Z = 75.0
ARM_CENTER_Z = 60.0
ARM_RADII = (14.0, 18.0, 34.0)
ARM_CENTER_X = 79.0

HIP_RADII = (64., 64., 32.)
HIP_CENTER_Z = 32.


# Assembly allowances, not verified production measurements.
HEAD_KEEPOUTS = {'display_pocket': {'size': (46.0, 14.0, 52.0), 'center': (0.0, -15.5, 0.0)},
 'camera_board': {'size': (30.0, 16.0, 44.0), 'center': (0.0, 5.0, 10.0)},
 'minus_switch': {'size': (8.0, 8.0, 8.0), 'center': (-46.0, 0.0, 0.0)},
 'plus_switch': {'size': (8.0, 8.0, 8.0), 'center': (46.0, 0.0, 0.0)}}

BODY_KEEPOUTS = {'esp32_board': {'size': (30.0, 12.0, 58.0), 'center': (0.0, 25.0, 64.0)},
 'neck_servo': {'size': (34.0, 14.0, 34.0), 'center': (0.0, -3.0, 100.0)},
 'left_shoulder_servo_reserved': {'size': (34.0, 34.0, 14.0), 'center': (-23.0, 0.0, 75.0)},
 'right_shoulder_servo_reserved': {'size': (34.0, 34.0, 14.0), 'center': (23.0, 0.0, 75.0)},
 'pca9685_driver': {'size': (64.0, 14.0, 26.0), 'center': (0.0, -14.0, 50.0)},
 'power_distribution': {'size': (28.0, 18.0, 7.0), 'center': (0.0, 5.0, 45.0)},
 'talk_switch': {'size': (8.0, 8.0, 8.0), 'center': (0.0, -33.0, 88.0)}}

BASE_KEEPOUTS = {'clock_board_and_cell': {'size': (42.0, 26.0, 18.0), 'center': (0.0, 13.0, 25.0)},
 'amplifier': {'size': (22.0, 21.0, 10.0), 'center': (-34.0, -8.0, 28.0)},
 'microphone_board': {'size': (18.0, 15.0, 7.0), 'center': (31.0, -8.0, 27.0)},
 'speaker': {'size': (36.0, 36.0, 13.0), 'center': (0.0, -23.0, 29.0)},
 'servo_capacitor': {'size': (10.0, 20.0, 14.0), 'center': (-35.0, 18.0, 29.0)},
 'audio_capacitor': {'size': (10.0, 10.0, 14.0), 'center': (32.0, 17.0, 29.0)},
 'usb_c_pd_board': {'size': (28.0, 26.0, 14.0), 'center': (0.0, 44.5, 32.0)}}

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
