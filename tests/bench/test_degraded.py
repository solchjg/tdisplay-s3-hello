"""Target tier, Wave 3 (negative): the degraded path on the fault-injection build.

FSD FR-5.6 – FR-5.10, FR-7.2, FR-7.4; the stimulus is the test build of
tests/target/lcd_fault/ (seam-lcd-fault-injection), variant `init` (lcd_start
fails with ESP_ERR_TIMEOUT) or `write5` (the 5th write after T1 fails with
ESP_ERR_INVALID_STATE).

Each run resets once through JTAG and reads the following minute of that same
boot from the bench ring buffer (conftest.reset_and_follow). P-FAULT: the
shipped build is flashed back when the module ends.
"""

import os
import re

import pytest

from conftest import (CHIP, LOG_LINE, flash_coldflash, hello_lines, reset_and_follow,
                      save_evidence, this_boot, up_values)

AFTER_FAILURE_S = 62          # FR-5.10 watches 60 s after the failure line
BOOT_MARKS = ("ESP-ROM:", "rst:", "Guru Meditation", "abort()", "Backtrace:", "Rebooting...")


def _fault_dir(variant):
    d = os.environ.get(f"FAULT_DIR_{variant.upper()}")
    if not d or not os.path.isfile(os.path.join(d, "flash_args")):
        pytest.skip(f"FAULT_DIR_{variant.upper()} not set to the lcdfault-{variant} artefact")
    return d


@pytest.fixture(scope="module")
def restore_shipped(bench, dut, firmware_dir):
    """P-FAULT cleanup: the shipped build goes back, and is seen running."""
    yield
    res = flash_coldflash(bench.base_url, dut, CHIP, firmware_dir)
    boot = this_boot(bench.serial_reset(dut).get("output") or [])
    assert res.get("ok") and any("hello: shown" in ln for ln in boot), \
        "shipped build not restored after the fault runs"


_runs = {}


def _run(bench, dut, variant):
    """Flash a fault variant, reset once, and collect that boot's first minute+."""
    if variant not in _runs:
        res = flash_coldflash(bench.base_url, dut, CHIP, _fault_dir(variant))
        assert res.get("ok"), res.get("error") or res.get("output")
        # The fault lands within ~6 s of reset; then FR-5.10's minute.
        lines = reset_and_follow(bench, dut, 6 + AFTER_FAILURE_S)
        save_evidence(f"lcdfault-{variant}-window", lines)   # FSD §5.5 evidence: the full window
        _runs[variant] = {"variant": variant, "lines": lines}
    return _runs[variant]


@pytest.fixture(scope="module")
def run_init(bench, dut, restore_shipped):
    return _run(bench, dut, "init")


@pytest.fixture(scope="module")
def run_write5(bench, dut, restore_shipped):
    return _run(bench, dut, "write5")


def failure(run):
    """Index of, and the parsed log line for, the variant's failure line."""
    want = "lcd init failed: " if run["variant"] == "init" else "lcd write failed: "
    hits = [(i, LOG_LINE.match(ln.strip())) for i, ln in enumerate(run["lines"])
            if f"hello: {want}" in ln]
    return want, hits


def _after(run, idx):
    return run["lines"][idx + 1:]


def assert_no_reset_and_counting(lines, from_ms, to_ms, expect):
    """Prohibited outcomes shared by FR-5.8 – FR-5.10: no boot banner, reset
    reason or panic in `lines`, and the refresh keeps going at N+1 with about
    `expect` lines between from_ms and to_ms."""
    marks = [ln for ln in lines if any(m in ln for m in BOOT_MARKS)]
    assert not marks, f"reset or panic: {marks[:3]}"
    ups = [(t, n) for t, n in up_values(lines) if from_ms < t <= to_ms]
    assert abs(len(ups) - expect) <= 1, f"{len(ups)} up= lines in {(to_ms - from_ms) / 1000:.0f} s"
    assert all(b[1] == a[1] + 1 for a, b in zip(ups, ups[1:])), "N not strictly +1"


# TC-HELLO-10 · FR-5.6
def test_init_failure_enters_degraded_within_3s(run_init):
    run = run_init
    _, hits = failure(run)
    assert len(hits) == 1 and hits[0][1], "no `hello: lcd init failed:` line"
    assert int(hits[0][1].group(2)) <= 3000, f"at {hits[0][1].group(2)} ms"
    assert not any("hello: shown" in ln for ln in run["lines"]), "`hello: shown` despite the failure"


# TC-LOG-10 · FR-7.2
def test_init_failure_line_is_error_level_with_the_error_name(run_init):
    run = run_init
    lines = [(lvl, msg) for lvl, _, msg in hello_lines(run["lines"]) if msg.startswith("lcd init failed")]
    assert lines == [("E", "lcd init failed: ESP_ERR_TIMEOUT")], lines


# TC-HELLO-12 · FR-5.7
def test_degraded_keeps_the_refresh_on_serial(run_init):
    run = run_init
    _, hits = failure(run)
    ups = up_values(_after(run, hits[0][0]))[:11]
    assert len(ups) == 11, f"only {len(ups)} up= lines after the failure"
    for (t0, n0), (t1, n1) in zip(ups, ups[1:]):
        assert n1 == n0 + 1, f"N {n0} -> {n1}"
        assert 900 <= t1 - t0 <= 1100, f"gap {t1 - t0} ms"


# TC-HELLO-16 · FR-5.9
def test_degraded_makes_no_display_call(run_init):
    run = run_init
    _, hits = failure(run)
    idx, fail_ms = hits[0][0], int(hits[0][1].group(2))
    before = [ln for ln in run["lines"][:idx] if "lcdfi: call" in ln]
    after = [ln for ln in _after(run, idx) if "lcdfi: call" in ln]
    assert len(before) == 1 and "call start" in before[0], f"before the failure: {before}"
    assert not after, f"display calls after the failure (a retry?): {after[:3]}"
    assert_no_reset_and_counting(_after(run, idx), fail_ms, fail_ms + 30000, 30)


# TC-HELLO-14 · FR-5.8
def test_write_failure_enters_degraded_on_the_same_tick(run_write5):
    run = run_write5
    assert any("hello: shown" in ln for ln in run["lines"]), "never reached SHOWING"
    _, hits = failure(run)
    assert len(hits) == 1, f"`hello: lcd write failed` {len(hits)} times"
    idx = hits[0][0]
    prev = [m for _, _, m in hello_lines(run["lines"][:idx])]
    assert prev and re.fullmatch(r"up=\d+", prev[-1]), f"line before the failure: {prev[-1:]}"
    n_fail = int(prev[-1][3:])
    nxt = up_values(_after(run, idx))
    assert nxt and nxt[0][1] == n_fail + 1, "refreshes did not continue at N+1"
    fail_ms = int(hits[0][1].group(2))
    # FSD FR-5.8 full form: the 10 s after the failure, no reset, refreshes go on.
    assert_no_reset_and_counting(_after(run, idx), fail_ms, fail_ms + 10000, 10)


# TC-LOG-11 · FR-7.4
def test_write_failure_line_is_error_level_with_the_error_name(run_write5):
    run = run_write5
    lines = [(lvl, msg) for lvl, _, msg in hello_lines(run["lines"]) if msg.startswith("lcd write failed")]
    assert lines == [("E", "lcd write failed: ESP_ERR_INVALID_STATE")], lines


# TC-HELLO-17 · FR-5.10 (both variants)
@pytest.mark.parametrize("variant", ["init", "write5"])
def test_no_reset_for_a_minute_after_the_failure(request, variant):
    run = request.getfixturevalue(f"run_{variant}")
    _, hits = failure(run)
    assert hits, "no failure line"
    idx, fail_ms = hits[0][0], int(hits[0][1].group(2))
    assert_no_reset_and_counting(_after(run, idx), fail_ms, fail_ms + 60000, 60)
