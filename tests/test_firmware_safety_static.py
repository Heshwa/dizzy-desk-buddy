"""Static guards for the V2 head firmware safety rules.

These read the C++ source as text. They do not compile or run the firmware, so they only
catch accidental removal of the checks. Real validation needs the ESP-IDF build and
hardware bench tests.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / 'v2/firmware/head/main/main.cpp').read_text()
KCONFIG = (ROOT / 'v2/firmware/head/main/Kconfig.projbuild').read_text()


SAFETY = (ROOT / 'v2/firmware/head/main/safety.hpp').read_text()


def test_fault_clear_requires_fresh_upright_imu_read():
    start = SAFETY.index('bool can_clear_fault(')
    body = SAFETY[start:SAFETY.index('\n}\n', start)]
    assert 'read_imu(tilt)' in body
    assert 'tilt <= kArmMaxTiltDegrees' in body
    assert 'stop_switch_pressed' in body and 'battery_ok(battery_volts)' in body
    assert 'kArmMaxTiltDegrees = 12.0f' in SAFETY


def test_firmware_main_uses_the_shared_safety_functions():
    for name in ('can_clear_fault', 'can_floor_arm', 'should_latch_stop', 'motion_allowed', 'servo_power_allowed'):
        assert f'dizzy_safety::{name}(' in MAIN


def test_arm_key_clears_fault_only_through_the_guarded_helper():
    assigns = [m.start() for m in re.finditer(r'motor_fault\s*=\s*false', MAIN)]
    helper = MAIN.index('bool clear_fault_if_safe(')
    helper_end = MAIN.index('\n}\n', helper)
    arm = MAIN.index('bool local_arm(')
    arm_end = MAIN.index('\n}\n', arm)
    for pos in assigns:
        assert helper <= pos <= helper_end or arm <= pos <= arm_end, 'unguarded motor_fault clear'


def test_motor_outputs_and_floor_mode_default_off():
    for symbol in ('DIZZY_ALLOW_MOTORS', 'DIZZY_ALLOW_FLOOR'):
        block = re.search(rf'config {symbol}\n(.*?)(?=\nconfig |\nendmenu)', KCONFIG, re.S).group(1)
        assert 'default n' in block
