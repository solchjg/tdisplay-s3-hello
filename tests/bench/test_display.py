"""Bench tier: the built-in display, confirmed by the operator (FSD §6, FR-7.1).

The serial log only says what the firmware meant to draw (FSD R-1), so every
display claim here is an answer the operator gives on the Pi display.
"""

import time

import pytest

from conftest import hello_lines

HOLD = "Hold the T-Display-S3 in landscape with its USB-C connector on your RIGHT."


@pytest.fixture(scope="module")
def showing(bench, dut, flashed):
    """A fresh boot in SHOWING; its capture is returned."""
    boot = bench.serial_reset(dut).get("output") or []
    if not any(msg.startswith("shown ") for _, _, msg in hello_lines(boot)):
        pytest.fail("display not up after reset: no `hello: shown`")
    return boot


# TC-LOG-04 · FR-7.1
def test_shown_logged_once_per_boot(showing):
    shown = [m for _, _, m in hello_lines(showing) if m == 'shown line1="Hello, world!"']
    assert len(shown) == 1, f"`hello: shown` {len(shown)} times in one boot"


# TC-LCD-05 · C-6.1 – C-6.5 (wire)
def test_operator_sees_both_lines_legible(bench, showing):
    assert bench.human_interaction(
        f"TC-LCD-05. {HOLD} Press DONE only if BOTH text lines are clearly legible: "
        "no blank, noisy, shifted or garbled areas.", timeout=300)


# TC-LCD-07 · FR-6.7
def test_operator_sees_backlight_on(bench, showing):
    assert bench.human_interaction(
        "TC-LCD-07. Press DONE only if the screen's backlight is ON: the text glows and "
        "can be read without room light falling on it, and it does not flicker.",
        timeout=300)


# TC-LCD-06 · FR-6.4 (P-POWERCYCLE: random panel RAM, then a clean screen)
def test_cold_start_leaves_no_stray_pixels(bench, dut, flashed):
    assert bench.human_interaction(
        "TC-LCD-06 (power cycle). Unplug the T-Display-S3's USB-C cable, wait 5 seconds, "
        "plug it back in, then press DONE.", timeout=300), "power cycle not confirmed"
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        slot = bench.get_slot(dut)
        if slot.get("present") and slot.get("state") in ("idle", "running"):
            break
        time.sleep(1)
    else:
        pytest.fail(f"{dut} did not re-enumerate within 30 s of the replug")
    up = bench.serial_monitor(dut, pattern="hello: up=", timeout=15)
    assert up.get("matched"), "no uptime line after the power cycle (positive control)"
    assert bench.human_interaction(
        f"TC-LCD-06. {HOLD} Press DONE only if there are NO stray pixels: no band of noise "
        "along any edge, nothing between or around the two text lines.", timeout=300)
