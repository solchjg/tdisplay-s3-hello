"""Bench tier: the board and the air (FSD C-10.3 board row, FR-9.1 air row)."""

import os

from conftest import MAC


# TC-BUILD-05 · C-10.3 (board)
def test_board_flash_is_16mb(bench, dut):
    assert bench.chip_info(dut).get("flash_size") == "16MB"


def _dut_macs():
    """WiFi STA, SoftAP, BT and Ethernet MACs derive from the base MAC (+0 to +3)."""
    base = int(MAC.replace(":", ""), 16)
    return {":".join(f"{(base + i) >> s & 0xFF:02x}" for s in range(40, -8, -8)) for i in range(4)}


# TC-SEC-02 · FR-9.1 (air, BLE half). The WiFi half is TC-SEC-03: the bench
# scan reports no BSSID, so it cannot tell the DUT's AP from any other.
def test_dut_does_not_advertise_on_ble(bench, dut, flashed):
    macs = _dut_macs()
    seen = [d for d in bench.ble_scan(timeout=int(os.environ.get("BLE_SCAN_S", "8")))
            if (d.get("address") or "").lower() in macs]
    assert not seen, f"DUT advertising on BLE: {seen}"


def _default_softap_ssids():
    """SSIDs a default-configured ESP32 SoftAP would advertise: ESP_ + the last
    three bytes of its MAC in upper-case hex (FSD FR-9.1 air, WiFi half)."""
    return {"ESP_" + m.replace(":", "")[-6:].upper() for m in _dut_macs()}


# TC-SEC-03 · FR-9.1 (air, WiFi half; FSD 0.1.2, R-6)
def test_dut_runs_no_default_softap(bench, dut, flashed):
    ssids = _default_softap_ssids()
    nets = bench.scan().get("networks", [])
    assert nets, "WiFi scan saw no networks at all (positive control: the bench radio is listening)"
    seen = [n for n in nets if (n.get("ssid") or "").upper() in ssids]
    assert not seen, f"DUT default SoftAP on air: {seen}"
