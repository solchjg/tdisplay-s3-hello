# Gate: AI harnessed — closes Phase 1 (Harness)

**Standing exclusion:** evidence is committed artefacts, CI results, and live
bench answers only — never memory, transcripts, or the author's account.

**Phase 1 never touches the DUT.** Do not flash, reset, read, or monitor SLOT4.

## Requirements

| # | Must be true | Where to look | Evidence |
|---|--------------|---------------|----------|
| 1 | Gate *Load defined* still holds | `testing/gates/load-defined.md` | Its mechanical checks pass on HEAD |
| 2 | Test plan exists with capabilities and the journey | `testing/test-plan.yaml` | `capabilities:` has bench entries `available: yes`, `dut-tdisplay-s3-slot4`, `lcd-st7789` and `operator-at-bench` `available: unproven`, `slot4-gpio-reset` `available: no` with a consequence, `release-verification`; `tests:` has JRN-01.1 – JRN-01.6, `shape: workflow`, `kind: standard`, `wave: 1`, each with `verifies:` and `needs:` |
| 3 | No status was typed: every result is `not done` with a reason, no `blocked` field anywhere | same | no `blocked:` field; no `status: successful` / `status: failed` |
| 4 | Every requirement id in `verifies:` exists in the FSD | plan + FSD | Each id greps as a bullet in the FSD |
| 5 | Debugging agenda lists exactly the three `unproven` capabilities, each with *unproven because* and *proven by* | `testing/debugging-agenda.md` | Table rows; the testbench is not listed |
| 6 | Testing standard is one file with run rules and shared procedures | `docs/Method/standards/testing.md` | Sections P-RESET, P-POWERCYCLE, P-OPERATOR, P-FAULT |
| 7 | Firmware hooks match the FSD scope: no WiFi, BLE, OTA, NVS, UDP-log module; the only output is the FR-7.6 marker (UDP logging excluded by FSD FR-9.1) | `main/`, `CMakeLists.txt`, `sdkconfig.defaults` | `main/app_main.c` logs `Init complete, running event-driven`; no `esp_wifi`, `bt`, `nvs_flash`, `udp_log` anywhere in `main/` |
| 8 | Build constraints come from the FSD, not from hardware | `sdkconfig.defaults` | 16 MB flash, single-app partition, USB-Serial/JTAG console, each citing its C-10.x |
| 9 | CI: build on push, release on tag, verify job between them | `.github/workflows/build.yml` | Jobs `build`, `verify` (`runs-on: [self-hosted, testbench]`, tags only), `release` with `needs: [build, verify]` |
| 10 | CI has run green once on main | GitHub | `gh run list -L 5 --branch main` shows `Build Firmware` and `host tests + lint` with conclusion `success` |
| 11 | Devcontainer with toolchain and runner; registration not automatic | `.devcontainer/` | `Dockerfile` FROM `espressif/idf:v6.0.2`, runner tarball pinned, TestbenchDriver pinned to a commit; `register-runner.sh` is per-repo, `--ephemeral`, label `testbench`; nothing in `devcontainer.json` runs it; the `devcontainer` job of `host tests + lint` is green on HEAD |
| 12 | Outside contributors need approval to run workflows (public repo + self-hosted runner) | GitHub | `gh api repos/solchjg/tdisplay-s3-hello/actions/permissions/fork-pr-contributor-approval` → `all_external_contributors` |

## Mechanical checks

```bash
test -f testing/test-plan.yaml && test -f testing/debugging-agenda.md
ls .github/workflows/
grep -c 'id: JRN-01\.' testing/test-plan.yaml                     # expect 6
grep -nE '^\s*blocked:|status: (successful|failed)' testing/test-plan.yaml   # expect nothing (fields only, not comments)
grep -rnE 'esp_wifi|esp_bt|nvs_flash|udp_log|esp_https_ota' main CMakeLists.txt   # expect nothing
grep -n 'Init complete, running event-driven' main/app_main.c
gh run list -R solchjg/tdisplay-s3-hello -L 5 --branch main
gh api repos/solchjg/tdisplay-s3-hello/actions/permissions/fork-pr-contributor-approval
```

## Judgement checks

- **The behavioural check.** Reading only `testing/test-plan.yaml`,
  `testing/debugging-agenda.md` and the FSD, can you state the project's position
  and the next act without asking anyone? Write the two sentences; if you
  cannot, name the missing input.
- Is every capability's `available:` value one of `yes` / `no` / `unproven`,
  with bench ones `yes` and project ones `unproven` (or `no` with a consequence)?

## Traps

- A capability whose evidence could only have come from the board (Phase 2 work
  done early).
- A host test asserting product behaviour rather than that the tier runs.
- The verify job silently passing with zero bench tests: it must fail
  (`pytest` exit 5), so no release can be published before the journey exists.
- A green build that never ran `set-target esp32s3`.

## Verdict

`OPEN`, or `SHUT` followed by one line per finding: requirement # · evidence looked
for · what was found.
