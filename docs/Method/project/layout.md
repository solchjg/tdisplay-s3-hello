# Project bindings — layers, source layout, toolchain, bench

## Source layout mirrors FSD §2.4

| Layer | Component | Location | Depends on |
|-------|-----------|----------|------------|
| L2 | Hello Display Logic (FSD §5) | `components/hello_logic/` — pure C, no ESP-IDF headers | nothing |
| L1 | LCD Display Interface (FSD §6) | `components/lcd/` (layout and font core pure; panel I/O via esp_lcd) | ESP-IDF esp_lcd, GPIO driver |
| L1 | Serial Log Interface (FSD §7) | `components/hello_log/` (format core pure; emit via esp_log) | esp_log |
| — | Composition root | `main/app_main.c` — wires the timer, the logic, and both interfaces | all of the above |
| host tests | | `tests/host/` — builds `hello_logic` and the pure cores with the host compiler | the pure cores only |

- `hello_logic` exposes a transition function: (state, event, guard result) →
  (next state, actions). The composition root executes the actions.
- `lcd` returns `esp_err_t` for every call and never retries or aborts; policy
  belongs to `hello_logic` (FSD §6.5).
- Panel bring-up order: GPIO 15 high → i80 bus (10 MHz) → ST7789 panel IO and
  panel → reset → init → colour inversion on → swap X/Y and mirror for landscape →
  gap (0, 35) → display on → clear to black → draw → GPIO 38 high. The inversion,
  mirror flags and gap are implementation recommendations from the LilyGO
  reference code; FSD FR-6.1, FR-6.3 and FR-6.4 are the requirements, and the
  operator checks decide.
- Text uses a 16 × 32 fixed-width bitmap font (ASCII 0x20 – 0x7E only). Line 1 at
  y = 40, line 2 at y = 96, both at x = 16 (recommendation; FR-6.5 is the
  requirement). Line 2 is redrawn by drawing its full 288 px-wide row cell, so
  stale digits are overwritten (FR-5.3).
- Draw from a line-sized buffer in internal DMA-capable RAM (16 chars × 16 × 32 ×
  2 B = 16 KiB); PSRAM stays disabled.
- The ST7789 panel driver is in-tree in ESP-IDF (`esp_lcd_new_panel_st7789`);
  declare `esp_lcd` only once the code includes it.

## Fault-injection test build

`tests/target/lcd_fault/` builds the shipped `main/` and components with
`components/lcd/` replaced by a stub (`lcd_fault`) selected by a test-only
Kconfig option. The stub returns a configured `esp_err_t` at init or at the k-th
draw, and logs `lcdfi: call` on every call it receives (FSD §5.5). It is built by
CI as a test artefact and never released.

## Toolchain

- ESP-IDF v6.0.2 via the container image `espressif/idf:v6.0.2` (FSD C-10.2).
- `cmake_minimum_required(VERSION 3.22)` (IDF 6 minimum).
- `sdkconfig.defaults` sets target `esp32s3`, 16 MB flash, single-app partition
  table, the USB-Serial/JTAG console, and leaves SPIRAM disabled (FSD C-10.1,
  C-10.3 – C-10.5).

## Bench

- Testbench `192.168.2.230`, SLOT4, `rfc2217://192.168.2.230:4004`.
- EN/BOOT GPIOs are not wired on SLOT4: flash and reset over USB only.
- SLOT4 is shared with `esp32-oled-hello`; confirm `detected_chip: esp32s3` before
  any run.
- Native USB part: never open the port with DTR/RTS asserted (see
  [`../standards/testing.md`](../standards/testing.md)).
