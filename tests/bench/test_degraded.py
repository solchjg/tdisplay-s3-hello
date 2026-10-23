"""Target tier, Wave 3 (negative): the degraded path on the fault-injection build.

FSD FR-5.6 – FR-5.10, FR-7.2, FR-7.4; the stimulus is the test build of
tests/target/lcd_fault/ (seam-lcd-fault-injection), variant `init` (lcd_start
fails with ESP_ERR_TIMEOUT) or `write5` (the 5th write after T1 fails with
ESP_ERR_INVALID_STATE).

The reset capture lasts 5 s and the write fault lands later, so each run reads
the bench's /api/serial/output ring buffer, which keeps collecting after the
reset. P-FAULT: the shipped build is flashed back when the module ends.
"""

import os
import re
import time

import pytest

from conftest import CHIP, LOG_LINE, flash_coldflash, hello_lines, this_boot, up_values

AFTER_FAILURE_S = 62          # FR-5.10 watches 60 s after the failure line
BOOT_MARKS = ("ESP-ROM:", "rst:", "Guru Meditation", "abort()", "Backtrace:", "Rebooting...")


def _fault_dir(variant):
    d = os.environ.get(f"FAULT_DIR_{variant.upper()}")
    if not d or not os.path.isfile(os.path.join(d, "flash_args")):
        pytest.skip(f"FAULT_DIR_{variant.upper()} not set to the lcdfault-{variant} artefact")
    return d


def _ring_since(bench, slot, since):
    buf = bench.serial_output(slot, lines=2000, since=since)
    return [e.get("text", "") for e in buf.get("lines", [])]


@pytest.fixture(scope="module")
def restore_shipped(bench, dut, firmware_dir):
    """P-FAULT cleanup: the shipped build goes back, and is seen running."""
    yield
    res = flash_coldflash(bench.base_url, dut, CHIP, firmware_dir)
    boot = this_boot(bench.serial_reset(dut).get("output") or [])
    assert res.get("ok") and any("hello: shown" in ln for ln in boot), \
        "shipped build not restored after the fault runs"


_runs = {}


@pytest.fixture(scope="module", params=["init", "write5"])
def run(request, bench, dut, restore_shipped):
    """Flash a fault variant, reset, and collect the boot plus the following minute."""
    variant = request.param
    if variant not in _runs:
        d = _fault_dir(variant)
        res = flash_coldflash(bench.base_url, dut, CHIP, d)
        assert res.get("ok"), res.get("error") or res.get("output")
        last = bench.serial_output(dut, lines=1).get("lines") or [{"ts": 0}]
        bench.serial_reset(dut)
        # The fault lands within ~6 s of reset; then FR-5.10's minute.
        time.sleep(6 + AFTER_FAILURE_S)
        lines = this_boot(_ring_since(bench, dut, last[-1]["ts"]))
        _runs[variant] = {"variant": variant, "lines": lines}
    return _runs[variant]


def only(variant):
    return lambda run: run["variant"] == variant or pytest.skip(f"not the {variant} variant")


def failure(run):
    """Index of, and the parsed log line for, the variant's failure line."""
    want = "lcd init failed: " if run["variant"] == "init" else "lcd write failed: "
    hits = [(i, LOG_LINE.match(ln.strip())) for i, ln in enumerate(run["lines"])
            if f"hello: {want}" in ln]
    return want, hits


def _after(run, idx):
    return run["lines"][idx + 1:]


# TC-HELLO-10 · FR-5.6
def test_init_failure_enters_degraded_within_3s(run):
    only("init")(run)
    _, hits = failure(run)
    assert len(hits) == 1 and hits[0][1], "no `hello: lcd init failed:` line"
    assert int(hits[0][1].group(2)) <= 3000, f"at {hits[0][1].group(2)} ms"
    assert not any("hello: shown" in ln for ln in run["lines"]), "`hello: shown` despite the failure"


# TC-LOG-10 · FR-7.2
def test_init_failure_line_is_error_level_with_the_error_name(run):
    only("init")(run)
    lines = [(lvl, msg) for lvl, _, msg in hello_lines(run["lines"]) if msg.startswith("lcd init failed")]
    assert lines == [("E", "lcd init failed: ESP_ERR_TIMEOUT")], lines


# TC-HELLO-12 · FR-5.7
def test_degraded_keeps_the_refresh_on_serial(run):
    only("init")(run)
    _, hits = failure(run)
    ups = up_values(_after(run, hits[0][0]))[:11]
    assert len(ups) == 11, f"only {len(ups)} up= lines after the failure"
    for (t0, n0), (t1, n1) in zip(ups, ups[1:]):
        assert n1 == n0 + 1, f"N {n0} -> {n1}"
        assert 900 <= t1 - t0 <= 1100, f"gap {t1 - t0} ms"


# TC-HELLO-16 · FR-5.9
def test_degraded_makes_no_display_call(run):
    only("init")(run)
    _, hits = failure(run)
    idx, fail_ms = hits[0][0], int(hits[0][1].group(2))
    before = [ln for ln in run["lines"][:idx] if "lcdfi: call" in ln]
    after = [ln for ln in _after(run, idx) if "lcdfi: call" in ln]
    assert len(before) == 1 and "call start" in before[0], f"before the failure: {before}"
    assert not after, f"display calls after the failure (a retry?): {after[:3]}"
    window = [n for t, n in up_values(_after(run, idx)) if fail_ms < t <= fail_ms + 30000]
    assert abs(len(window) - 30) <= 1, f"{len(window)} up= lines in the 30 s window"


# TC-HELLO-14 · FR-5.8
def test_write_failure_enters_degraded_on_the_same_tick(run):
    only("write5")(run)
    assert any("hello: shown" in ln for ln in run["lines"]), "never reached SHOWING"
    _, hits = failure(run)
    assert len(hits) == 1, f"`hello: lcd write failed` {len(hits)} times"
    idx = hits[0][0]
    prev = [m for _, _, m in hello_lines(run["lines"][:idx])]
    assert prev and re.fullmatch(r"up=\d+", prev[-1]), f"line before the failure: {prev[-1:]}"
    n_fail = int(prev[-1][3:])
    nxt = up_values(_after(run, idx))
    assert nxt and nxt[0][1] == n_fail + 1, "refreshes did not continue at N+1"


# TC-LOG-11 · FR-7.4
def test_write_failure_line_is_error_level_with_the_error_name(run):
    only("write5")(run)
    lines = [(lvl, msg) for lvl, _, msg in hello_lines(run["lines"]) if msg.startswith("lcd write failed")]
    assert lines == [("E", "lcd write failed: ESP_ERR_INVALID_STATE")], lines


# TC-HELLO-17 · FR-5.10 (both variants)
def test_no_reset_for_a_minute_after_the_failure(run):
    _, hits = failure(run)
    assert hits, "no failure line"
    idx, fail_ms = hits[0][0], int(hits[0][1].group(2))
    rest = _after(run, idx)
    marks = [ln for ln in rest if any(m in ln for m in BOOT_MARKS)]
    assert not marks, f"reset or panic after the failure: {marks[:3]}"
    ups = [(t, n) for t, n in up_values(rest) if t <= fail_ms + 60000]
    assert abs(len(ups) - 60) <= 1, f"{len(ups)} up= lines in the 60 s after the failure"
    assert all(b[1] == a[1] + 1 for a, b in zip(ups, ups[1:])), "N not strictly +1"
