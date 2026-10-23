# Debugging agenda

Project-side parts never observed doing their job on this bench. Burned down by
`/commission`; each proven item flips its capability in
[`test-plan.yaml`](test-plan.yaml) from `unproven` to `yes`, with the
measurement recorded on the capability. The testbench is not on this list.

| Part | Capability | Unproven because | Proven by |
|------|------------|------------------|-----------|
| T-Display-S3 in SLOT4 and the forward path | `dut-tdisplay-s3-slot4` | The bench's device list shows an `esp32s3` in SLOT4, but that does not prove it is a T-Display-S3 with 16 MB flash (SLOT4 is shared with `esp32-oled-hello`). No CI-built image for this project has been flashed or observed. | Flash ID reads 16 MB; a CI artefact flashed at its own `flash_args` offsets; its marker line observed on SLOT4's monitor after reset |
| Built-in ST7789 LCD | `lcd-st7789` | The pin map, GPIO 15 power enable, GPIO 38 backlight, 10 MHz i80 clock and offset 35 come from LilyGO's published pin map, not from observation of this board | A CI-built probe that fills the panel with a known pattern (edges marked, one colour band) using exactly those values, with the operator confirming orientation, colour and no edge noise |
| Operator at the bench | `operator-at-bench` | No operator prompt has been answered for this project, and nobody has checked that the panel can be seen from the operator's position | One prompt raised and answered by a person, with a timestamp, asking a question only someone looking at the panel can answer |
