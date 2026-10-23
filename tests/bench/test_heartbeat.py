"""Target tier: the 1 s uptime refresh and its log lines (FSD FR-5.4, FR-5.5, FR-7.3, FR-7.5).

One capture serves all four tests: a pattern match pins the bench wall clock to
a first `up=` line, a 62 s read collects ≥ 61 lines, and a second pattern
match pins the wall clock at the end.
"""

import re
import time

import pytest

from conftest import LOG_LINE, hello_lines, up_values


@pytest.fixture(scope="module")
def capture(bench, dut, flashed):
    first = bench.serial_monitor(dut, pattern="hello: up=", timeout=5)
    w0 = time.monotonic()
    body = bench.serial_monitor(dut, timeout=62).get("output") or []
    last = bench.serial_monitor(dut, pattern="hello: up=", timeout=5)
    w1 = time.monotonic()
    if not (first.get("matched") and last.get("matched")):
        pytest.fail("no `hello: up=` line to pin the wall clock to")
    n0 = int(re.search(r"up=(\d+)", first["line"]).group(1))
    n1 = int(re.search(r"up=(\d+)", last["line"]).group(1))
    return {"body": body, "n0": n0, "n1": n1, "wall": w1 - w0}


# TC-HELLO-01 · FR-5.4
def test_refresh_period(capture):
    ups = up_values(capture["body"])
    assert len(ups) >= 61, f"only {len(ups)} up= lines in 62 s"
    gaps = [t1 - t0 for (t0, _), (t1, _) in zip(ups, ups[1:])]
    bad = [g for g in gaps if not 900 <= g <= 1100]
    assert not bad, f"gaps outside 900-1100 ms: {bad}"
    refreshes, wall = capture["n1"] - capture["n0"], capture["wall"]
    assert abs(refreshes - wall) <= 1, f"{refreshes} refreshes in {wall:.1f} s of bench wall clock"


# TC-HELLO-02 · FR-5.5
def test_uptime_steps_by_one_and_tracks_the_clock(capture):
    ups = up_values(capture["body"])
    assert ups, "no up= lines"
    for (_, n0), (_, n1) in zip(ups, ups[1:]):
        assert n1 == n0 + 1, f"N {n0} -> {n1}"
    off = [(t, n) for t, n in ups if abs(n - t // 1000) > 1]
    assert not off, f"N more than 1 from the log clock: {off[:3]}"


# TC-LOG-03 · FR-7.3 (one line per refresh; the drawn-value match is Phase 2)
def test_one_up_line_per_refresh(capture):
    ups = up_values(capture["body"])
    assert len({n for _, n in ups}) == len(ups), "an N was logged twice"
    for _, _, msg in hello_lines(capture["body"]):
        if msg.startswith("up"):
            assert re.fullmatch(r"up=\d+", msg), f"extra text on an up line: {msg!r}"


# TC-LOG-02 · FR-7.5
def test_every_hello_line_has_the_timestamp_prefix(capture):
    raw = [ln.strip() for ln in capture["body"] if " hello: " in ln or ln.startswith("hello:")]
    assert raw, "no hello: lines captured"
    bad = [ln for ln in raw if not LOG_LINE.match(ln)]
    assert not bad, f"lines without the ESP-IDF timestamp prefix: {bad[:3]}"
