# Gate: Load defined — closes Phase 0 (Definition)

**Standing exclusion:** evidence is committed artefacts and live bench answers
only — never memory, transcripts, or the author's account.

## Requirements

| # | Must be true | Where to look | Evidence |
|---|--------------|---------------|----------|
| 1 | Every requirement (`FR-`, `NFR-`, `C-` bullet) has a verification contract | `docs/Functionality/TDisplay-S3-Hello-FSD.md` | A table row starting `\| <id> ` / `\| <id> (` or a YAML `id: <id>` (C-6.1 – C-6.5 share one row) |
| 2 | Every contract has a non-empty *Must NOT happen* / `prohibited_outcomes` | same | Column 4 of each compact row; `prohibited_outcomes:` in each YAML |
| 3 | Every requirement carries a provenance tag and no `[proposed]` remains in requirement text | same | `[user]` / `[derived …]` on each bullet |
| 4 | State model complete: T1 – T5 plus a completeness paragraph | FSD §5.3 | Table and "Completeness" list |
| 5 | Security profile precedes FR-9.1 | FSD §9.1 | Profile table |
| 6 | Build numbers stated: target, IDF version, flash size, partition, console, pins, LCD power and backlight GPIOs, i80 clock, panel offset | FSD §10, §6.3 | C-10.1 – C-10.5, C-6.1 – C-6.5, FR-6.7 |
| 7 | Each phase is enterable from the previous one | FSD §3 | Phase 1 deliverables need no display; Phase 2 depends only on Phase 1 + wiring |
| 8 | Three planes committed | `docs/00-Overview.md`, `docs/Method/`, `docs/UserDocumentation/User-Manual.md` | `git ls-files docs` |
| 9 | No open decisions | FSD Appendix B | `open_decisions: []` |

## Mechanical checks

```bash
F=docs/Functionality/TDisplay-S3-Hello-FSD.md
for id in $(grep -oE '^- \*\*(FR|NFR|C)-[0-9]+\.[0-9]+' $F | sed 's/- \*\*//'); do
  grep -qF "| $id |" $F || grep -qF "| $id (" $F || grep -qxF "id: $id" $F \
  || { [[ $id == C-6.* ]] && grep -qF "| C-6.1 – C-6.5" $F; } || echo "NO CONTRACT $id"; done
grep -nE '^- \*\*(FR|NFR|C)-' $F | grep -iE 'appropriate|graceful|user-friendly|as needed|if possible|reasonable|sufficient|robust|properly|seamless|optimal|minimal|acceptable|normal operation|best effort'   # expect nothing
grep -nE '\{\{|TODO|<placeholder>' -r docs                     # expect nothing
grep -n 'open_decisions: \[\]' $F                              # expect a hit
git ls-files docs | sort
```

## Judgement checks

- Pick three contracts at random. Could a competent stranger build a rig from each
  **without reading any code**? Quote the stimulus and the observable.
- Do FR-5.8, FR-5.9 and FR-5.10 each prohibit "the device reset"? Quote it.

## Traps

- Operator-observed requirements (FR-5.1, FR-5.3, FR-6.1, FR-6.3, FR-6.4, FR-6.7) with no named
  operator procedure — check `docs/Method/standards/testing.md` has P-OPERATOR.
- A number appearing in a contract that no requirement states (invented threshold).

## Verdict

`OPEN`, or `SHUT` followed by one line per finding: requirement # · evidence looked
for · what was found.
