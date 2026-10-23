# T-Display-S3 Hello — User Manual

How to connect, flash and run the hello-world firmware on a LilyGO T-Display-S3.

**Status: development builds only, no release yet.** Builds from `main` run on
the board and show the greeting and uptime; they are verified on the testbench
for the normal case. Display-error handling is built but not yet verified.

## Contents

1. What you need
2. Installation and first run
3. Troubleshooting
4. Recovery

## 1. What you need

- A LilyGO T-Display-S3, non-touch variant, with 16 MB flash.
- A USB-C data cable to the board's USB-C connector.

No wiring is needed: the display is built in. No battery is needed.

Hold the board in landscape with the USB-C connector on your right to read the
display.

## 2. Installation and first run

1. Download a build's artefact `firmware-v<version>` from the repository's
   *Build Firmware* workflow run and unpack it. Use its `coldflash/` folder.
2. Connect the board by USB-C and flash all images at the offsets in
   `coldflash/flash_args`:

   ```bash
   cd coldflash
   esptool --chip esp32s3 -b 460800 write-flash @flash_args
   ```

3. After the flash, the board restarts. Within 3 seconds the display shows,
   in white on black:

   ```
   Hello, world!
   Up: 0 s
   ```

   The second line counts up once per second.
4. To read the log, open the board's USB serial port (native USB; any baud rate). Each second
   it prints `hello: up=<N>`, matching the display.

## 3. Troubleshooting

| You see | Meaning | Do |
|---------|---------|----|
| Display dark, log shows `hello: lcd init failed: <error>` | The display driver reported an error at start; the board carries on with the log only | Unplug and replug USB-C. If it repeats, report the error name |
| Log shows `hello: lcd write failed: <error>` | A display update failed; the display is no longer updated until restart | Unplug and replug USB-C |
| Display dark, no log at all | The firmware is not running | Re-flash (chapter 2) |
| Text upside down or mirrored | You are holding the board the other way | Hold it with USB-C on the right |
| A serial monitor shows nothing and the board seems stopped | Some monitors hold the board in reset or download mode when they open the port | Use a monitor that leaves DTR and RTS low, or unplug and replug USB-C |

## 4. Recovery

The firmware does not retry the display after a driver error. A full restart is
a USB reset of the board, or unplugging and replugging USB-C; nothing is stored,
so a restart always starts clean at `Up: 0 s`.

If the board will not take a flash, hold the button wired to GPIO 0 (BOOT)
while plugging in USB-C, then flash again.

---

**Contract:** [`../Functionality/TDisplay-S3-Hello-FSD.md`](../Functionality/TDisplay-S3-Hello-FSD.md) · **Build rules:** [`../Method/AI-Workflow.md`](../Method/AI-Workflow.md)
