# Gate: Ready for shipment — closes Phase 3 (Build)

**Standing exclusion:** evidence is committed artefacts, CI results, and live
bench answers only — never memory, transcripts, or the author's account.

## Requirements

| # | Must be true | Where to look | Evidence |
|---|--------------|---------------|----------|
| 1 | Every FSD requirement is verified by ≥ 1 declared test | FSD ids vs plan `verifies:` | Every `FR-`/`C-` id appears in some `verifies:` |
| 2 | Every verifying test is `successful`, with its prohibited outcomes checked, at a commit not older than the last change to its `impl:` or the code under test | plan `result:` | `status: successful`, `commit:` |
| 3 | Journey JRN-01.1 – .6 green | plan | all six `successful` |
| 4 | Every state-table row T1 – T5 has a transition test | plan | `verifies:` or title naming T1 – T5 |
| 5 | Reconcile both directions empty: no declared test with empty `impl:`; no executable under `tests/` that no `impl:` points at | plan + `tests/` | the two lists |
| 6 | User manual current: status line no longer "nothing is deployable yet"; chapters 2 – 4 written | `docs/UserDocumentation/User-Manual.md` | text |

## Mechanical checks

```bash
F=docs/Functionality/TDisplay-S3-Hello-FSD.md
for id in $(grep -oE '^- \*\*(FR|NFR|C)-[0-9]+\.[0-9]+' $F | sed 's/- \*\*//'); do
  grep -qE "verifies:.*\b${id//./\\.}\b" testing/test-plan.yaml || echo "UNVERIFIED $id"; done
grep -nE 'impl: ""' testing/test-plan.yaml                       # expect nothing
grep -nE 'status: (not done|failed)' testing/test-plan.yaml       # expect nothing
```

## Traps

- FR-5.8 / FR-5.9 / FR-5.10 passing because the device rebooted — the evidence
  must show no boot banner across the window.
- Operator-confirmed tests "passed" from a serial log alone.

## Verdict

`OPEN`, or `SHUT` + one line per finding.
