"""JRN-01 — the standard run, one test per step, in order (testing/test-plan.yaml).

Steps 3, 4 and 6 need FSD Phase 2 firmware (the display).
"""

import re

import pytest

from conftest import hello_lines, this_boot, up_values

pytestmark = pytest.mark.journey

MARKER = "Init complete, running event-driven"


@pytest.fixture(scope="module")
def boot(bench, dut, flashed):
    """Boot capture of one USB reset. A monitor cannot span a bench reset
    (test-plan bench-serial-monitor note), so the reset's own capture is read."""
    return this_boot(bench.serial_reset(dut).get("output") or [])


def test_jrn_01_1_flash(flashed):
    assert flashed.get("ok"), flashed.get("error") or flashed.get("output")


def test_jrn_01_2_boot_marker(boot):
    hits = [i for i, ln in enumerate(boot) if MARKER in ln]
    assert len(hits) == 1, f"marker seen {len(hits)} times"
    startup = [i for i, ln in enumerate(boot) if "app_init:" in ln]
    assert startup and hits[0] > max(startup), "marker before the ESP-IDF startup lines"


def test_jrn_01_3_display_up(boot):
    shown = [(ms, msg) for _, ms, msg in hello_lines(boot)
             if msg == 'shown line1="Hello, world!"']
    assert shown, "no `hello: shown` in the boot capture"
    # FSD FR-5.2 (0.1.1): the line's own log timestamp, ms since the chip's reset.
    assert int(shown[0][0]) <= 3000


def test_jrn_01_4_operator_sees_greeting(bench, boot):
    assert any("hello: shown" in ln for ln in boot), "display not up; nothing to show"
    assert bench.human_interaction(
        "JRN-01.4: hold the T-Display-S3 with USB-C on your RIGHT. Press DONE only if "
        "the top line reads exactly 'Hello, world!', upright, white text on black.",
        timeout=300)


def test_jrn_01_5_uptime_ticks(bench, dut, boot):
    ups = up_values(bench.serial_monitor(dut, timeout=12).get("output") or [])
    assert len(ups) >= 10, f"only {len(ups)} up= lines in 12 s"
    ups = ups[:10]
    for (t0, n0), (t1, n1) in zip(ups, ups[1:]):
        assert n1 == n0 + 1, f"N {n0} -> {n1}"
        assert 900 <= t1 - t0 <= 1100, f"gap {t1 - t0} ms at N={n1}"


def test_jrn_01_6_operator_sees_uptime(bench, dut, boot):
    """The operator presses DONE when line 2 shows a target value; the log decides.

    A person cannot compare a counter that changes every second against a
    number to within ±1, so the comparison is the instrument's: at the press,
    the logged N must be the target within ±1. The first up= line after the
    press is one refresh later, hence target .. target + 2.
    """
    assert any("hello: shown" in ln for ln in boot), "display not up; nothing to show"
    m = bench.serial_monitor(dut, pattern="hello: up=", timeout=5)
    target = int(re.search(r"up=(\d+)", m.get("line") or "").group(1)) + 30
    assert bench.human_interaction(
        f"JRN-01.6. Watch the second line count up. Press DONE at the moment it reads "
        f"exactly 'Up: {target} s' (same spelling: 'Up:', the number, a space, 's'). "
        "If it reads anything else, or you miss it, press CANCEL.", timeout=120)
    after = bench.serial_monitor(dut, pattern="hello: up=", timeout=3)
    n = int(re.search(r"up=(\d+)", after.get("line") or "").group(1))
    assert target <= n <= target + 2, f"pressed at {target}, log then at {n}"
