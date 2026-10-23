# T-Display-S3 Hello — Functional Specification Document (FSD)

This document is the **WHAT** plane: what must be true of the firmware. The plane
map is [`../00-Overview.md`](../00-Overview.md); the other planes are
[`../Method/`](../Method/00-Overview.md) (HOW) and the
[User Manual](../UserDocumentation/User-Manual.md) (OPERATE).

**Conventions.** Requirements are `FR-x.y` (functional), `NFR-x.y` (quality) and
`C-x.y` (constraint), each with a priority `[Must/Should/May]` and a provenance tag:
`[user]` stated by the user, or carried over from the `esp32-oled-hello` shape that
the user chose for this project; `[derived]` a logical consequence of a `[user]`
item or a board fact; `[proposed]` a value this document proposes that has not yet
been accepted (listed under *Open decisions*, Appendix B). Everything not tagged
`[proposed]` is approved.

## Contents

| § | Section |
|---|---------|
| 1 | System Overview |
| 2 | System Architecture (incl. 2.4 Component Layering) |
| 3 | Implementation Phases |
| 4 | Risks, Assumptions & Dependencies |
| 5 | Hello Display Logic (L2) |
| 6 | LCD Display Interface (L1) |
| 7 | Serial Log Interface (L1) |
| 8 | ESP-IDF Platform (L0) |
| 9 | Security |
| 10 | Build & Platform Constraints |
| 11 | Operational Procedures |
| 12 | Verification & Validation |
| A | Constants & Configuration Catalogue |
| B | Lifecycle Metadata |

---

## 1. System Overview

A minimal "hello world" firmware for the LilyGO T-Display-S3 (ESP32-S3, built-in
1.9-inch ST7789 170×320 LCD on an 8-bit parallel bus). In landscape it shows a
fixed greeting on the first line and a seconds-since-boot counter on the second,
refreshed once per second, in white on black. Every value drawn is mirrored to the
serial log, so the loop can verify behaviour automatically without a camera. If the
display driver reports an error, the firmware carries on with the serial log alone
until the next reset.

**Goals.** A known-good first project for this board on the Harness testbench:
build, flash, observe on serial, and confirm the built-in display end to end.

**Non-goals.** No WiFi, BLE, OTA, persistence, buttons, touch, battery measurement,
or PSRAM use. No graphics beyond two text lines.

**Users.** The developer running the AI closed loop on the testbench; a bench
operator who confirms what the display shows.

**High-level flow.** Reset → power and initialise the LCD → draw `Hello, world!`
and the uptime → every second, redraw the uptime and log it → if the driver
reports an error, log it and continue logging only.

---

## 2. System Architecture

### 2.1 Logical Architecture

```
            ┌──────────────────────────── ESP32-S3 ─────────────────────────────┐
            │  1 s tick ──► Hello Display Logic ──► LCD Display Interface ──────┼─ i80 8-bit ─► ST7789
            │                       │                                           │
            │                       └────────────► Serial Log Interface ────────┼─ USB-Serial/JTAG ─► bench
            └───────────────────────────────────────────────────────────────────┘
```

One periodic tick drives the application logic; each tick produces at most one
display update and exactly one log line. The display path and the log path are
independent: a failing display never suppresses the log line.

### 2.2 Hardware / Platform Architecture

| Item | Value | Source |
|------|-------|--------|
| Board | LilyGO T-Display-S3, non-touch variant | [user] |
| MCU | ESP32-S3R8: 16 MB flash, 8 MB octal PSRAM (PSRAM unused) | [user] |
| Display | ST7789 controller, 170×320 visible pixels, RGB565, 8-bit Intel-8080 (i80) parallel bus | [derived from the board] |
| LCD data pins | D0 – D7 = GPIO 39, 40, 41, 42, 45, 46, 47, 48 | [derived from the LilyGO T-Display-S3 pin map] |
| LCD control pins | WR = GPIO 8, RD = GPIO 9, DC = GPIO 7, CS = GPIO 6, RST = GPIO 5 | [derived from the LilyGO T-Display-S3 pin map] |
| LCD power enable | GPIO 15 (active high) | [derived from the LilyGO T-Display-S3 pin map] |
| Backlight | GPIO 38 (active high) | [derived from the LilyGO T-Display-S3 pin map] |
| i80 pixel clock | 10 MHz | [user] |
| Visible-area offset | The 170-pixel axis starts at controller address 35 (the ST7789's 240-line RAM, centred) | [derived from the board] |
| Power and console | USB-C on the board, which is the ESP32-S3's native USB-Serial/JTAG | [derived from the board] |
| Bench slot | SLOT4 (EN/BOOT GPIOs **not wired**; reset over USB only) | [derived from the testbench device list, 2026-10-23] |

### 2.3 Software Architecture

Single application task driven by a 1 s periodic timer. No persistence: all state
is lost at reset by design. No network stack is linked (§9).

### 2.4 Component Layering

```
┌──────────────────────────────────────────────────────────────────┐
│ L2  Application logic   │ Hello Display Logic (§5)               │
├──────────────────────────────────────────────────────────────────┤
│ L1  Interfaces          │ LCD Display Interface (§6)             │
│                         │ Serial Log Interface (§7)              │
├──────────────────────────────────────────────────────────────────┤
│ L0  Foundation          │ ESP-IDF: esp_lcd i80 bus and ST7789    │
│                         │ panel driver, GPIO, esp_timer,         │
│                         │ FreeRTOS, esp_log, USB-Serial/JTAG     │
│                         │ console (§8)                           │
└──────────────────────────────────────────────────────────────────┘
          dependencies point strictly downward
```

- **L2 Hello Display Logic**: owns the state model (§5.3), the line text, and the
  uptime value. Pure functions; no I/O.
- **L1 LCD Display Interface**: owns panel power, backlight, orientation, text
  rendering onto the 320×170 landscape area, and the mapping of driver results to
  "display ok / display failed".
- **L1 Serial Log Interface**: owns the exact log line formats (§7).
- **L0 ESP-IDF**: configured and used, not implemented; tested transitively.

Source layout and dependency rules that implement this layering are HOW:
[`../Method/project/layout.md`](../Method/project/layout.md).

---

## 3. Implementation Phases

### 3.1 Phase 1: Serial heartbeat

- **Scope.** Build for the ESP32-S3, flash through SLOT4, emit the uptime log
  line every second. No display code.
- **Deliverables.** Firmware satisfying C-10.1 – C-10.5, FR-5.5, FR-7.5, FR-7.6,
  FR-9.1, and the serial side of FR-5.4 and FR-7.3 (the display side of both is
  Phase 2).
- **Exit criteria.** On the bench, after a USB reset of SLOT4, 60 consecutive
  `hello: up=<N>` lines arrive with N increasing by exactly 1 per line, period
  1000 ± 100 ms, and no reset in between.
- **Dependencies.** The testbench and the board in SLOT4 only. Nothing from a later
  phase is needed.

### 3.2 Phase 2: Display

- **Scope.** Drive the built-in LCD; implement the full state model, including the
  degraded path.
- **Deliverables.** All remaining requirements in §5, §6, §7, plus the
  fault-injection test build that §5.5 uses.
- **Exit criteria.** All Must requirements in §5 – §7 pass their contracts,
  including the operator-confirmed display checks and the fault-injected degraded
  runs.
- **Dependencies.** Phase 1 (the serial log is the evidence channel for every
  Phase 2 contract); the panel pin map and offset of §2.2 confirmed during
  commissioning (`/commission`).

---

## 4. Risks, Assumptions & Dependencies

### 4.1 Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| R-1 | The serial mirror proves what the firmware *intended* to draw, not what the panel shows | Certain | Medium | Display content is confirmed by an operator (FR-5.1, FR-5.3, FR-6.1, FR-6.3 – FR-6.5) |
| R-2 | The i80 bus is write-only, so a real panel fault is invisible to the firmware; the degraded path can be exercised only by injecting a driver error | Certain | Low | Degraded behaviour is verified on a fault-injection test build (§5.5); real-hardware display faults are out of scope (§4.3) |
| R-3 | Native-USB re-enumeration after reset adds latency to bench timing of FR-5.2 | Medium | Low | The test errs conservative: it can fail a compliant device, never pass a non-compliant one. A false fail returns as a spec-defect finding |
| R-4 | Wrong mirror, colour-inversion or offset settings produce a mirrored, colour-inverted or shifted image, which every serial-only test misses | Medium | Medium | Operator checks FR-6.1, FR-6.3 and FR-6.4 each name the specific defect to look for |
| R-5 | SLOT4 is also the bound slot of `esp32-oled-hello`; only one of the two projects can be tested at a time | Certain | Low | Commissioning confirms the board in SLOT4 is the T-Display-S3 before any test (P-RESET precondition) |

### 4.2 Assumptions

- The board is powered from USB-C on the bench; no battery is fitted (assumed; not
  architecture-critical).

### 4.3 Explicitly out of scope

- WiFi, BLE, OTA, NVS persistence, watchdog configuration beyond ESP-IDF defaults.
- The two on-board buttons (GPIO 0, GPIO 14), touch, battery voltage (GPIO 4),
  backlight dimming, and PSRAM. [user]
- Retrying or recovering the display after a driver error; the device stays in
  DEGRADED until reset (FR-5.9). [user]
- Detecting a physically absent or faulty panel (R-2). [user]
- Panel content in DEGRADED: unspecified.
- Uptime counter wrap after 2³² − 1 s (≈ 136 years).
- Secure boot, flash encryption (§9).

### 4.4 Dependencies

- ESP-IDF **v6.0.2**, the image the Harness uses (`espressif/idf:v6.0.2`). [user]
- Embedded AI Harness testbench at `192.168.2.230`, SLOT4.

---

# Part A — Application Logic (L2)

## 5. Hello Display Logic

### 5.1 Purpose

Decides what the two lines say, when they are refreshed, and how the firmware
behaves when the display driver reports an error.

### 5.2 Data

| Item | Origin | Type / unit | Range | Invalid representation |
|------|--------|-------------|-------|------------------------|
| Line 1 | constant | ASCII string | exactly `Hello, world!` | n/a |
| N (uptime) | ESP-IDF monotonic clock | unsigned 32-bit, seconds since boot | 0 – 4294967295 | none; always valid |
| Line 2 | derived from N | ASCII string `Up: <N> s`, N in decimal, no leading zeros | 7 – 16 characters | n/a |

### 5.3 State model

States are exhaustive and mutually exclusive; the transition table is normative.

| State | Meaning |
|-------|---------|
| **BOOT** | From reset until the first display initialisation attempt completes |
| **SHOWING** | The display driver has reported no error; the panel shows both lines |
| **DEGRADED** | The display driver has reported an error; uptime continues on serial only, until reset |

| # | Current | Event | Guard | Next | Action | Limit |
|---|---------|-------|-------|------|--------|-------|
| T1 | BOOT | display init done | init succeeded | SHOWING | Clear panel to black; draw line 1 and line 2; backlight on; log `hello: shown` | 3 s from reset |
| T2 | BOOT | display init done | init failed | DEGRADED | Log `hello: lcd init failed: <ERR>` | 3 s from reset |
| T3 | SHOWING | 1 s tick | write succeeded | SHOWING | Redraw line 2; log `hello: up=<N>` | 1000 ± 100 ms period |
| T4 | SHOWING | 1 s tick | write failed | DEGRADED | Log `hello: up=<N>`; log `hello: lcd write failed: <ERR>` | same tick |
| T5 | DEGRADED | 1 s tick | — | DEGRADED | Log `hello: up=<N>`; no display call | 1000 ± 100 ms period |

**Completeness.**
- BOOT × 1 s tick: impossible by construction; the tick starts on exit from BOOT.
- There is no retry timer; DEGRADED has no exit other than reset.
- Any state × reset: the device restarts in BOOT; no state persists across reset.
- Prohibited: any transition that causes a reset (FR-5.10).

### 5.4 Requirements

- **FR-5.1** [Must] [user] In SHOWING, the display shall show the text
  `Hello, world!` as the top text line.
- **FR-5.2** [Must] [user] The device shall enter SHOWING (T1) within 3 s of reset
  when display initialisation succeeds.
- **FR-5.3** [Must] [user] In SHOWING, the second text line shall read
  `Up: <N> s`, where N is the current uptime in whole seconds.
- **FR-5.4** [Must] [user] The device shall produce one uptime refresh every
  1000 ms ± 100 ms, in SHOWING and DEGRADED alike.
- **FR-5.5** [Must] [derived from FR-5.3/FR-5.4] N shall increase by exactly 1
  between consecutive refreshes and shall satisfy |N − ⌊t/1000⌋| ≤ 1, where t is
  the ms-since-boot timestamp of the refresh's log line (FR-7.5).
- **FR-5.6** [Must] [user] The device shall enter DEGRADED (T2) within 3 s of
  reset when display initialisation reports an error.
- **FR-5.7** [Must] [user] In DEGRADED, the device shall continue the uptime
  refreshes of FR-5.4 on serial.
- **FR-5.8** [Must] [user] When a display write reports an error in SHOWING, the
  device shall enter DEGRADED (T4) on that same tick.
- **FR-5.9** [Must] [user] In DEGRADED, the device shall make no display
  initialisation or write call until the next reset.
- **FR-5.10** [Must] [user] The device shall not reset as a result of any display
  error (at initialisation or at runtime).

### 5.5 Verification contracts

The degraded path (FR-5.6 – FR-5.10) is driven by a **fault-injection test
build**: the shipped firmware with its LCD Display Interface replaced by one that
reports an error at a chosen call (initialisation, or the k-th write). It is a
test artefact, never released; how it is built is HOW.

Compact form:

| ID | Precondition · stimulus | Expected observation | Must NOT happen | Timing | Tier |
|----|------------------------|----------------------|-----------------|--------|------|
| FR-5.1 | Shipped build; reset SLOT4; operator prompted | Operator confirms `Hello, world!` on the top line, spelled exactly | Text truncated, misspelled, mirrored or upside-down; operator not asked | n/a | bench (operator) |
| FR-5.2 | Shipped build; bench issues USB reset | `hello: shown` arrives on the bench serial monitor | `hello: lcd init failed` before `hello: shown`; a second boot banner | ≤ 3.0 s from the reset command (bench wall clock) | bench |
| FR-5.3 | In SHOWING; operator prompted after the latest `hello: up=<N>` | Operator confirms line 2 reads `Up: <N> s` with N within ±1 of the logged value | Leading zeros; unit missing; stale digits left from a previous value | n/a | bench (operator) |
| FR-5.3 (core) | Format N ∈ {0, 9, 10, 4294967295} | `Up: 0 s`, `Up: 9 s`, `Up: 10 s`, `Up: 4294967295 s` | Any other string | n/a | host |
| FR-5.4 | Running; capture 61 consecutive `hello: up=` lines | Each log-timestamp gap is 900 – 1100 ms; and 60 refreshes span 60 ± 1 s of bench wall clock | A gap outside the range; a missing line | 1000 ± 100 ms | target |
| FR-5.5 | As FR-5.4 | Consecutive N differ by exactly 1; each N within ±1 of ⌊t/1000⌋ | Repeated or skipped N; N restarting at 0 | n/a | target |
| FR-5.6 | Fault-injection build failing at init; bench issues USB reset | `hello: lcd init failed: ` line arrives | `hello: shown`; any reset | ≤ 3.0 s from the reset command | target |
| FR-5.6 (core) | Transition function: BOOT, init done, guard failed | Next = DEGRADED; action = log init failure | Next = SHOWING; a retry action | n/a | host |
| FR-5.7 | As FR-5.6, then capture 11 `hello: up=` lines | Gaps 900 – 1100 ms; N strictly +1 | No lines at all; a gap > 1100 ms | 1000 ± 100 ms | target |
| FR-5.8 (core) | Transition function: SHOWING, 1 s tick, guard write failed | Next = DEGRADED; actions = log up, log write failure, in that order | Next = SHOWING; the up log dropped | n/a | host |
| FR-5.9 (core) | Transition function in DEGRADED; feed 100 ticks | T5 every time; no action is a display call | Any display action; any transition out of DEGRADED | n/a | host |

Full form (a wrong pass is plausible: each of these can "pass" by rebooting):

```yaml
id: FR-5.8
verification:
  preconditions:
    - Fault-injection build set to fail the 5th display write after T1.
  stimulus:
    - Bench issues a USB reset of SLOT4; capture serial until 10 s after the failure.
  expected_observations:
    - "hello: shown" appears, then "hello: up=" lines.
    - "hello: lcd write failed: " appears exactly once.
    - The "hello: up=<N>" line of the same tick precedes it; refreshes continue with N strictly +1.
  timing: the failure line after the "hello: up=" line of the failing tick and before the next "hello: up=" line (same tick)
  tolerance: none beyond the timing bound
  prohibited_outcomes:
    - A boot banner (ESP-ROM or bootloader lines) or N restarting near 0, meaning the device reset.
    - "hello: lcd write failed" logged more than once in one boot.
    - Refreshes stop.
  tier: target
  evidence:
    - Serial log from reset to 10 s after the failure line.
  cleanup:
    - Reflash the shipped build.
```

```yaml
id: FR-5.9
verification:
  preconditions:
    - Fault-injection build failing at init, instrumented to log "lcdfi: call" on every display call it receives.
  stimulus:
    - Bench issues a USB reset of SLOT4; capture serial for 30 s.
  expected_observations:
    - Exactly one "lcdfi: call" line (the failed init) before "hello: lcd init failed".
    - 30 ± 1 "hello: up=" lines after it.
  timing: 30 s observation window
  tolerance: ±1 line
  prohibited_outcomes:
    - Any "lcdfi: call" line after "hello: lcd init failed", which would be a retry.
    - A reset (boot banner, N restarting near 0).
  tier: target
  evidence:
    - Full serial log of the window.
  cleanup:
    - Reflash the shipped build.
```

```yaml
id: FR-5.10
verification:
  preconditions:
    - Fault-injection build; run once failing at init, once failing at the 5th write.
  stimulus:
    - For each run, USB reset of SLOT4, then leave the device running for 60 s after the failure line.
  expected_observations:
    - 60 ± 1 consecutive "hello: up=<N>" lines after the failure line, with N strictly +1.
  timing: 60 s observation window per run
  tolerance: ±1 line
  prohibited_outcomes:
    - Any boot banner, panic message, abort() or "rst:" reset-reason line after the first boot.
    - N decreasing at any point.
  tier: target
  evidence:
    - Full serial log of both runs.
  cleanup:
    - Reflash the shipped build and reset SLOT4.
```

---

# Part B — Interfaces (L1)

## 6. LCD Display Interface

### 6.1 Purpose & peer

Powers the built-in ST7789 panel, turns on its backlight, renders the two text
lines in landscape, and reports whether each driver call succeeded. Direction:
device → display.

### 6.2 Protocol

ESP-IDF esp_lcd i80 bus, 8 data lines, at the pixel clock of C-6.4, with the pins
of C-6.2. RD is not used for reads; it is held high. "Display failed" means an
esp_lcd call (bus creation, panel initialisation, or bitmap draw) returns a value
other than `ESP_OK`. The bus has no acknowledge, so a physically absent or broken
panel is not detected (R-2).

### 6.3 Requirements

- **C-6.1** [Must] [derived from the LilyGO T-Display-S3 pin map] The i80 data
  lines D0 – D7 shall be GPIO 39, 40, 41, 42, 45, 46, 47, 48 in that order.
- **C-6.2** [Must] [derived from the LilyGO T-Display-S3 pin map] The LCD control
  lines shall be WR = GPIO 8, DC = GPIO 7, CS = GPIO 6, RST = GPIO 5, and
  RD = GPIO 9 driven high.
- **C-6.3** [Must] [derived from the LilyGO T-Display-S3 pin map] GPIO 15 (LCD
  power enable) shall be driven high before panel initialisation begins.
- **C-6.4** [Must] [user] The i80 pixel clock shall be 10 MHz.
- **C-6.5** [Must] [derived from the board] The panel's 170-pixel axis shall be
  addressed with an offset of 35 controller lines.
- **FR-6.1** [Must] [user] In SHOWING, text shall be upright and read left to right
  when the board is held in landscape with its USB-C connector to the viewer's
  right.
- **FR-6.2** [Must] [user] Text shall be rendered in a fixed-width font with a
  16 × 32 pixel character cell.
- **FR-6.3** [Must] [user] In SHOWING, text shall be white on a black background.
- **FR-6.4** [Must] [derived from FR-5.1] On entry to SHOWING (T1), the full
  320 × 170 visible area shall be cleared to black, leaving no lit pixels outside
  the two text lines.
- **FR-6.5** [Must] [derived from FR-5.1] Line 2 shall be entirely below line 1,
  with no overlap, and both lines entirely inside the visible area.
- **FR-6.6** [Must] [derived from §5.2 and FR-6.2] Line 2 shall be displayed in
  full, without clipping or wrapping, for every N from 0 to 4294967295 (up to 16
  characters × 16 px = 256 px across 320 px).
- **FR-6.7** [Must] [derived from FR-5.1] In SHOWING, GPIO 38 (backlight) shall be
  driven high.

### 6.4 Verification contracts

| ID | Precondition · stimulus | Expected observation | Must NOT happen | Tier |
|----|------------------------|----------------------|-----------------|------|
| C-6.1 – C-6.5 | Inspect the built configuration | The pin numbers, 10 MHz clock and offset 35 appear in the firmware's own configuration | Any other value; a value taken from a driver default rather than stated | host |
| C-6.1 – C-6.5 (wire) | Shipped build; reset; operator prompted after `hello: shown` | Operator confirms both lines are legible (with FR-6.1, FR-6.4) | Blank, noisy, shifted or garbled panel | bench (operator) |
| FR-6.1 | In SHOWING; operator prompted with the board held USB-C to the right | Operator confirms text upright and left to right | Mirrored, upside-down or rotated by 90° text | bench (operator) |
| FR-6.2 | Inspect the font used by the renderer | Cell width 16 px, height 32 px | Any other cell size; proportional font | host |
| FR-6.3 | In SHOWING; operator prompted | Operator confirms white text on black | Black on white or coloured (inverted-colour defect); grey or tinted background | bench (operator) |
| FR-6.4 | Power-cycle the board (random panel RAM); operator prompted after `hello: shown` | Operator confirms no stray pixels along any edge or between lines | A band of noise along any edge (offset defect); remnants anywhere | bench (operator) |
| FR-6.5 | Render both lines with the shipped layout | Line 2's top row > line 1's bottom row; every glyph inside x ∈ [0, 319], y ∈ [0, 169] | Overlap; any pixel outside the visible area | host |
| FR-6.6 | Render `Up: 4294967295 s` with the shipped font and layout | Rightmost pixel x ≤ 319; single row | Width > 320 px; wrap onto another row | host |
| FR-6.7 | In SHOWING; operator prompted | Operator confirms the backlight is on (text clearly visible, not only under reflected light) | Backlight off or flickering | bench (operator) |

### 6.5 Failure modes

Any esp_lcd call that does not return `ESP_OK` → the interface reports "display
failed" with the `esp_err_t` value to §5; it never retries on its own and never
aborts. What happens next is §5's decision (T2, T4, FR-5.9).

---

## 7. Serial Log Interface

### 7.1 Purpose & peer

The machine-readable mirror of every display decision, read by the testbench
serial monitor on SLOT4. Direction: device → bench. Transport: ESP-IDF log over
USB-Serial/JTAG (C-10.5). Tag: `hello`.

### 7.2 Line formats

`<ERR>` is the name ESP-IDF's `esp_err_to_name()` returns for the failing call's
error code.

| Event | Line (after the ESP-IDF prefix `<L> (<ms>) `) | Level |
|-------|-----------------------------------------------|-------|
| T1 | `hello: shown line1="Hello, world!"` | I |
| T2 | `hello: lcd init failed: <ERR>` | E |
| T3, T4, T5 | `hello: up=<N>` | I |
| T4 | `hello: lcd write failed: <ERR>` | E |
| End of startup | `Init complete, running event-driven` (any tag) | I |

### 7.3 Requirements

- **FR-7.1** [Must] [user] On T1, the device shall log `hello: shown line1="Hello, world!"`.
- **FR-7.2** [Must] [user] On T2, the device shall log `hello: lcd init failed: <ERR>` at error level.
- **FR-7.3** [Must] [user] Each uptime refresh shall log exactly one line
  `hello: up=<N>`, N equal to the value drawn (or that would have been drawn, in DEGRADED).
- **FR-7.4** [Must] [derived from FR-5.8] On T4, the device shall log
  `hello: lcd write failed: <ERR>` at error level.
- **FR-7.5** [Must] [derived from FR-5.5] Every line in §7.2 shall carry the
  ESP-IDF log prefix with a millisecond-since-boot timestamp.
- **FR-7.6** [Must] [user, testbench compatibility contract carried over from
  `esp32-oled-hello`] Once startup has finished, the device shall log exactly
  `Init complete, running event-driven`, once per boot, as the last line of startup.

### 7.4 Verification contracts

| ID | Precondition · stimulus | Expected observation | Must NOT happen | Tier |
|----|------------------------|----------------------|-----------------|------|
| FR-7.1 | Shipped build; reset | Exactly one matching line per boot | Line absent; line repeated without a reset | bench |
| FR-7.2 | Fault-injection build failing at init with `ESP_ERR_TIMEOUT`; reset | `hello: lcd init failed: ESP_ERR_TIMEOUT` at level `E`, once | Level `I`/`W`; numeric code instead of name; line repeated | target |
| FR-7.3 | Running; 10 s capture | 10 ± 1 `hello: up=` lines, one per refresh; N matches the operator-read line 2 within ±1 (with FR-5.3) | Two lines for one refresh; other text on the line | target |
| FR-7.3 (core) | Format the log text for N = 0 and 4294967295 | `up=0`, `up=4294967295` | Padding, sign, other formatting | host |
| FR-7.4 | Fault-injection build failing the 5th write with `ESP_ERR_INVALID_STATE`; reset | `hello: lcd write failed: ESP_ERR_INVALID_STATE` at level `E`, once | Missing; repeated every tick | target |
| FR-7.5 | Any capture | Every `hello:` line matches `^[IEWD] \([0-9]+\) hello: ` | A line without timestamp | target |
| FR-7.6 | USB reset; capture until the first `hello: up=` | Exactly one `Init complete, running event-driven` line, after the ESP-IDF startup lines | Absent; repeated within one boot; reworded | target |

---

# Part C — Foundation (L0)

## 8. ESP-IDF Platform

### 8.1 Purpose

ESP-IDF v6.0.2 supplies the esp_lcd i80 bus and ST7789 panel driver, the GPIO
driver, esp_timer, FreeRTOS, esp_log and the USB-Serial/JTAG console. Configured
and used, not implemented.

### 8.2 Requirements

None of its own. Exercised **transitively** through §5 – §7; no host-tier tests.

---

# Part D — Cross-cutting Concerns

## 9. Security

### 9.1 Security profile: isolated bench demo

| Aspect | Position |
|--------|----------|
| Threat actors | None considered; the device holds no secrets and offers no service |
| Physical access | Anyone with physical access has full control (accepted) |
| Remote exposure | None: no radio, no network |
| Confidentiality / integrity | No data worth protecting |
| Credentials | None exist |
| Firmware authenticity | Not required; secure boot off (accepted risk) |
| Flash encryption | Off (accepted risk) |

The profile justifies exactly one protection: keeping the remote attack surface at
zero.

### 9.2 Requirements

- **FR-9.1** [Must] [derived from §9.1 and the non-goals in §1] The firmware shall
  not initialise the WiFi or BLE radio.

### 9.3 Verification contract

| ID | Precondition · stimulus | Expected observation | Must NOT happen | Tier |
|----|------------------------|----------------------|-----------------|------|
| FR-9.1 | Inspect the linked ELF | No `esp_wifi_init` and no `esp_bt_controller_init` symbol | Either symbol present | host |
| FR-9.1 (air) | Device running; bench WiFi scan and BLE scan | No AP and no advertiser with the DUT's MAC | DUT MAC seen | bench |

---

## 10. Build & Platform Constraints

The numbers a build will otherwise take from a default.

- **C-10.1** [Must] [user] The firmware shall be built for target `esp32s3`.
- **C-10.2** [Must] [user] The firmware shall be built with ESP-IDF v6.0.2.
- **C-10.3** [Must] [user] The build shall declare a 16 MB flash size; a unit with
  less than 16 MB of flash cannot run this firmware.
- **C-10.4** [Must] [user] The application image shall fit the default single-app
  partition table's 1 MB factory partition.
- **C-10.5** [Must] [derived from SLOT4's unwired EN/BOOT] The firmware shall be
  flashable, resettable and observable through the USB-Serial/JTAG port alone,
  with the console on USB-Serial/JTAG.

| ID | Precondition · stimulus | Expected observation | Must NOT happen | Tier |
|----|------------------------|----------------------|-----------------|------|
| C-10.1 | Inspect `sdkconfig` after build | `CONFIG_IDF_TARGET="esp32s3"` | Any other target | host |
| C-10.2 | Inspect the build log / CI image tag | IDF version string `v6.0.2` | Another version | host |
| C-10.3 | Inspect `sdkconfig` | `CONFIG_ESPTOOLPY_FLASHSIZE_16MB=y` | Any other size; size left to a default | host |
| C-10.3 (board) | Read the flash ID of the board in SLOT4 | Detected flash size 16 MB | Smaller flash | bench |
| C-10.4 | Build | `idf.py size` app binary ≤ 1 MB (0x100000) and partition table is the default single-app | Overflow; custom table | host |
| C-10.5 | Flash and reset SLOT4 through the bench using only USB | Flash succeeds and `hello: up=` lines appear on SLOT4's monitor | Need for EN/BOOT GPIO or a button press | bench |

---

# Part E — Operations & Verification

## 11. Operational Procedures

Reading path: connect the board by USB-C (§2.2, User Manual ch. 1) → build per §10
→ flash via SLOT4 (C-10.5) → observe SHOWING (§5, §7) → on a display driver error
the device continues on serial only (§5.3 T2, T4) → a full reset is a USB reset of
SLOT4. Step-by-step instructions:
[User Manual](../UserDocumentation/User-Manual.md).

## 12. Verification & Validation

### 12.0 Test Architecture

| Tier | Runs on | Covers here |
|------|---------|-------------|
| **host** | Dev machine / CI, plain C compiler | §5 transition function, line formatting, render layout and width (FR-6.5, FR-6.6), font cell, configuration and ELF inspection |
| **target** | T-Display-S3 in SLOT4, no operator; shipped or fault-injection build | Refresh period, N monotonicity, log format, the degraded path (FR-5.6 – FR-5.10) |
| **bench** | T-Display-S3 + operator prompt | Display content, orientation, colour, offset, backlight, boot deadline, no-radio scan, flash size |

Layer mapping: L2 (§5) at host as pure functions, plus transitions end to end at
target (fault-injection build); L1 (§6, §7) pure cores (formatting, layout, width)
at host, wire at target/bench; L0 (§8) transitively.

Operator-confirmed checks use the testbench's blocking operator prompt; the
operator's answer and timestamp are the evidence.

### 12.1 Acceptance test

One bench run on the shipped build: power-cycle (FR-6.4) → reset (FR-5.1 – 5.3,
6.1, 6.3, 6.7, 7.1, 7.6) → 60 s capture (FR-5.4, 5.5, 7.3, 7.5). Then the
fault-injection build: fail at init (FR-5.6, 5.7, 5.9, 5.10, 7.2) and fail at the
5th write (FR-5.8, 5.10, 7.4). Reflash the shipped build at the end.

### 12.2 Traceability

Computed by `/build` from `testing/test-plan.yaml` (created in Phase 1 of the
harness journey); never maintained in this document.

---

## Appendix A — Constants & Configuration Catalogue

All configuration is build-time; nothing is changeable at runtime and nothing persists.

| Name | Type | Value | Range | Persistence | Sensitivity | Interface | Change effect |
|------|------|-------|-------|-------------|-------------|-----------|---------------|
| Line 1 text | string | `Hello, world!` | fixed | firmware image | public | source | next flash |
| i80 data pins D0 – D7 | GPIO | 39, 40, 41, 42, 45, 46, 47, 48 | fixed | firmware image | public | build config | next flash |
| WR / RD / DC / CS / RST | GPIO | 8 / 9 / 7 / 6 / 5 | fixed | firmware image | public | build config | next flash |
| LCD power enable | GPIO | 15 | fixed | firmware image | public | build config | next flash |
| Backlight | GPIO | 38 | fixed | firmware image | public | build config | next flash |
| Pixel clock | Hz | 10000000 | fixed | firmware image | public | build config | next flash |
| Panel offset (170-px axis) | lines | 35 | fixed | firmware image | public | build config | next flash |
| Landscape area | px | 320 × 170 | fixed | firmware image | public | source | next flash |
| Font cell | px | 16 × 32 | fixed | firmware image | public | source | next flash |
| Text / background colour | RGB565 | `0xFFFF` / `0x0000` | fixed | firmware image | public | source | next flash |
| Refresh period | ms | 1000 | ±100 tolerance | firmware image | public | source | next flash |
| Boot deadline | ms | 3000 | upper bound | n/a | n/a | n/a | n/a |
| Log tag | string | `hello` | fixed | firmware image | public | source | next flash |

## Appendix B — Lifecycle Metadata

```yaml
document_status: draft
fsd_version: 0.1.0
repository: local only (/home/sadmin/tdisplay-s3-hello); no remote yet
baseline_commit: (initial commit of this document)
applicable_firmware_version: none yet
author: solchjg
reviewers: []
approval_status: all requirements approved by the user
created: 2026-10-23
last_updated: 2026-10-23
change_history:
  - 0.1.0 2026-10-23 initial definition
superseded_requirements: []
open_decisions: []
related_test_baseline: none yet
```
