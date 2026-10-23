# Gate: DUT ready — closes Phase 2 (Commissioning)

**Standing exclusion:** evidence is committed artefacts, CI results, and live
bench answers only — never memory, transcripts, or the author's account.

## Requirements

| # | Must be true | Where to look | Evidence |
|---|--------------|---------------|----------|
| 1 | The DUT is the unit the FSD names | Live bench device list | SLOT4 `present: true`, `detected_chip: esp32s3` |
| 2 | Forward path proven: a CI-built image flashed at the offsets in its own `flash_args`, marker observed | `testing/test-plan.yaml` capability `dut-tdisplay-s3-slot4` | `available: yes` plus the CI run id, the offsets used, and the observed `Init complete, running event-driven` line |
| 3 | LCD proven | capability `lcd-st7789` | `available: yes` plus the CI-built probe's run id and an operator confirmation of orientation, colour and clean edges |
| 3a | Operator proven | capability `operator-at-bench` | `available: yes` plus one answered prompt with timestamp |
| 3b | Board identity | capability `dut-tdisplay-s3-slot4` | Flash ID reads 16 MB (FSD C-10.3) |
| 4 | Debugging agenda empty of project-side items | `testing/debugging-agenda.md` | No open rows |
| 5 | Every JRN-01 step that needs only commissioned capabilities is unblocked | plan | No `needs:` entry is `unproven` |

## Mechanical checks

```bash
grep -nA3 'dut-tdisplay-s3-slot4:\|lcd-st7789:\|operator-at-bench:' testing/test-plan.yaml   # available: yes
grep -c 'available: unproven' testing/test-plan.yaml                   # expect 0 (fields, not the header comment)
curl -fsS http://192.168.2.230:8080/api/devices | jq '.slots[] | select(.label=="SLOT4") | {present, detected_chip}'
```

## Judgement checks

- Did the forward-path evidence come from a **CI artefact**, not a local build?
  Quote the run id.

## Traps

- Commissioning "proved" the board by a local flash from a developer's build dir.
- LCD proven by the firmware's own `hello: shown` line only (that is FR-5.2's
  test, not commissioning of the wiring).

## Verdict

`OPEN`, or `SHUT` + one line per finding.
