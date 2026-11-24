"""Builds and runs the host test for v2/firmware/head/main/safety.hpp.

It exercises the firmware's safety decisions (fault clear, floor arm, tilt latch, motion and servo
gates) on a host compiler. It does not build the ESP-IDF firmware or touch hardware.
"""
import shutil
import subprocess
from pathlib import Path

import pytest

HEAD = Path(__file__).resolve().parents[1] / 'v2/firmware/head'


def test_safety_logic_host_checks(tmp_path):
    compiler = shutil.which('g++') or shutil.which('clang++')
    if not compiler:
        pytest.skip('no C++ compiler on this machine')
    exe = tmp_path / 'safety_test'
    build = subprocess.run([compiler, '-std=c++17', '-Wall', '-Wextra', '-Werror', f'-I{HEAD / "main"}',
                            str(HEAD / 'test/safety_test.cpp'), '-o', str(exe)], capture_output=True, text=True)
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(exe)], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
